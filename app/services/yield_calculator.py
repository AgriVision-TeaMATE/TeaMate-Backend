def calculate_predicted_yield(
    field_area_hectares: float,
    total_captured_area_sqm: float,
    total_pluckable_count: int,
    total_arimbu_count: int,
    avg_pluckable_ratio: float,
) -> float:
    """Computes predicted yield in kg from sampled image area and field scale."""
    if total_captured_area_sqm <= 0 or field_area_hectares <= 0:
        return 0.0

    bud_strength = (total_pluckable_count * 0.42) + (
        total_arimbu_count * 0.18
    )
    sampled_density = bud_strength / total_captured_area_sqm
    maturity_factor = 0.92 + (
        avg_ratio * 0.35 if (avg_ratio := avg_pluckable_ratio) else 0
    )
    field_area_sqm = field_area_hectares * 10000
    return round(sampled_density * field_area_sqm * maturity_factor, 2)
