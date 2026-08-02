from .gradcam import generate_gradcam
from .shap_explainer import explain_environment


def generate_explanation(
    prediction_model,
    gradcam_model,
    image_batch,
    env_scaled,
    predicted_class,
    output_path,
):

    """
    Runs both XAI methods for ONE image and returns both results.

    NOTE on the original bug: `explain_environment(...)` was being called
    here without `class_index` (and elsewhere without `image_array`),
    which doesn't match its required signature and would raise a
    TypeError at runtime. Both are now passed through explicitly.
    """

    gradcam = generate_gradcam(
        gradcam_model=gradcam_model,
        image_array=image_batch,
        env_data=env_scaled,
        class_index=predicted_class,
        output_path=output_path,
    )

    shap_result = explain_environment(
        model=prediction_model,        
        image_array=image_batch,
        env_data=env_scaled,
        class_index=predicted_class,
    )

    # import matplotlib.pyplot as plt

    # features = [x["feature"] for x in shap_result]
    # impacts = [x["impact"] for x in shap_result]

    # plt.figure(figsize=(8,4))
    # plt.barh(features, impacts)
    # plt.xlabel("SHAP Impact")
    # plt.ylabel("Environmental Feature")
    # plt.title("Environmental Feature Contribution")

    # plt.tight_layout()
    # plt.savefig("shap_explanation.png", dpi=300)
    # plt.close()

    return {
        "gradcam_image": gradcam["path"],
        "gradcam_heatmap": gradcam["heatmap"],
        "environment_factors": shap_result,
    }