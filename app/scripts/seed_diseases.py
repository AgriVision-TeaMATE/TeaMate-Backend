"""
One-off seed script for the `diseases` reference table.

Run with: python -m app.scripts.seed_diseases
"""

from datetime import datetime, timezone, timedelta

from ..database import SessionLocal
from ..models.disease import Disease


SL_TIMEZONE = timezone(timedelta(hours=5, minutes=30))
SEED_TIME = datetime(2026, 7, 28, 10, 16, 6, 635082, tzinfo=SL_TIMEZONE)


DISEASES = [
    {
        "id": "20bf5399-2d22-4b1d-a262-8da4fa21154d",
        "class_key": "Blister_blight",
        "name": "Blister Blight",
        "description": (
            "Fungal disease (Exobasidium vexans) producing blister-like lesions "
            "on young leaves that turn white and later brown."
        ),
        "causes": [
            "Fungal infection favored by high humidity and prolonged leaf wetness",
            "Cool, wet weather with frequent rainfall",
            "Poor air circulation within the canopy",
        ],
        "recommendations": [
            "Remove and destroy infected leaves immediately",
            "Apply copper-based fungicides during outbreak periods",
            "Improve air circulation by proper pruning",
            "Avoid overhead irrigation",
        ],
        "severity_default": "high",
        "disease_type": "Fungal Disease",
    },

    {
        "id": "2fbc7d23-f2ac-4b40-ad15-347af4cc2549",
        "class_key": "Healthy",
        "name": "Healthy",
        "description": (
            "No disease detected. The tea leaf appears healthy with no significant "
            "pathological symptoms."
        ),
        "causes": [],
        "recommendations": [
            "Continue regular monitoring",
            "Maintain proper agricultural practices",
            "Ensure adequate nutrition and irrigation",
            "Keep field records updated",
        ],
        "severity_default": "none",
        "disease_type": "Healthy",
    },

    {
        "id": "57f932a5-ca4f-4c03-a20f-a7f23b1a66ce",
        "class_key": "pest_damage",
        "name": "Pest Damage",
        "description": (
            "General pest-related damage to tea leaves, including chewing and "
            "sucking injuries from various insects."
        ),
        "causes": [
            "Infestation by various leaf-feeding insects",
            "Lack of natural enemies in the ecosystem",
            "Hot and dry weather favoring pest development",
        ],
        "recommendations": [
            "Monitor fields regularly for early detection",
            "Use integrated pest management practices",
            "Conserve beneficial insects where possible",
            "Apply appropriate treatments based on pest identification",
        ],
        "severity_default": "medium",
        "disease_type": "Unknown",
    },

    {
        "id": "5d3a82dd-9001-44e5-997e-a5f30f913bd8",
        "class_key": "Anthracnose",
        "name": "Anthracnose",
        "description": (
            "Fungal disease (Colletotrichum species) causing dark, sunken "
            "lesions on leaves and fruits, leading to defoliation and yield loss."
        ),
        "causes": [
            "Fungal spores spread by splashing water",
            "Warm, humid weather with frequent rainfall",
            "Presence of infected plant debris",
            "Poor drainage and air circulation",
        ],
        "recommendations": [
            "Remove and destroy infected plant debris",
            "Apply copper-based fungicides during favorable conditions",
            "Prune for better air circulation",
            "Avoid overhead irrigation",
        ],
        "severity_default": "high",
        "disease_type": "Fungal Disease",
    },

    {
        "id": "646614fb-184a-4d5a-bdc2-6f82c187d47b",
        "class_key": "Algae_or_Moss",
        "name": "Algae or Moss",
        "description": (
            "Fungal infection (Colletotrichum camelliae) causing reddish-brown "
            "spots on mature leaves, affecting yield and quality."
        ),
        "causes": [
            "Fungal spores spreading in warm, humid conditions",
            "Fallen infected leaf litter left in the field",
            "Excessive nitrogen fertilization promoting susceptible growth",
        ],
        "recommendations": [
            "Remove and destroy fallen infected leaves",
            "Apply appropriate fungicides during favorable conditions",
            "Prune for better air circulation",
            "Avoid excessive nitrogen fertilization",
        ],
        "severity_default": "low",
        "disease_type": "Environmental Stress",
    },

    {
        "id": "94128da1-5fe6-4a7f-b983-3d59ab09c4e0",
        "class_key": "Spider_mite_disease",
        "name": "Spider mite disease",
        "description": (
            "Damage caused by mite infestation resulting in leaf bronzing, "
            "stippling, and webbing, affecting plant vigor and yield."
        ),
        "causes": [
            "Heavy mite population buildup",
            "Hot, dry weather conditions",
            "Lack of natural predators due to pesticide use",
            "Stressed plants due to poor nutrition",
        ],
        "recommendations": [
            "Introduce or conserve natural predators (ladybugs, lacewings)",
            "Spray neem oil or horticultural oil for control",
            "Maintain proper plant nutrition to reduce stress",
            "Use insecticidal soap for heavy infestations",
        ],
        "severity_default": "medium",
        "disease_type": "Nutritional Stress",
    },

    {
        "id": "b99e28fa-ed98-4d24-99ff-7cdbd67cd802",
        "class_key": "tea_mosquito_bug",
        "name": "Tea Mosquito Bug",
        "description": (
            "Insect pest (Helopeltis theivora) causing leaf damage and sooty "
            "mould growth on tender shoots."
        ),
        "causes": [
            "Nymph and adult feeding on tender leaves and buds",
            "High humidity and shaded, poorly ventilated canopy",
            "Presence of alternate host weeds near the field",
        ],
        "recommendations": [
            "Use yellow sticky traps for monitoring and control",
            "Prune and destroy infested shoots and leaves",
            "Apply neem oil or other botanical insecticides during early infestation",
            "Maintain field hygiene by removing weeds and alternate hosts",
        ],
        "severity_default": "medium",
        "disease_type": "Unknown",
    },
]


def seed_diseases():
    db = SessionLocal()

    try:
        for entry in DISEASES:

            existing = (
                db.query(Disease)
                .filter(Disease.class_key == entry["class_key"])
                .first()
            )

            if existing:
                # Update everything except id/class_key/name
                existing.description = entry["description"]
                existing.causes = entry["causes"]
                existing.recommendations = entry["recommendations"]
                existing.severity_default = entry["severity_default"]
                existing.disease_type = entry["disease_type"]

            else:
                db.add(
                    Disease(
                        id=entry["id"],
                        class_key=entry["class_key"],
                        name=entry["name"],
                        description=entry["description"],
                        causes=entry["causes"],
                        recommendations=entry["recommendations"],
                        severity_default=entry["severity_default"],
                        disease_type=entry["disease_type"],
                        created_at=SEED_TIME,
                        updated_at=SEED_TIME,
                    )
                )

        db.commit()
        print(f"Seeded {len(DISEASES)} diseases successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_diseases()