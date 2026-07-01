def calculate_predicted_yield(
    field_area_hectares: float,
    total_pluckable_count: int,
    total_arimbu_count: int,
    avg_pluckable_ratio: float,
) -> float:
    """Computes predicted yield in kg based on analyzed bud metrics and field area."""
    bud_strength = (total_pluckable_count * 0.42) + (
        total_arimbu_count * 0.18
    )
    maturity_factor = 0.92 + (avg_ratio * 0.35 if (avg_ratio := avg_pluckable_ratio) else 0)
    return round(bud_strength * field_area_hectares * maturity_factor, 2)
