import numpy as np
import shap

ENV_FEATURE_NAMES = [
    "total_rainfall_last_7",
    "avg_temperature_last_7",
    "avg_humidity_last_7",
    "avg_wind_speed_last_7",
    "avg_sunshine_hours_last_7",
]

# ------------------------------------------------------------------
# Speed notes
# ------------------------------------------------------------------
# KernelExplainer's cost is roughly O(background_rows * nsamples) model
# calls. The original code used 50 background rows and nsamples=100
# -> up to 5000 forward passes through the *whole* CNN+MLP model per
# request. That's the main reason it was slow.
#
# Fixes applied:
#   1. background is a single row of zeros. env_data is scaled/standardized
#      before it reaches this function, so an all-zero row already
#      represents the "average" weather condition - a single reference
#      row is standard practice for this kind of baseline and removes the
#      background-size factor from the cost entirely.
#   2. nsamples = 2**5 = 32, i.e. every possible feature coalition for
#      5 features. This turns Kernel SHAP into an *exact* Shapley value
#      computation (no Monte-Carlo noise) while still being far fewer
#      model calls than the original 100.
# ------------------------------------------------------------------

_BACKGROUND = np.zeros((1, len(ENV_FEATURE_NAMES)), dtype=np.float32)
_NSAMPLES = 2 ** len(ENV_FEATURE_NAMES)  # 32, exact for 5 features


def explain_environment(model, image_array, env_data, class_index):
    """
    SHAP explanation for environmental features, for one fixed leaf image.

    image_array:
        preprocessed image, shape (1, 224, 224, 3)
    env_data:
        scaled weather values, shape (1, 5)
    """

    image_array = np.asarray(image_array, dtype=np.float32)
    env_data = np.asarray(env_data, dtype=np.float32)

    def predict_environment(weather_batch):
        batch_size = weather_batch.shape[0]
        # Repeat the same leaf image so only weather varies.
        images = np.repeat(image_array, batch_size, axis=0)
        predictions = model.predict([images, weather_batch], verbose=0)
        return predictions[:, class_index]

    explainer = shap.KernelExplainer(predict_environment, _BACKGROUND)

    shap_values = explainer.shap_values(env_data, nsamples=_NSAMPLES)

    if isinstance(shap_values, list):
        shap_values = shap_values[0]

    shap_values = np.asarray(shap_values).reshape(-1)
    env_values = env_data.reshape(-1)

    result = []
    for name, value, impact in zip(ENV_FEATURE_NAMES, env_values, shap_values):
        result.append({
            "feature": name,
            "scaled_value": float(value),
            "impact": float(impact),
            "effect": "increase_risk" if impact > 0 else "decrease_risk",
        })

    result.sort(key=lambda x: abs(x["impact"]), reverse=True)
    return result