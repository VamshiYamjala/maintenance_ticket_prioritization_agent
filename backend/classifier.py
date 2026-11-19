"""
Machine Learning Classifier module for Maintenance Ticket Prioritization.

Uses a simple, transparent, and explainable approach:
- TF-IDF Vectorizer (word unigrams + bigrams)
- Multi-output K-Nearest Neighbors (KNN with n_neighbors=1 and cosine metric)

Trained strictly on the original supplied dataset:
`data/maintenance_tickets.csv` (6 labelled examples).

KNN is an instance-based learning algorithm. It stores the vector representations
of the 6 reference tickets and finds the most similar labelled ticket using cosine distance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KNeighborsClassifier

from backend.preprocessing import prepare_input

# Path to the authoritative 6-row CSV dataset
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "data" / "maintenance_tickets.csv"


class TicketClassifier:
    """
    Instance-based Ticket Classifier using TF-IDF and K-Nearest Neighbors.
    Predicts both category and severity simultaneously using multi-output KNN.
    """

    def __init__(self, data_path: Path = DATA_PATH) -> None:
        self.data_path = data_path
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        self.knn = KNeighborsClassifier(n_neighbors=1, metric="cosine", algorithm="brute")
        self.reference_df: pd.DataFrame | None = None
        self._is_fitted = False
        self._fit_model()

    def _fit_model(self) -> None:
        """Loads data/maintenance_tickets.csv and fits the vectorizer and KNN model."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Training dataset not found at: {self.data_path}")

        df = pd.read_csv(self.data_path)
        self.reference_df = df.copy()

        # Build feature text by combining asset_type and description
        feature_texts = [
            prepare_input(row["description"], row["asset_type"])
            for _, row in df.iterrows()
        ]

        # Multi-output target: column 0 is target_category, column 1 is target_severity
        targets = np.column_stack([
            df["target_category"].astype(str).values,
            df["target_severity"].astype(str).values,
        ])

        # Fit TF-IDF representation and KNN classifier
        X_vec = self.vectorizer.fit_transform(feature_texts)
        self.knn.fit(X_vec, targets)
        self._is_fitted = True

    def predict(self, description: str, asset_type: str | None = None) -> dict[str, Any]:
        """
        Classifies an incoming ticket description using nearest-neighbor similarity.

        Args:
            description: Maintenance ticket observation string.
            asset_type: Optional asset type ('solar', 'wind', 'hydro', 'grid').

        Returns:
            Dictionary containing:
            - predicted_category: Nearest sample's category
            - predicted_severity: Nearest sample's initial severity
            - similarity_score: Cosine similarity to the nearest sample (0.0 to 1.0)
            - matched_sample: Full dictionary of the nearest reference ticket
        """
        if not self._is_fitted or self.reference_df is None:
            self._fit_model()

        # Preprocess query text
        query_text = prepare_input(description, asset_type)
        query_vec = self.vectorizer.transform([query_text])

        # Predict multi-output targets (category and severity)
        prediction = self.knn.predict(query_vec)[0]
        predicted_category = str(prediction[0])
        predicted_severity = str(prediction[1])

        # Retrieve nearest neighbor distance and index
        distances, indices = self.knn.kneighbors(query_vec, n_neighbors=1)
        cosine_distance = float(distances[0][0])
        nearest_idx = int(indices[0][0])

        # Convert cosine distance (0.0 to 2.0) into cosine similarity (0.0 to 1.0)
        similarity_score = max(0.0, min(1.0, 1.0 - cosine_distance))

        # Retrieve matched reference ticket details
        matched_row = self.reference_df.iloc[nearest_idx]
        matched_sample = {
            "ticket_id": str(matched_row["ticket_id"]),
            "asset_type": str(matched_row["asset_type"]),
            "description": str(matched_row["description"]),
            "target_severity": str(matched_row["target_severity"]),
            "target_category": str(matched_row["target_category"]),
        }

        return {
            "predicted_category": predicted_category,
            "predicted_severity": predicted_severity,
            "similarity_score": round(similarity_score, 4),
            "confidence": round(similarity_score, 4),
            "matched_sample": matched_sample,
        }


# Global singleton instance (initialized once at server startup)
_classifier_instance: TicketClassifier | None = None


def get_classifier() -> TicketClassifier:
    """Returns the singleton TicketClassifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = TicketClassifier()
    return _classifier_instance
