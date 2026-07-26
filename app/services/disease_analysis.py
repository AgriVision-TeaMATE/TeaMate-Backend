"""
Turns raw ML predictions + weather + disease reference data into everything
the frontend needs: confidence labels, resolved disease info, explanations.
None of this is ML — it's deterministic logic owned by the main backend.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..models.disease import Disease
from .disease_ml_client import RawPrediction
from .risk_engine import RiskAssessment


def confidence_level(probability: float) -> str:
    score = probability * 100
    if score > 85:
        return "Very High"
    if score > 70:
        return "High"
    if score > 50:
        return "Medium"
    return "Low"


@dataclass
class ScoredPrediction:
    disease: Disease
    probability: float
    confidence: str


def resolve_predictions(
    db: Session,
    raw_predictions: list[RawPrediction],
    top_n: int = 3,
) -> list[ScoredPrediction]:
    """Joins raw ML class/probability pairs against the diseases reference
    table and returns the top N, richest-first."""
    top_raw = raw_predictions[:top_n]
    class_keys = [p.class_key for p in top_raw]
    diseases = db.query(Disease).filter(Disease.class_key.in_(class_keys)).all()
    diseases_by_key = {d.class_key: d for d in diseases}

    scored: list[ScoredPrediction] = []
    for p in top_raw:
        disease = diseases_by_key.get(p.class_key)
        if disease is None:
            # ML returned a class with no matching reference row. Skip
            # rather than fabricate info — but this needs investigating:
            # either `diseases` is missing a seed entry, or the ML model's
            # class list has drifted from what's seeded here.
            continue
        scored.append(
            ScoredPrediction(
                disease=disease,
                probability=p.probability,
                confidence=confidence_level(p.probability),
            )
        )
    return scored


def build_ai_explanation(disease: Disease, risk: RiskAssessment) -> str:
    """Short natural-language explanation combining the detected disease's
    known profile with the actual weather conditions observed (Step 5)."""
    if disease.class_key == "healthy":
        return (
            "No disease symptoms were identified in the image, and recent "
            "weather conditions do not indicate elevated risk."
        )

    base = f"The prediction was influenced by visual symptoms consistent with {disease.name}."

    if risk.triggered_factors:
        weather_note = (
            " This is further supported by recent conditions: "
            + ", ".join(risk.triggered_factors)
            + "."
        )
    else:
        weather_note = (
            " Recent weather conditions were not strongly favorable for this "
            "disease, so continued monitoring is recommended to confirm the finding."
        )

    return base + weather_note