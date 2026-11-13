"""
Reproducible evaluation script:
- Stratified train/test split (no leakage, deduplicated first)
- 5-fold StratifiedKFold cross-validation (mean +/- std)
- Baseline (keyword + majority) vs LogisticRegression vs LinearSVC vs MultinomialNB
- Safety-oriented metrics: critical_recall, under_triage_rate, over_triage_rate, ordinal severity error
- Separate evaluation on hand-written challenge set (data/challenge_tickets.csv)
- Feature ablation (no asset_type, no char n-grams)
- Saves docs/evaluation_results.json and trains final models on full data

Run with: python -m backend.evaluate
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, train_test_split

from backend.preprocessing import (
    SEVERITY_LEVELS,
    SEVERITY_TO_INT,
    load_tickets,
    normalize_text,
)
from backend.train import (
    BASE_DIR,
    BUNDLED_DATA,
    MODELS_DIR,
    SEED,
    SYNTHETIC_DATA,
    build_alternative_pipeline,
    build_logreg_pipeline,
    train_and_save_models,
)

CHALLENGE_DATA = BASE_DIR / "data" / "challenge_tickets.csv"
DOCS_DIR = BASE_DIR / "docs"
EVAL_JSON_PATH = DOCS_DIR / "evaluation_results.json"

KEYWORD_CATEGORY_RULES = [
    ("safety_incident", ["smoke", "fire", "arc flash", "sparks", "burning", "evacuated", "near-miss", "injury"]),
    ("gearbox_vibration", ["gearbox", "gearbx", "vibration", "vibraton", "cms", "bearing", "nacelle"]),
    ("inverter_thermal", ["inverter", "invertr", "igbt", "heatsink", "mppt", "thermal"]),
    ("pitch_system", ["pitch", "feather", "blade", "gust"]),
    ("transformer_fault", ["transformer", "transfrmer", "buchholz", "oltc", "winding", "oil leak"]),
    ("grid_curtailment", ["curtailment", "curtailmnt", "sldc", "ppc", "setpoint", "dispatch"]),
    ("communication_loss", ["rtu", "modbus", "fiber", "ping", "offline", "comm fail", "gateway"]),
    ("data_gap", ["scada", "historian", "flatline", "nan", "missing", "mising", "pyranometer"]),
    ("tracker_fault", ["tracker", "stow", "slew", "ncu", "inclinometer"]),
    ("inspection_compliance", ["inspection", "inspectn", "checklist", "audit", "compliance", "certificate"]),
]


def keyword_baseline_predict(df: pd.DataFrame, majority_cat: str, majority_sev: str) -> tuple[list[str], list[str]]:
    """Simple interpretable keyword + majority baseline."""
    cat_preds: list[str] = []
    sev_preds: list[str] = []
    for text in df["clean_text"]:
        matched_cat = majority_cat
        for cat, kws in KEYWORD_CATEGORY_RULES:
            if any(kw in text for kw in kws):
                matched_cat = cat
                break
        cat_preds.append(matched_cat)

        if any(w in text for w in ["smoke", "fire", "arc flash", "critical", "evacuated", "shutdown", "trip"]):
            sev_preds.append("critical")
        elif any(w in text for w in ["high", "tripping", "overdue", "leak", "alarm", "fault"]):
            sev_preds.append("high")
        elif any(w in text for w in ["minor", "routine", "recovered", "slightly"]):
            sev_preds.append("low")
        else:
            sev_preds.append(majority_sev)
    return cat_preds, sev_preds


def compute_severity_safety_metrics(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    """Compute ordinal severity safety metrics. Sign convention: error = pred - actual."""
    true_idx = np.array([SEVERITY_TO_INT[s] for s in y_true])
    pred_idx = np.array([SEVERITY_TO_INT[s] for s in y_pred])
    errors = pred_idx - true_idx  # negative = under-triaged (dangerous)

    crit_mask = true_idx == SEVERITY_TO_INT["critical"]
    crit_recall = float(np.mean(pred_idx[crit_mask] == SEVERITY_TO_INT["critical"])) if crit_mask.any() else 0.0

    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "critical_recall": round(crit_recall, 4),
        "under_triage_rate": round(float(np.mean(errors < 0)), 4),
        "over_triage_rate": round(float(np.mean(errors > 0)), 4),
        "exact_severity_rate": round(float(np.mean(errors == 0)), 4),
        "mean_ordinal_error": round(float(np.mean(errors)), 4),
        "mae_ordinal": round(float(np.mean(np.abs(errors))), 4),
    }


def run_cv(df: pd.DataFrame, n_splits: int = 5) -> dict[str, Any]:
    """Run stratified k-fold cross-validation and return mean +/- std."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    X = df[["clean_text", "asset_type"]]
    y_cat = df["target_category"].values
    y_sev = df["target_severity"].values

    cat_acc, cat_f1, sev_acc, sev_f1, crit_rec, under_tr = [], [], [], [], [], []
    for train_idx, val_idx in skf.split(X, y_cat):
        X_tr, X_va = X.iloc[train_idx], X.iloc[val_idx]
        cat_pipe = build_logreg_pipeline(c_val=2.0)
        sev_pipe = build_logreg_pipeline(c_val=2.0)

        cat_pipe.fit(X_tr, y_cat[train_idx])
        sev_pipe.fit(X_tr, y_sev[train_idx])

        c_pred = cat_pipe.predict(X_va)
        s_pred = sev_pipe.predict(X_va)

        cat_acc.append(accuracy_score(y_cat[val_idx], c_pred))
        cat_f1.append(f1_score(y_cat[val_idx], c_pred, average="macro", zero_division=0))
        s_metrics = compute_severity_safety_metrics(list(y_sev[val_idx]), list(s_pred))
        sev_acc.append(s_metrics["accuracy"])
        sev_f1.append(s_metrics["macro_f1"])
        crit_rec.append(s_metrics["critical_recall"])
        under_tr.append(s_metrics["under_triage_rate"])

    def stat(arr: list[float]) -> dict[str, float]:
        return {"mean": round(float(np.mean(arr)), 4), "std": round(float(np.std(arr)), 4)}

    return {
        "n_splits": n_splits,
        "category_accuracy": stat(cat_acc),
        "category_macro_f1": stat(cat_f1),
        "severity_accuracy": stat(sev_acc),
        "severity_macro_f1": stat(sev_f1),
        "critical_recall": stat(crit_rec),
        "under_triage_rate": stat(under_tr),
    }


def evaluate_all() -> dict[str, Any]:
    df = load_tickets(BUNDLED_DATA, SYNTHETIC_DATA, include_synthetic=True)
    challenge_df = pd.read_csv(CHALLENGE_DATA, comment="#")
    challenge_df["asset_type"] = challenge_df["asset_type"].str.strip().str.lower()
    challenge_df["target_severity"] = challenge_df["target_severity"].str.strip().str.lower()
    challenge_df["target_category"] = challenge_df["target_category"].str.strip().str.lower()
    challenge_df["clean_text"] = challenge_df["description"].astype(str).apply(normalize_text)

    # Class balance
    cat_counts = df["target_category"].value_counts().to_dict()
    sev_counts = df["target_severity"].value_counts().to_dict()
    asset_counts = df["asset_type"].value_counts().to_dict()

    # Stratified split (80/20)
    train_df, test_df = train_test_split(
        df, test_size=0.20, random_state=SEED, stratify=df["target_category"]
    )
    X_train = train_df[["clean_text", "asset_type"]]
    X_test = test_df[["clean_text", "asset_type"]]
    X_chal = challenge_df[["clean_text", "asset_type"]]

    # 1. Baseline
    maj_cat = train_df["target_category"].mode()[0]
    maj_sev = train_df["target_severity"].mode()[0]
    base_cat_test, base_sev_test = keyword_baseline_predict(test_df, maj_cat, maj_sev)
    base_cat_chal, base_sev_chal = keyword_baseline_predict(challenge_df, maj_cat, maj_sev)

    # 2. Main model (LogisticRegression)
    cat_lr = build_logreg_pipeline(c_val=2.0)
    sev_lr = build_logreg_pipeline(c_val=2.0)
    cat_lr.fit(X_train, train_df["target_category"])
    sev_lr.fit(X_train, train_df["target_severity"])

    lr_cat_test = cat_lr.predict(X_test)
    lr_sev_test = sev_lr.predict(X_test)
    lr_cat_chal = cat_lr.predict(X_chal)
    lr_sev_chal = sev_lr.predict(X_chal)

    # 3. Alternatives: LinearSVC & MultinomialNB
    comparisons: list[dict[str, Any]] = [
        {
            "model": "Keyword + Majority Baseline",
            "test_category_acc": round(float(accuracy_score(test_df["target_category"], base_cat_test)), 4),
            "test_category_macro_f1": round(float(f1_score(test_df["target_category"], base_cat_test, average="macro", zero_division=0)), 4),
            "test_severity_metrics": compute_severity_safety_metrics(list(test_df["target_severity"]), base_sev_test),
            "challenge_category_macro_f1": round(float(f1_score(challenge_df["target_category"], base_cat_chal, average="macro", zero_division=0)), 4),
            "challenge_severity_metrics": compute_severity_safety_metrics(list(challenge_df["target_severity"]), base_sev_chal),
        },
        {
            "model": "TF-IDF + LogisticRegression (Main)",
            "test_category_acc": round(float(accuracy_score(test_df["target_category"], lr_cat_test)), 4),
            "test_category_macro_f1": round(float(f1_score(test_df["target_category"], lr_cat_test, average="macro", zero_division=0)), 4),
            "test_severity_metrics": compute_severity_safety_metrics(list(test_df["target_severity"]), list(lr_sev_test)),
            "challenge_category_macro_f1": round(float(f1_score(challenge_df["target_category"], lr_cat_chal, average="macro", zero_division=0)), 4),
            "challenge_severity_metrics": compute_severity_safety_metrics(list(challenge_df["target_severity"]), list(lr_sev_chal)),
        },
    ]

    for alt_name, label in [("linear_svc", "TF-IDF + LinearSVC"), ("multinomial_nb", "TF-IDF + MultinomialNB")]:
        c_alt = build_alternative_pipeline(alt_name)
        s_alt = build_alternative_pipeline(alt_name)
        c_alt.fit(X_train, train_df["target_category"])
        s_alt.fit(X_train, train_df["target_severity"])
        c_t = c_alt.predict(X_test)
        s_t = s_alt.predict(X_test)
        c_c = c_alt.predict(X_chal)
        s_c = s_alt.predict(X_chal)
        comparisons.append({
            "model": label,
            "test_category_acc": round(float(accuracy_score(test_df["target_category"], c_t)), 4),
            "test_category_macro_f1": round(float(f1_score(test_df["target_category"], c_t, average="macro", zero_division=0)), 4),
            "test_severity_metrics": compute_severity_safety_metrics(list(test_df["target_severity"]), list(s_t)),
            "challenge_category_macro_f1": round(float(f1_score(challenge_df["target_category"], c_c, average="macro", zero_division=0)), 4),
            "challenge_severity_metrics": compute_severity_safety_metrics(list(challenge_df["target_severity"]), list(s_c)),
        })

    # 4. Ablation on LogReg (remove asset_type, remove char n-grams)
    ablation: list[dict[str, Any]] = []
    for desc, u_char, u_asset in [
        ("Full (word + char + asset_type)", True, True),
        ("No asset_type (word + char)", True, False),
        ("No char n-grams (word + asset_type)", False, True),
    ]:
        c_ab = build_logreg_pipeline(c_val=2.0, use_char=u_char, use_asset=u_asset)
        s_ab = build_logreg_pipeline(c_val=2.0, use_char=u_char, use_asset=u_asset)
        c_ab.fit(X_train, train_df["target_category"])
        s_ab.fit(X_train, train_df["target_severity"])
        ablation.append({
            "variant": desc,
            "test_category_macro_f1": round(float(f1_score(test_df["target_category"], c_ab.predict(X_test), average="macro", zero_division=0)), 4),
            "test_severity_macro_f1": round(float(f1_score(test_df["target_severity"], s_ab.predict(X_test), average="macro", zero_division=0)), 4),
            "challenge_category_macro_f1": round(float(f1_score(challenge_df["target_category"], c_ab.predict(X_chal), average="macro", zero_division=0)), 4),
            "challenge_severity_macro_f1": round(float(f1_score(challenge_df["target_severity"], s_ab.predict(X_chal), average="macro", zero_division=0)), 4),
        })

    # 5. Confusion matrices & per-class report (test set + challenge set)
    cat_labels = sorted(df["target_category"].unique().tolist())
    sev_labels = list(SEVERITY_LEVELS)

    cat_cm_test = confusion_matrix(test_df["target_category"], lr_cat_test, labels=cat_labels).tolist()
    sev_cm_test = confusion_matrix(test_df["target_severity"], lr_sev_test, labels=sev_labels).tolist()
    sev_cm_chal = confusion_matrix(challenge_df["target_severity"], lr_sev_chal, labels=sev_labels).tolist()

    cat_report_test = classification_report(
        test_df["target_category"], lr_cat_test, labels=cat_labels, output_dict=True, zero_division=0
    )
    sev_report_test = classification_report(
        test_df["target_severity"], lr_sev_test, labels=sev_labels, output_dict=True, zero_division=0
    )

    # 6. Challenge set actual-vs-predicted table (first 12 rows + any misses)
    chal_rows: list[dict[str, Any]] = []
    for i, row in challenge_df.iterrows():
        act_sev = row["target_severity"]
        pred_sev = str(lr_sev_chal[i])
        sev_err = SEVERITY_TO_INT[pred_sev] - SEVERITY_TO_INT[act_sev]
        chal_rows.append({
            "ticket_id": row["ticket_id"],
            "asset_type": row["asset_type"],
            "description": row["description"],
            "actual_category": row["target_category"],
            "predicted_category": str(lr_cat_chal[i]),
            "actual_severity": act_sev,
            "predicted_severity": pred_sev,
            "severity_error": int(sev_err),
        })

    # 7. Cross-validation
    cv_results = run_cv(df, n_splits=5)

    # 8. Train & save final production pipelines on full deduplicated dataset
    train_and_save_models(df=df, models_dir=MODELS_DIR)

    results = {
        "dataset_summary": {
            "total_deduplicated_rows": int(len(df)),
            "bundled_rows": int((df["data_source"] == "bundled").sum()),
            "synthetic_rows": int((df["data_source"] != "bundled").sum()),
            "train_rows": int(len(train_df)),
            "test_rows": int(len(test_df)),
            "challenge_rows": int(len(challenge_df)),
            "category_counts": cat_counts,
            "severity_counts": sev_counts,
            "asset_counts": asset_counts,
        },
        "cross_validation": cv_results,
        "model_comparison": comparisons,
        "ablation": ablation,
        "category_labels": cat_labels,
        "severity_labels": sev_labels,
        "test_category_confusion_matrix": cat_cm_test,
        "test_severity_confusion_matrix": sev_cm_test,
        "challenge_severity_confusion_matrix": sev_cm_chal,
        "test_category_report": cat_report_test,
        "test_severity_report": sev_report_test,
        "challenge_predictions": chal_rows,
    }

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_JSON_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    res = evaluate_all()
    print("=== Evaluation Complete ===")
    print(f"Total rows (dedup): {res['dataset_summary']['total_deduplicated_rows']}")
    print(f"5-fold CV Category Macro-F1: {res['cross_validation']['category_macro_f1']}")
    print(f"5-fold CV Critical Recall:   {res['cross_validation']['critical_recall']}")
    print(f"5-fold CV Under-Triage Rate: {res['cross_validation']['under_triage_rate']}")
    for m in res["model_comparison"]:
        print(
            f"  {m['model']}: test_cat_f1={m['test_category_macro_f1']}, "
            f"test_crit_rec={m['test_severity_metrics']['critical_recall']}, "
            f"chal_cat_f1={m['challenge_category_macro_f1']}, "
            f"chal_under_triage={m['challenge_severity_metrics']['under_triage_rate']}"
        )
    print(f"Saved results to {EVAL_JSON_PATH}")
