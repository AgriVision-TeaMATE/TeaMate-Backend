from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch
import io


class CLIPLeafValidator:

    def __init__(self):
        self.model = CLIPModel.from_pretrained(
            "openai/clip-vit-base-patch32"
        )

        self.processor = CLIPProcessor.from_pretrained(
            "openai/clip-vit-base-patch32"
        )

        self.labels = [
            "a tea leaf",
            "a plant leaf",
            "a tree leaf",
            "a television",
            "a building",
            "a person",
            "a car",
            "an indoor object"
        ]


    def validate(self, image_bytes: bytes):

        image = Image.open(
            io.BytesIO(image_bytes)
        ).convert("RGB")


        inputs = self.processor(
            text=self.labels,
            images=image,
            return_tensors="pt",
            padding=True
        )


        with torch.no_grad():

            outputs = self.model(**inputs)


        probabilities = (
            outputs
            .logits_per_image
            .softmax(dim=1)[0]
        )


        scores = {
            label: float(prob)
            for label, prob in zip(
                self.labels,
                probabilities
            )
        }


        leaf_score = max(
            scores["a tea leaf"],
            scores["a plant leaf"],
            scores["a tree leaf"]
        )


        return {
            "is_leaf": leaf_score > 0.35,
            "leaf_confidence": leaf_score,
            "scores": scores
        }


clip_validator = CLIPLeafValidator()