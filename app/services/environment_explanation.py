from collections import defaultdict


FEATURE_MESSAGES = {
    "avg_wind_speed_last_7": {
        "title": "Wind Conditions",
        "increase":
            "Lower wind movement may reduce air circulation and create favourable conditions for disease development.",
        "decrease":
            "Higher wind movement may help reduce moisture accumulation on leaves.",
    },

    "avg_temperature_last_7": {
        "title": "Temperature",
        "increase":
            "Temperature conditions may support pathogen activity and disease development.",
        "decrease":
            "Temperature conditions appear less favourable for disease development.",
    },

    "avg_humidity_last_7": {
        "title": "Humidity",
        "increase":
            "Higher humidity can increase leaf moisture and favour disease spread.",
        "decrease":
            "Lower humidity may reduce conditions suitable for disease development.",
    },

    "total_rainfall_last_7": {
        "title": "Rainfall",
        "increase":
            "Recent rainfall may have increased moisture availability for disease development.",
        "decrease":
            "Lower rainfall reduces moisture-related disease risk.",
    },

    "avg_sunshine_hours_last_7": {
        "title": "Sunlight",
        "increase":
            "Higher sunlight may reduce disease-supporting moisture conditions.",
        "decrease":
            "Reduced sunlight may allow moisture to remain longer on leaves.",
    },
}


def interpret_environment_factors(
    factors: list[dict],
) -> dict:

    if not factors:
        return {
            "environmental_summary": None,
            "environmental_insights": [],
            "environmental_technical_summary": None,
        }


    grouped = defaultdict(list)

    for factor in factors:
        grouped[factor["feature"]].append(factor)


    averaged_factors = []

    for feature, values in grouped.items():

        total_impact = sum(
            abs(v["impact"])
            for v in values
        )

        strongest = max(
            values,
            key=lambda x: abs(x["impact"])
        )

        averaged_factors.append(
            {
                "feature": feature,
                "impact": round(total_impact, 5),
                "effect": strongest["effect"],
            }
        )


    averaged_factors.sort(
        key=lambda x: x["impact"],
        reverse=True
    )


    insights = []

    for factor in averaged_factors:

        feature = factor["feature"]

        if feature not in FEATURE_MESSAGES:
            continue

        data = FEATURE_MESSAGES[feature]

        increase = factor["effect"] == "increase_risk"

        severity = "low"

        if factor["impact"] >= 0.1:
            severity = "high"
        elif factor["impact"] >= 0.01:
            severity = "medium"


        insights.append(
            {
                "title": data["title"],
                "message": data[
                    "increase" if increase else "decrease"
                ],
                "severity": severity,
                "impact": factor["impact"],
            }
        )


    # sort by importance
    insights.sort(
        key=lambda x: x["impact"],
        reverse=True
    )


    # return only top explanations
    insights = [
        {
            "title": i["title"],
            "message": i["message"],
            "severity": i["severity"],
        }
        for i in insights[:3]
    ]

    risk_increasing = len(
        [
            f for f in averaged_factors
            if f["effect"] == "increase_risk"
        ]
    )

    risk_reducing = len(
        [
            f for f in averaged_factors
            if f["effect"] == "decrease_risk"
        ]
    )


    summary = (
        "Recent environmental conditions may have increased "
        "disease risk based on weather patterns."
        if risk_increasing > risk_reducing
        else
        "Recent environmental conditions appear less favourable "
        "for disease development."
    )


    return {
        "environmental_summary": summary,

        "environmental_insights": insights,

        "environmental_technical_summary": {
            "top_risk_factors": averaged_factors[:5],
            "risk_increasing_factors": risk_increasing,
            "risk_reducing_factors": risk_reducing,
        },
    }