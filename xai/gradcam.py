import numpy as np
import cv2
import tensorflow as tf
from pathlib import Path

# ------------------------------------------------------------------
# Speed note: rebuilding `tf.keras.Model(inputs=..., outputs=...)`
# on every single call re-traces the graph and adds real overhead,
# especially when you're now calling GradCAM once per image in a
# batch. Cache the wrapper model per underlying `model` instance so
# it's only built once.
# ------------------------------------------------------------------
_grad_model_cache = {}

def generate_gradcam(
    gradcam_model,
    image_array,
    env_data,
    class_index,
    output_path,
):
    image_tensor = tf.convert_to_tensor(image_array, dtype=tf.float32)
    env_tensor = tf.convert_to_tensor(env_data, dtype=tf.float32)

    with tf.GradientTape() as tape:
        conv_outputs, predictions = gradcam_model([image_tensor, env_tensor])
        loss = predictions[:, class_index]

    grads = tape.gradient(loss, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    conv_outputs = conv_outputs[0]
    heatmap = conv_outputs @ pooled_grads[..., None]
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0)
    heatmap /= (tf.reduce_max(heatmap) + 1e-8)
    heatmap = heatmap.numpy()

    heatmap = cv2.resize(heatmap, (224, 224))
    heatmap_uint = np.uint8(heatmap * 255)

    # applyColorMap returns BGR (OpenCV convention).
    heatmap_color = cv2.applyColorMap(heatmap_uint, cv2.COLORMAP_JET)

    original = image_array[0]
    original = (original - original.min()) / (
        original.max() - original.min() + 1e-8
    )
    original = np.uint8(original * 255)

    # `original` comes from PIL (RGB). Convert to BGR *before* blending
    # so it matches heatmap_color's channel order - the previous code
    # blended RGB with BGR directly, which swapped the red/blue channels
    # in the saved overlay.
    original_bgr = cv2.cvtColor(original, cv2.COLOR_RGB2BGR)

    overlay = cv2.addWeighted(original_bgr, 0.6, heatmap_color, 0.4, 0)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # overlay is already BGR, imwrite expects BGR - no extra conversion.
    cv2.imwrite(output_path, overlay)

    tf.keras.backend.clear_session()
    
    return {
        "path": output_path,
        "heatmap": heatmap.astype(np.float32),
    }