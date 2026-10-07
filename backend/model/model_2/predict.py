import os
import pickle
import torch

from transformers import AutoTokenizer, AutoModelForSequenceClassification

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = "sage7896/Nivada"

ENCODER_PATH = os.path.join(BASE_DIR, "label_encoder1.pkl")
COMPLAINTS_PATH = os.path.join(BASE_DIR, "complaints.txt")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_PATH
)

model.eval()

with open(ENCODER_PATH, "rb") as f:
    label_encoder = pickle.load(f)

def predict_categories(complaints):
    inputs = tokenizer(
        complaints,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )

    with torch.no_grad():
        outputs = model(**inputs)

    probabilities = torch.softmax(outputs.logits, dim=1)

    predicted_ids = torch.argmax(probabilities, dim=1)

    results = []

    for i, predicted_id in enumerate(predicted_ids):
        confidence = probabilities[i, predicted_id].item()

        category = label_encoder.inverse_transform(
            [predicted_id.item()]
        )[0]

        if confidence < 0.60:
            category = "Other"

        results.append({
            "complaint": complaints[i],
            "category": category,
            "confidence": confidence
        })

    return results

with open(COMPLAINTS_PATH, "r", encoding="utf-8") as f:
    complaints = [
        line.strip()
        for line in f
        if line.strip()
    ]

results = predict_categories(complaints)

print("\n" + "=" * 100)
print("NIVADA COMPLAINT CLASSIFICATION")
print("=" * 100)

for i, result in enumerate(results, 1):
    print(f"\n{i}. {result['complaint']}")
    print(f"   Category   : {result['category']}")
    print(f"   Confidence : {result['confidence']:.2%}")