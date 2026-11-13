"""
Optional LLM Explanation Layer (OFF by default).

Turns already-computed structured triage fields into a short analyst summary.
Never alters category, severity, or priority.
Falls back deterministically to a verified template if LLM_PROVIDER is 'none',
LLM_API_KEY is missing, or the external call fails/times out.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx


def _template_explanation(result: dict[str, Any]) -> str:
    """Deterministic, verified template explanation built strictly from computed fields."""
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
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "temperature": 0.1,
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
    """Return {'explanation': str, 'explanation_source': 'llm' | 'template'}."""
    provider = os.getenv("LLM_PROVIDER", "none").strip().lower()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "8"))

    if provider in ("", "none") or not api_key or api_key == "your_api_key_here":
        return {
            "explanation": _template_explanation(structured_result),
            "explanation_source": "template",
        }

    # Send only verified structured fields
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

    # Retry once on transient failure, then fall back to template
    for _attempt in range(2):
        try:
            if provider == "openai":
                text = _call_openai_compatible(prompt, api_key, model, timeout)
                return {"explanation": text, "explanation_source": "llm"}
            else:
                break
        except Exception:
            continue

    return {
        "explanation": _template_explanation(structured_result),
        "explanation_source": "template",
    }
