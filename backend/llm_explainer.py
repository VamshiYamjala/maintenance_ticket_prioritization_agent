"""
===============================================================================
FILE: backend/llm_explainer.py
===============================================================================
1. WHAT THIS FILE DOES:
   Provides an explanation layer that converts structured triage predictions
   into a concise, human-readable 2–3 sentence operational summary. By default,
   it runs in deterministic template mode with ZERO external API calls. Optionally,
   if an LLM API key is provided in the environment, it can call an OpenAI-compatible
   endpoint with automatic retry and guaranteed fallback.

2. WHY THIS FILE IS NEEDED:
   Control-room operators and technicians reviewing tickets need a quick narrative
   summary explaining the triage decision, probable cause, and immediate recommended
   action. Crucially, this layer acts strictly as a summarizer: it NEVER alters the
   predicted category, severity, priority score, or assigned team.

3. WHICH OTHER FILES USE IT:
   - backend/agent.py: Calls `generate_explanation()` in Tool Step 9.
   - tests/test_triage.py: Verifies fallback to template when API keys are absent.

4. WHAT INPUT IT RECEIVES:
   - `structured_result` (dict): Complete dictionary of verified triage fields
     (category, severity, priority_score, owner_team, probable_causes, etc.).

5. WHAT OUTPUT IT PRODUCES:
   - dict: {
         "explanation": str (plain-English summary),
         "explanation_source": "template" | "llm"
     }
===============================================================================
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx


def _template_explanation(result: dict[str, Any]) -> str:
    """
    1. WHAT IT DOES:
       Synthesizes a deterministic, verified narrative summary directly from
       computed dictionary fields without calling any external AI models.

    2. WHY WE NEED IT:
       Guarantees 100% offline reliability, zero latency overhead, zero financial cost,
       and zero risk of hallucinations or fabricated information.

    3. PARAMETERS:
       - result (dict): The structured ticket evaluation dictionary.

    4. RETURNS:
       str: A 2-to-3 sentence plain English summary.

    5. HOW IT WORKS INTERNALLY:
       Extracts equipment IDs, notes if a safety guardrail escalation occurred,
       notes if human review was flagged, selects the top candidate cause and action,
       and formats them into a standardized operational sentence.
    """
    equip = ", ".join(result.get("equipment_ids") or []) or "unspecified equipment"
    guard_note = (
        f" Safety guardrail escalated severity from {result['ml_severity']} to {result['severity']}."
        if result.get("guardrail_escalated")
        else ""
    )
    review_note = " Flagged for human review due to low model confidence." if result.get("needs_human_review") else ""
    first_cause = (result.get("probable_causes") or ["unspecified fault"])[0]
    first_action = (result.get("next_actions") or ["inspect asset"])[0]

    return (
        f"Classified as {result['category']} ({result['severity']} severity, priority {result['priority_score']}/100) "
        f"for {result['asset_type']} asset ({equip}).{guard_note} "
        f"Routed to {result['owner_team']} ({result['sla_label']}). "
        f"Top probable cause to check: {first_cause}. Recommended first action: {first_action}.{review_note}"
    )


def _call_openai_compatible(prompt: str, api_key: str, model: str, timeout: float) -> str:
    """
    Calls an external OpenAI-compatible chat completion endpoint.
    Constrained with strict system instructions prohibiting fabrication.
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "temperature": 0.1,  # Low temperature for deterministic, factual outputs
        "max_tokens": 180,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an O&M triage assistant. Summarize ONLY the provided JSON fields in 2-3 plain sentences. "
                    "Do NOT invent causes, numbers, or actions not present in the JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    resp = httpx.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"].strip()
    if not text or len(text) < 15:
        raise ValueError("Empty or malformed LLM response")
    return text


def generate_explanation(structured_result: dict[str, Any]) -> dict[str, str]:
    """
    1. WHAT IT DOES:
       Coordinates the explanation layer. Checks environment configuration:
       if LLM_PROVIDER is 'none' or unconfigured (the default), immediately returns
       the deterministic template explanation. Otherwise attempts an LLM call with
       automatic retry and graceful fallback.

    2. PARAMETERS:
       - structured_result (dict): Full triage result dictionary.

    3. RETURNS:
       dict: {"explanation": str, "explanation_source": "template" | "llm"}
    """
    provider = os.getenv("LLM_PROVIDER", "none").strip().lower()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "8"))

    # Default to zero-latency deterministic template if no provider/key configured
    if provider in ("", "none") or not api_key or api_key == "your_api_key_here":
        return {
            "explanation": _template_explanation(structured_result),
            "explanation_source": "template",
        }

    # Pass strictly structured data to prevent hallucination
    safe_context = {
        "asset_type": structured_result.get("asset_type"),
        "equipment_ids": structured_result.get("equipment_ids"),
        "category": structured_result.get("category"),
        "severity": structured_result.get("severity"),
        "guardrail_escalated": structured_result.get("guardrail_escalated"),
        "priority_score": structured_result.get("priority_score"),
        "owner_team": structured_result.get("owner_team"),
        "sla_label": structured_result.get("sla_label"),
        "probable_causes": structured_result.get("probable_causes", [])[:2],
        "next_actions": structured_result.get("next_actions", [])[:2],
        "needs_human_review": structured_result.get("needs_human_review"),
    }
    prompt = f"Summarize this verified triage output:\n{json.dumps(safe_context)}"

    # Retry once on transient network failure, then fall back to template
    for _attempt in range(2):
        try:
            if provider == "openai":
                text = _call_openai_compatible(prompt, api_key, model, timeout)
                return {"explanation": text, "explanation_source": "llm"}
            else:
                break
        except Exception:
            continue

    # Guaranteed fallback
    return {
        "explanation": _template_explanation(structured_result),
        "explanation_source": "template",
    }
