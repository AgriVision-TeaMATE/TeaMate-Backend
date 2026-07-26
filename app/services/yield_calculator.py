def calculate_predicted_yield(
    field_area_hectares: float,
    total_captured_area_sqm: float,
    total_pluckable_count: int,
    total_arimbu_count: int,
    pluckable_100_bud_weight_g: float,
    arimbu_100_bud_weight_g: float,
) -> float:
    """Computes predicted fresh-leaf yield in kg from sampled bud weights."""
    if total_captured_area_sqm <= 0 or field_area_hectares <= 0:
        return 0.0

    sample_weight_g = (
        total_pluckable_count * (pluckable_100_bud_weight_g / 100.0)
    ) + (
        total_arimbu_count * (arimbu_100_bud_weight_g / 100.0)
    )
    sampled_mass_density_g_per_sqm = sample_weight_g / total_captured_area_sqm
    field_area_sqm = field_area_hectares * 10000
    predicted_yield_kg = (sampled_mass_density_g_per_sqm * field_area_sqm) / 1000.0
    return round(predicted_yield_kg, 2)
