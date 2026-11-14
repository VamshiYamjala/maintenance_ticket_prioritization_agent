"""
===============================================================================
FILE: backend/train.py
===============================================================================
1. WHAT THIS FILE DOES:
   Constructs the scikit-learn feature extraction and machine learning training
   pipelines, trains two independent models (Fault Category Multi-Class Classifier
   and Severity Ordinal Classifier), and serializes them to disk using Joblib.

2. WHY THIS FILE IS NEEDED:
   Machine learning requires combining tabular categorical metadata (`asset_type`)
   with unstructured free-text (`clean_text`). This file builds a unified ColumnTransformer
   that pairs word n-grams, character n-grams, and One-Hot Encoding into a balanced
   Logistic Regression pipeline.

3. WHICH OTHER FILES USE IT:
   - backend/evaluate.py: Imports `build_logreg_pipeline()`, `build_preprocessor()`,
     and `build_alternative_pipeline()` to run 5-fold cross-validation and benchmarks.
   - backend/agent.py: Calls `train_and_save_models()` as an automated fallback if
     model joblib files are missing upon server boot.

4. WHAT INPUT IT RECEIVES:
   - `data/maintenance_tickets.csv` and `data/maintenance_tickets_synthetic.csv`.

5. WHAT OUTPUT IT PRODUCES:
   - Serialized model files in `models/`:
     - `models/category_pipeline.joblib` (predicts 1 of 10 renewable fault categories)
     - `models/severity_pipeline.joblib` (predicts 1 of 4 severity levels: low, med, high, crit)
===============================================================================
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

# Fixed random seed for complete reproducibility
SEED = 42


def build_preprocessor(use_char: bool = True, use_asset: bool = True) -> ColumnTransformer:
    """
    1. WHAT IT DOES:
       Builds a scikit-learn ColumnTransformer that extracts multi-modal features
       from ticket descriptions and asset categories simultaneously.

    2. WHY WE NEED IT:
       A raw ticket contains both text ("Inverter tripping after noon") and a categorical
       asset type ("solar"). A ColumnTransformer allows running different feature extraction
       algorithms on different dataframe columns and concatenating them into a single sparse matrix.

    3. PARAMETERS:
       - use_char (bool): Whether to include character n-gram TF-IDF (default: True).
                          Used for ablation studies in `backend/evaluate.py`.
       - use_asset (bool): Whether to include OneHotEncoder for asset_type (default: True).
                           Used for ablation studies in `backend/evaluate.py`.

    4. RETURNS:
       ColumnTransformer: Configured preprocessor object ready for pipeline embedding.

    5. HOW IT WORKS INTERNALLY:
       Transformer 1 - Word TF-IDF on 'clean_text':
         - `ngram_range=(1, 2)`: Captures both unigrams ("inverter") and bigrams ("arc flash").
         - `min_df=2`: Ignores words appearing in only 1 ticket to reduce vocabulary noise.
         - `sublinear_tf=True`: Uses logarithmic term frequency 1 + log(tf) to prevent
           repeated words from dominating feature weights.

       Transformer 2 - Character n-gram TF-IDF on 'clean_text':
         - `analyzer='char_wb'`: Extracts character n-grams strictly within word boundaries.
         - `ngram_range=(3, 5)`: Captures 3-to-5 character substrings (e.g. "inv", "gear", "vibr").
         - Why it's crucial: Handles operator typos ("invertr", "gearbx") and plural variations
           without needing a massive dictionary.

       Transformer 3 - OneHotEncoder on 'asset_type':
         - Encodes 'solar', 'wind', 'hydro', and 'grid' into binary indicator columns.
         - `handle_unknown='ignore'`: Prevents crashes if an unexpected asset type is encountered.

    6. CALLED BY:
       - `build_logreg_pipeline()`
       - `build_alternative_pipeline()`
    """
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
    """
    1. WHAT IT DOES:
       Assembles the complete scikit-learn Pipeline linking the ColumnTransformer
       preprocessor directly to a balanced LogisticRegression classifier.

    2. WHY WE NEED IT:
       Packaging preprocessing and modeling inside an official Pipeline guarantees
       zero data leakage during cross-validation, and allows saving/loading the entire
       end-to-end transformation in a single `.joblib` file.

    3. PARAMETERS:
       - c_val (float): Inverse regularization strength (default: 2.0).
                        Slightly higher C gives more weight to training data while maintaining
                        L2 regularization against overfitting.
       - use_char (bool): Enable/disable char n-grams.
       - use_asset (bool): Enable/disable asset OneHotEncoder.

    4. RETURNS:
       Pipeline: Combined (features + clf) model object.

    5. WHY LOGISTIC REGRESSION WAS CHOSEN (INTERVIEW EXPLANATION):
       - Transparency & Explainability: Model weights (`clf.coef_`) map directly back to
         word tokens, powering the UI's "Why Did the AI Make This Decision?" feature.
       - Calibrated Probabilities: `predict_proba()` produces true softmax probabilities
         needed by the Confidence Gate.
       - Class Imbalance Protection: `class_weight='balanced'` automatically adjusts weights
         inversely proportional to class frequencies, ensuring minority critical faults
         (e.g. fire/smoke) are not ignored in favor of frequent routine categories.
       - Microsecond Inference: Executes in <2 milliseconds with near-zero memory, ideal
         for serverless cloud execution.

    6. CALLED BY:
       - `train_and_save_models()`
       - `backend/evaluate.py` for cross-validation and ablation.
    """
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
    """
    1. WHAT IT DOES:
       Builds alternative baseline model pipelines (Linear Support Vector Classifier
       or Multinomial Naive Bayes) for benchmark comparison in evaluation tests.

    2. WHY WE NEED IT:
       In a rigorous machine learning project, you must prove that your chosen model
       outperforms standard baselines. This function allows automated model comparison.

    3. PARAMETERS:
       - model_name (str): Either 'linear_svc' or 'multinomial_nb'.

    4. RETURNS:
       Pipeline: Alternative feature + classifier pipeline.

    5. CALLED BY:
       - `backend/evaluate.py::evaluate_all()`
    """
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
    """
    1. WHAT IT DOES:
       Trains both the Category and Severity Logistic Regression pipelines on the
       full deduplicated ticket dataset and writes them to disk as Joblib files.

    2. WHY WE NEED IT:
       Produces the serialized model artifacts (`category_pipeline.joblib` and
       `severity_pipeline.joblib`) that the FastAPI server loads into memory on startup
       for instantaneous inference.

    3. PARAMETERS:
       - df (pd.DataFrame | None): Dataset to train on. If None, automatically loads
                                   via `load_tickets()`.
       - models_dir (Path): Destination folder for `.joblib` files.

    4. RETURNS:
       tuple[Pipeline, Pipeline]: (category_pipeline, severity_pipeline)

    5. HOW IT WORKS INTERNALLY:
       Step 1: Ingests tickets and separates features X = ['clean_text', 'asset_type'].
       Step 2: Sets target y_cat = 'target_category' (10 classes).
       Step 3: Sets target y_sev = 'target_severity' (4 classes).
       Step 4: Fits both pipelines.
       Step 5: Creates `models/` directory if missing and dumps joblib binaries.

    6. CALLED BY:
       - `python -m backend.train` (CLI execution).
       - `backend/agent.py::TicketTriageAgent.from_disk()` if artifacts are absent.
    """
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
    cat_model, sev_model = train_and_save_models()
    print("Training complete!")
    print(f"Category classes ({len(cat_model.classes_)}): {list(cat_model.classes_)}")
    print(f"Severity classes ({len(sev_model.classes_)}): {list(sev_model.classes_)}")
