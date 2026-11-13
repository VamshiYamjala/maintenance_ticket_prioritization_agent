"""
Rule/tool-based Maintenance Ticket Triage Agent.

Executes an explicit, ordered pipeline of tools and records every step in `agent_trace`:
1. normalize_and_extract(text)
2. classify_ticket(text, asset_type)
3. safety_guardrail(text, ml_severity)  [escalate-only, never downgrades]
4. lookup_runbook(category, text)       [TF-IDF cosine similarity over local runbook.json]
5. check_duplicates(text, asset_type, recent_tickets)
6. compute_priority(...)
7. route_ticket(...)
8. confidence_gate(...)                 [sets needs_human_review when uncertain]
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import Pipeline

from backend.llm_explainer import generate_explanation
from backend.preprocessing import SEVERITY_TO_INT, extract_entities, normalize_text
from backend.priority import compute_priority, route_ticket

BASE_DIR = Path(__file__).resolve().parents[1]
RUNBOOK_PATH = BASE_DIR / "data" / "runbook.json"
MODELS_DIR = BASE_DIR / "models"


def resolve_models_dir() -> Path:
    if (MODELS_DIR / "category_pipeline.joblib").exists():
        return MODELS_DIR
    for candidate in [
        BASE_DIR / "models",
        Path.cwd() / "models",
        Path("/var/task/models"),
    ]:
        if (candidate / "category_pipeline.joblib").exists():
            return candidate
    return MODELS_DIR


def resolve_runbook_path() -> Path:
    if RUNBOOK_PATH.exists():
        return RUNBOOK_PATH
    for candidate in [
        BASE_DIR / "data" / "runbook.json",
        Path.cwd() / "data" / "runbook.json",
        Path("/var/task/data/runbook.json"),
    ]:
        if candidate.exists():
            return candidate
    return RUNBOOK_PATH

CATEGORY_CONF_THRESHOLD = 0.45
SEVERITY_CONF_THRESHOLD = 0.40
TOP2_MARGIN_THRESHOLD = 0.12

# Deterministic hazard rules: (rule_id, target_min_severity, keywords, reason)
SAFETY_RULES: list[tuple[str, str, list[str], str]] = [
    (
        "SAF-01-FIRE-ARC",
        "critical",
        ["smoke", "fire", "arc flash", "sparks", "burning smell", "burning plastic", "evacuated", "loto"],
        "Active fire, smoke, arc flash, or emergency evacuation keyword detected.",
    ),
    (
        "SAF-02-CRITICAL-FAULT",
        "critical",
        ["unable to feather", "overspeed", "metallic debris", "buchholz trip", "grid trip imminent", "complete plant scada blind", "total rtu comm loss"],
        "High-consequence mechanical, transformer, or grid-visibility hazard detected.",
    ),
    (
        "SAF-03-HAZARD-ESCALATION",
        "high",
        ["oil leak", "oil spill", "buchholz", "overheating", "high temperature alarm", "injury", "near-miss", "interlock"],
        "Equipment integrity or EHS hazard keyword detected; minimum severity set to high.",
    ),
]

NEGATION_PREFIXES = ("no ", "not ", "without ", "no sign of ", "absent ")


def _keyword_present_unnegated(text_lower: str, kw: str) -> bool:
    """Return True if keyword appears and is not immediately preceded by a negation."""
    idx = text_lower.find(kw)
    while idx != -1:
        window = text_lower[max(0, idx - 15):idx]
        if not any(window.endswith(neg) for neg in NEGATION_PREFIXES):
            return True
        idx = text_lower.find(kw, idx + len(kw))
    return False


class TicketTriageAgent:
    """Hybrid ML + deterministic rule/tool triage agent."""

    def __init__(
        self,
        cat_pipeline: Pipeline | None = None,
        sev_pipeline: Pipeline | None = None,
        runbook_path: Path | None = None,
    ) -> None:
        self.cat_pipeline = cat_pipeline
        self.sev_pipeline = sev_pipeline
        target_runbook = runbook_path or resolve_runbook_path()
        self.runbook = json.loads(target_runbook.read_text(encoding="utf-8"))
        self.recent_tickets: list[dict[str, str]] = []

    @classmethod
    def from_disk(cls, models_dir: Path | None = None) -> "TicketTriageAgent":
        target_models_dir = models_dir or resolve_models_dir()
        cat_path = target_models_dir / "category_pipeline.joblib"
        sev_path = target_models_dir / "severity_pipeline.joblib"
        if not cat_path.exists() or not sev_path.exists():
            # In serverless environments (e.g. Vercel), the filesystem is read-only outside /tmp.
            # Train in-memory or save only if the target directory is writable.
            from backend.train import train_and_save_models
            try:
                cat_pipe, sev_pipe = train_and_save_models(models_dir=target_models_dir)
            except (OSError, PermissionError):
                # Target models directory is read-only; train in memory without disk save
                import tempfile
                with tempfile.TemporaryDirectory() as tmp_dir:
                    cat_pipe, sev_pipe = train_and_save_models(models_dir=Path(tmp_dir))
            return cls(cat_pipeline=cat_pipe, sev_pipeline=sev_pipe)
        return cls(
            cat_pipeline=joblib.load(cat_path),
            sev_pipeline=joblib.load(sev_path),
        )

    def normalize_and_extract(self, text: str) -> dict[str, Any]:
        """Tool 1: Clean text and extract equipment IDs & site hints."""
        return extract_entities(text)

    def _top_contributing_terms(self, pipeline: Pipeline, clean_text: str, asset_type: str, pred_class: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Extract top positive contributing word n-grams for explainability."""
        try:
            pre = pipeline.named_steps["features"]
            clf = pipeline.named_steps["clf"]
            X_df = pd.DataFrame([{"clean_text": clean_text, "asset_type": asset_type}])
            X_vec = pre.transform(X_df)
            feature_names = pre.get_feature_names_out()
            class_idx = list(clf.classes_).index(pred_class)
            coefs = clf.coef_[class_idx]
            contributions = X_vec.toarray()[0] * coefs
            top_indices = np.argsort(contributions)[::-1]
            terms: list[dict[str, Any]] = []
            for idx in top_indices:
                if contributions[idx] <= 0:
                    break
                fname = str(feature_names[idx])
                if fname.startswith("word_tfidf__"):
                    term = fname.replace("word_tfidf__", "")
                    terms.append({"term": term, "weight": round(float(contributions[idx]), 3)})
                elif fname.startswith("asset_ohe__"):
                    term = fname.replace("asset_ohe__", "")
                    terms.append({"term": term, "weight": round(float(contributions[idx]), 3)})
                if len(terms) >= top_k:
                    break
            return terms
        except Exception:
            return []

    def classify_ticket(self, clean_text: str, asset_type: str) -> dict[str, Any]:
        """Tool 2: Predict category & severity with probabilities and top contributing terms."""
        assert self.cat_pipeline is not None and self.sev_pipeline is not None
        X_df = pd.DataFrame([{"clean_text": clean_text, "asset_type": asset_type}])

        cat_probs_arr = self.cat_pipeline.predict_proba(X_df)[0]
        cat_classes = list(self.cat_pipeline.classes_)
        cat_probs = {str(c): round(float(p), 4) for c, p in zip(cat_classes, cat_probs_arr)}
        sorted_cats = sorted(cat_probs.items(), key=lambda x: x[1], reverse=True)
        pred_cat, cat_conf = sorted_cats[0]
        cat_margin = round(cat_conf - (sorted_cats[1][1] if len(sorted_cats) > 1 else 0.0), 4)

        sev_probs_arr = self.sev_pipeline.predict_proba(X_df)[0]
        sev_classes = list(self.sev_pipeline.classes_)
        sev_probs = {str(s): round(float(p), 4) for s, p in zip(sev_classes, sev_probs_arr)}
        sorted_sevs = sorted(sev_probs.items(), key=lambda x: x[1], reverse=True)
        pred_sev, sev_conf = sorted_sevs[0]

        top_terms = self._top_contributing_terms(self.cat_pipeline, clean_text, asset_type, pred_cat, top_k=5)

        return {
            "category": pred_cat,
            "category_confidence": cat_conf,
            "category_margin": cat_margin,
            "category_probabilities": dict(sorted_cats[:3]),
            "severity": pred_sev,
            "severity_confidence": sev_conf,
            "severity_probabilities": sev_probs,
            "top_contributing_terms": top_terms,
        }

    def safety_guardrail(self, raw_text: str, ml_severity: str) -> dict[str, Any]:
        """Tool 3: Deterministic escalate-only safety guardrail. Never downgrades severity."""
        text_lower = raw_text.lower()
        final_severity = ml_severity
        fired_rules: list[dict[str, str]] = []
        safety_flag = False

        for rule_id, min_sev, keywords, reason in SAFETY_RULES:
            matched_kws = [kw for kw in keywords if _keyword_present_unnegated(text_lower, kw)]
            if matched_kws:
                safety_flag = True
                escalated = SEVERITY_TO_INT[min_sev] > SEVERITY_TO_INT[final_severity]
                if escalated:
                    final_severity = min_sev
                fired_rules.append({
                    "rule_id": rule_id,
                    "matched_keywords": ", ".join(matched_kws),
                    "escalated_to": min_sev if escalated else "already_at_or_above",
                    "reason": reason,
                })

        return {
            "ml_severity": ml_severity,
            "final_severity": final_severity,
            "escalated": final_severity != ml_severity,
            "safety_flag": safety_flag,
            "fired_rules": fired_rules,
        }

    def lookup_runbook(self, category: str, clean_text: str) -> dict[str, Any]:
        """Tool 4: Retrieve relevant probable causes and next actions via TF-IDF cosine similarity."""
        cat_block = self.runbook.get(category)
        if not cat_block:
            return {
                "retrieval_method": "TF-IDF cosine similarity over local data/runbook.json",
                "runbook_id": "RB-DEFAULT",
                "owner_team": "O&M Operations Desk",
                "asset_criticality": 0.60,
                "generation_loss_risk": 0.50,
                "probable_causes": ["General equipment fault; inspect asset logs"],
                "next_actions": ["Dispatch shift technician for visual and SCADA check"],
            }

        entries = cat_block["entries"]
        if len(entries) == 1:
            best = entries[0]
            sim_score = 1.0
        else:
            corpus = [e["keywords"] for e in entries] + [clean_text]
            vec = TfidfVectorizer().fit_transform(corpus)
            sims = cosine_similarity(vec[-1:], vec[:-1])[0]
            best_idx = int(np.argmax(sims))
            best = entries[best_idx]
            sim_score = round(float(sims[best_idx]), 4)

        return {
            "retrieval_method": "TF-IDF cosine similarity over local data/runbook.json",
            "runbook_id": best["id"],
            "similarity_score": sim_score,
            "owner_team": cat_block["owner_team"],
            "asset_criticality": cat_block["asset_criticality"],
            "generation_loss_risk": cat_block["generation_loss_risk"],
            "probable_causes": best["probable_causes"],
            "next_actions": best["next_actions"],
        }

    def check_duplicates(self, clean_text: str, asset_type: str, recent_tickets: list[dict[str, str]] | None = None) -> dict[str, Any]:
        """Tool 5: Flag probable duplicate or repeat faults using token Jaccard similarity."""
        pool = recent_tickets if recent_tickets is not None else self.recent_tickets
        tokens_a = set(re.findall(r"[a-z0-9\-]+", clean_text))
        matches: list[dict[str, Any]] = []

        for prev in pool[-50:]:
            if prev.get("asset_type") != asset_type:
                continue
            tokens_b = set(re.findall(r"[a-z0-9\-]+", prev.get("clean_text", "")))
            if not tokens_a or not tokens_b:
                continue
            jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
            if jaccard >= 0.65:
                matches.append({"ticket_id": prev.get("ticket_id", "unknown"), "similarity": round(jaccard, 3)})

        return {
            "duplicate_count": len(matches),
            "is_repeat_fault": len(matches) > 0,
            "matched_tickets": matches[:3],
        }

    def run(self, description: str, asset_type: str, ticket_id: str | None = None, record_history: bool = True) -> dict[str, Any]:
        """Execute the full triage agent pipeline and return structured result + trace."""
        trace: list[dict[str, Any]] = []
        asset = asset_type.strip().lower()

        # Step 1: normalize_and_extract
        ent = self.normalize_and_extract(description)
        trace.append({
            "step": 1,
            "tool": "normalize_and_extract",
            "output": {
                "clean_text": ent["clean_text"],
                "equipment_ids": ent["equipment_ids"],
                "site_hints": ent["site_hints"],
            },
        })

        # Step 2: classify_ticket
        cls_res = self.classify_ticket(ent["clean_text"], asset)
        trace.append({
            "step": 2,
            "tool": "classify_ticket",
            "output": {
                "category": cls_res["category"],
                "category_confidence": cls_res["category_confidence"],
                "category_margin": cls_res["category_margin"],
                "ml_severity": cls_res["severity"],
                "severity_confidence": cls_res["severity_confidence"],
            },
        })

        # Step 3: safety_guardrail
        guard = self.safety_guardrail(description, cls_res["severity"])
        trace.append({
            "step": 3,
            "tool": "safety_guardrail",
            "output": guard,
        })

        # Step 4: lookup_runbook
        rb = self.lookup_runbook(cls_res["category"], ent["clean_text"])
        trace.append({
            "step": 4,
            "tool": "lookup_runbook",
            "output": {
                "runbook_id": rb["runbook_id"],
                "retrieval_method": rb["retrieval_method"],
                "owner_team": rb["owner_team"],
            },
        })

        # Step 5: check_duplicates
        dup = self.check_duplicates(ent["clean_text"], asset)
        trace.append({
            "step": 5,
            "tool": "check_duplicates",
            "output": dup,
        })

        # Step 6: compute_priority
        prio = compute_priority(
            severity=guard["final_severity"],
            asset_criticality=rb["asset_criticality"],
            generation_loss_risk=rb["generation_loss_risk"],
            safety_flag=guard["safety_flag"],
            duplicate_count=dup["duplicate_count"],
        )
        trace.append({
            "step": 6,
            "tool": "compute_priority",
            "output": prio,
        })

        # Step 7: route_ticket
        routing = route_ticket(
            category=cls_res["category"],
            asset_type=asset,
            severity=guard["final_severity"],
            priority_score=prio["priority_score"],
            runbook_owner=rb["owner_team"],
        )
        trace.append({
            "step": 7,
            "tool": "route_ticket",
            "output": routing,
        })

        # Step 8: Confidence gate
        review_reasons: list[str] = []
        if cls_res["category_confidence"] < CATEGORY_CONF_THRESHOLD:
            review_reasons.append(f"Low category confidence ({cls_res['category_confidence']:.2f} < {CATEGORY_CONF_THRESHOLD})")
        if cls_res["category_margin"] < TOP2_MARGIN_THRESHOLD:
            review_reasons.append(f"Close top-2 categories (margin {cls_res['category_margin']:.2f} < {TOP2_MARGIN_THRESHOLD})")
        if cls_res["severity_confidence"] < SEVERITY_CONF_THRESHOLD and not guard["escalated"]:
            review_reasons.append(f"Low severity confidence ({cls_res['severity_confidence']:.2f} < {SEVERITY_CONF_THRESHOLD})")

        needs_human_review = len(review_reasons) > 0
        trace.append({
            "step": 8,
            "tool": "confidence_gate",
            "output": {
                "needs_human_review": needs_human_review,
                "reasons": review_reasons,
            },
        })

        structured = {
            "ticket_id": ticket_id or "ADHOC",
            "asset_type": asset,
            "category": cls_res["category"],
            "severity": guard["final_severity"],
            "ml_severity": guard["ml_severity"],
            "guardrail_escalated": guard["escalated"],
            "priority_score": prio["priority_score"],
            "priority_formula": prio["formula"],
            "priority_components": prio["components"],
            "owner_team": routing["owner_team"],
            "sla_hours": routing["sla_hours"],
            "sla_label": routing["sla_label"],
            "escalation_tier": routing["escalation_tier"],
            "confidence": {
                "category": cls_res["category_confidence"],
                "severity": cls_res["severity_confidence"],
                "top2_category_margin": cls_res["category_margin"],
            },
            "needs_human_review": needs_human_review,
            "review_reasons": review_reasons,
            "equipment_ids": ent["equipment_ids"],
            "site_hints": ent["site_hints"],
            "probable_causes": rb["probable_causes"],
            "next_actions": rb["next_actions"],
            "top_contributing_terms": cls_res["top_contributing_terms"],
            "category_probabilities": cls_res["category_probabilities"],
            "duplicate_info": dup,
        }

        # Step 9: Optional LLM explanation (off by default -> deterministic template)
        expl = generate_explanation(structured)
        structured["explanation"] = expl["explanation"]
        structured["explanation_source"] = expl["explanation_source"]
        trace.append({
            "step": 9,
            "tool": "explanation_layer",
            "output": {"explanation_source": expl["explanation_source"]},
        })

        structured["agent_trace"] = trace

        if record_history:
            self.recent_tickets.append({
                "ticket_id": structured["ticket_id"],
                "asset_type": asset,
                "clean_text": ent["clean_text"],
            })

        return structured
