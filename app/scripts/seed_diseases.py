"""
One-off seed script for the `diseases` reference table.

Run with: python -m app.scripts.seed_diseases
"""
from ..database import SessionLocal
from ..models.disease import Disease

DISEASES = [
    {
        "class_key": "anthracnose",
        "name": "Anthracnose",
        "description": "Fungal disease (Colletotrichum species) causing dark, sunken lesions on leaves and fruits, leading to defoliation and yield loss.",
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
    },
    {
        "class_key": "mite_disease",
        "name": "Mite Disease",
        "description": "Damage caused by mite infestation resulting in leaf bronzing, stippling, and webbing, affecting plant vigor and yield.",
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
    },
    {
        "class_key": "tea_mosquito_bug",
        "name": "Tea Mosquito Bug",
        "description": "Insect pest (Helopeltis theivora) causing leaf damage and sooty mould growth on tender shoots.",
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
    },
    {
        "class_key": "blister_blight",
        "name": "Blister Blight",
        "description": "Fungal disease (Exobasidium vexans) producing blister-like lesions on young leaves that turn white and later brown.",
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
    },
    {
        "class_key": "red_leaf_spot",
        "name": "Red Leaf Spot",
        "description": "Fungal infection (Colletotrichum camelliae) causing reddish-brown spots on mature leaves, affecting yield and quality.",
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
    },
    {
        "class_key": "healthy",
        "name": "Healthy",
        "description": "No disease detected. The tea leaf appears healthy with no significant pathological symptoms.",
        "causes": [],
        "recommendations": [
            "Continue regular monitoring",
            "Maintain proper agricultural practices",
            "Ensure adequate nutrition and irrigation",
            "Keep field records updated",
        ],
        "severity_default": "none",
    },
    {
        "class_key": "pest_damage",
        "name": "Pest Damage",
        "description": "General pest-related damage to tea leaves, including chewing and sucking injuries from various insects.",
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
    },
]


def seed_diseases() -> None:
    db = SessionLocal()
    try:
        for entry in DISEASES:
            existing = db.query(Disease).filter_by(class_key=entry["class_key"]).first()
            if existing:
                for key, value in entry.items():
                    setattr(existing, key, value)
            else:
                db.add(Disease(**entry))
        db.commit()
        print(f"Seeded {len(DISEASES)} diseases.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_diseases()