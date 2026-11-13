"""
Model training pipeline for Maintenance Ticket Prioritization.

Trains two separate scikit-learn pipelines (category multi-class classifier and
severity ordinal classifier) using TF-IDF (word + char_wb n-grams) + asset_type OHE
with LogisticRegression(class_weight="balanced").
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.svm import LinearSVC

from backend.preprocessing import load_tickets

BASE_DIR = Path(__file__).resolve().parents[1]
BUNDLED_DATA = BASE_DIR / "data" / "maintenance_tickets.csv"
SYNTHETIC_DATA = BASE_DIR / "data" / "maintenance_tickets_synthetic.csv"
MODELS_DIR = BASE_DIR / "models"

SEED = 42


def build_preprocessor(use_char: bool = True, use_asset: bool = True) -> ColumnTransformer:
    """Build ColumnTransformer for clean_text and asset_type."""
    transformers: list[tuple[str, Any, Any]] = [
        (
            "word_tfidf",
            TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
            "clean_text",
        )
    ]
    if use_char:
        transformers.append(
            (
                "char_tfidf",
                TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, sublinear_tf=True),
                "clean_text",
            )
        )
    if use_asset:
        transformers.append(
            (
                "asset_ohe",
                OneHotEncoder(handle_unknown="ignore"),
                ["asset_type"],
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop")


def build_logreg_pipeline(
    c_val: float = 2.0,
    use_char: bool = True,
    use_asset: bool = True,
) -> Pipeline:
    """Build TF-IDF + OHE + LogisticRegression pipeline."""
    return Pipeline(
        steps=[
            ("features", build_preprocessor(use_char=use_char, use_asset=use_asset)),
            (
                "clf",
                LogisticRegression(
                    C=c_val,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=SEED,
                ),
            ),
        ]
    )


def build_alternative_pipeline(model_name: str) -> Pipeline:
    """Build alternative classifier pipelines for model comparison."""
    pre = build_preprocessor(use_char=True, use_asset=True)
    if model_name == "linear_svc":
        clf = LinearSVC(C=1.0, class_weight="balanced", random_state=SEED)
    elif model_name == "multinomial_nb":
        clf = MultinomialNB(alpha=0.5)
    else:
        raise ValueError(f"Unknown alternative model: {model_name}")
    return Pipeline(steps=[("features", pre), ("clf", clf)])


def train_and_save_models(
    df: pd.DataFrame | None = None,
    models_dir: Path = MODELS_DIR,
) -> tuple[Pipeline, Pipeline]:
    """Train category & severity LogisticRegression pipelines on full dataset and save."""
    if df is None:
        df = load_tickets(BUNDLED_DATA, SYNTHETIC_DATA, include_synthetic=True)

    X = df[["clean_text", "asset_type"]]
    y_cat = df["target_category"]
    y_sev = df["target_severity"]

    cat_pipe = build_logreg_pipeline(c_val=2.0)
    sev_pipe = build_logreg_pipeline(c_val=2.0)

    cat_pipe.fit(X, y_cat)
    sev_pipe.fit(X, y_sev)

    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(cat_pipe, models_dir / "category_pipeline.joblib")
    joblib.dump(sev_pipe, models_dir / "severity_pipeline.joblib")

    return cat_pipe, sev_pipe


if __name__ == "__main__":
    cat_m, sev_m = train_and_save_models()
    print(f"Saved category and severity pipelines to {MODELS_DIR}")
