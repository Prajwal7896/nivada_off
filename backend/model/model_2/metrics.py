import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
)

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        predictions,
        average="weighted",
    )
    accuracy = accuracy_score(
        labels,
        predictions,
    )
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }