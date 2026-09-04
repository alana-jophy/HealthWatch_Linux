"""AI-Assisted Outbreak Risk Predictor Service using scikit-learn."""

import datetime
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger
from sklearn.ensemble import RandomForestClassifier

from app.schemas.prediction import (
    AreaOutbreakPrediction,
    OutbreakPredictionInput,
    PredictedTrendEnum,
    RiskLevelEnum,
)


class OutbreakPredictorService:
    """
    Explainable Outbreak Risk Estimation Service using scikit-learn.
    Decision-support feature only; not a clinical or medical diagnosis tool.
    """

    _model: Optional[RandomForestClassifier] = None
    _feature_names: List[str] = [
        "recent_cases",
        "historical_cases",
        "case_growth_rate",
        "r0_estimate",
        "is_contagious",
        "spatial_density",
        "potential_exposures",
    ]

    @classmethod
    def get_or_train_model(cls) -> RandomForestClassifier:
        """Initialize or retrieve singleton explainable Random Forest model."""
        if cls._model is not None:
            return cls._model

        # Train on calibrated synthetic epidemiological profiles
        # Features: [recent_cases, historical_cases, growth_rate, r0, is_contagious, density, exposures]
        X_train = np.array([
            # LOW RISK samples (minimal cases, negative/flat growth, low exposures)
            [0, 2, -1.0, 1.2, 1, 0.2, 0],
            [1, 5, -0.8, 1.5, 1, 0.5, 0],
            [2, 8, -0.7, 0.0, 0, 0.3, 0],
            [0, 0, 0.0, 1.8, 1, 0.1, 0],
            [1, 3, -0.6, 2.0, 1, 0.4, 1],

            # MEDIUM RISK samples (moderate cases, moderate growth, localized density)
            [5, 4, 0.25, 1.5, 1, 1.2, 2],
            [6, 6, 0.0, 1.8, 1, 1.5, 3],
            [8, 10, -0.2, 2.2, 1, 1.8, 2],
            [4, 2, 1.0, 1.4, 1, 0.9, 1],
            [7, 5, 0.4, 1.6, 1, 1.4, 3],

            # HIGH RISK samples (surging cases, high growth, high R0, multiple exposures)
            [15, 6, 1.5, 2.2, 1, 3.0, 6],
            [18, 8, 1.25, 2.5, 1, 3.5, 8],
            [12, 5, 1.4, 1.9, 1, 2.8, 5],
            [20, 10, 1.0, 2.4, 1, 4.0, 7],
            [16, 7, 1.28, 2.0, 1, 3.2, 6],

            # CRITICAL RISK samples (extreme growth, severe clustering, dense exposures)
            [30, 10, 2.0, 2.5, 1, 6.0, 15],
            [45, 12, 2.75, 2.8, 1, 8.0, 20],
            [35, 8, 3.37, 2.4, 1, 7.5, 18],
            [50, 15, 2.33, 2.6, 1, 9.0, 25],
            [40, 9, 3.44, 2.5, 1, 7.0, 16],
        ])

        # Target classes: 0 = LOW, 1 = MEDIUM, 2 = HIGH, 3 = CRITICAL
        y_train = np.array([
            0, 0, 0, 0, 0,
            1, 1, 1, 1, 1,
            2, 2, 2, 2, 2,
            3, 3, 3, 3, 3,
        ])

        model = RandomForestClassifier(
            n_estimators=50,
            max_depth=5,
            random_state=42,
            class_weight="balanced",
        )
        model.fit(X_train, y_train)
        cls._model = model
        logger.info("OutbreakPredictorService: Trained explainable RandomForestClassifier with 50 estimators.")
        return cls._model

    @classmethod
    def predict_risk(cls, features: OutbreakPredictionInput, area_name: str = "Surveillance Area", disease_name: str = "Monitored Disease") -> AreaOutbreakPrediction:
        """Run ML inference for given feature payload with explainability."""
        model = cls.get_or_train_model()

        # Derive growth rate if not provided
        if features.case_growth_rate is not None:
            growth = features.case_growth_rate
        else:
            denom = max(features.historical_case_count, 1)
            growth = round((features.recent_case_count - features.historical_case_count) / denom, 2)

        contagious_val = 1 if features.is_contagious else 0
        input_vector = np.array([[
            features.recent_case_count,
            features.historical_case_count,
            growth,
            features.disease_r0_estimate,
            contagious_val,
            features.spatial_case_density,
            features.potential_exposure_count,
        ]])

        # Predict probabilities across classes [LOW, MEDIUM, HIGH, CRITICAL]
        probabilities = model.predict_proba(input_vector)[0]
        # In case some classes weren't encountered in predict_proba
        classes = model.classes_
        class_prob_map = {cls_id: prob for cls_id, prob in zip(classes, probabilities)}

        # Continuous risk score: weighted combination (0 to 1)
        risk_score = round(
            class_prob_map.get(0, 0.0) * 0.1 +
            class_prob_map.get(1, 0.0) * 0.45 +
            class_prob_map.get(2, 0.0) * 0.75 +
            class_prob_map.get(3, 0.0) * 0.95,
            2
        )
        risk_score = max(0.0, min(1.0, risk_score))

        # Risk level categorization
        if risk_score < 0.35:
            risk_level = RiskLevelEnum.LOW
        elif risk_score < 0.65:
            risk_level = RiskLevelEnum.MEDIUM
        elif risk_score < 0.85:
            risk_level = RiskLevelEnum.HIGH
        else:
            risk_level = RiskLevelEnum.CRITICAL

        # Predicted trend based on growth rate & recent cases
        if growth >= 1.0:
            trend = PredictedTrendEnum.SURGING
        elif growth > 0.1:
            trend = PredictedTrendEnum.INCREASING
        elif growth >= -0.2:
            trend = PredictedTrendEnum.STABLE
        else:
            trend = PredictedTrendEnum.DECLINING

        # Feature contributions via Random Forest feature importances
        raw_importances = model.feature_importances_
        feature_contributions = {
            cls._feature_names[i]: round(float(raw_importances[i]), 3)
            for i in range(len(cls._feature_names))
        }

        confidence = round(float(np.max(probabilities)), 2)

        return AreaOutbreakPrediction(
            area_name=area_name,
            disease_name=disease_name,
            district_name="Surveillance Jurisdiction",
            recent_cases=features.recent_case_count,
            historical_cases=features.historical_case_count,
            case_growth_rate=growth,
            risk_score=risk_score,
            risk_level=risk_level,
            predicted_trend=trend,
            confidence_score=confidence,
            feature_contributions=feature_contributions,
            prediction_date=datetime.date.today(),
        )
