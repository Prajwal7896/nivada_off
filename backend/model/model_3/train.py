import os
import pickle
import mlflow
import pandas as pd
import torch

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
    DataCollatorWithPadding,
)

from model import (
    SEED,
    MODEL_NAME,
    DATA_PATH,
    OUTPUT_DIR,
    ENCODER_PATH,
)

from dataset import ComplaintDataset
from metrics import compute_metrics


df = pd.read_csv(DATA_PATH)

df.columns = df.columns.str.strip()

required_columns = ["complaint", "category"]

missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing columns: {missing_columns}. "
        f"Available columns: {df.columns.tolist()}"
    )

df = df.dropna(
    subset=["complaint", "category"]
)

df = df[
    (df["complaint"].astype(str).str.strip() != "") &
    (df["category"].astype(str).str.strip() != "")
]

df = df.sample(frac=1, random_state=SEED)

texts = df["complaint"].astype(str).tolist()
labels = df["category"].astype(str).tolist()

label_encoder = LabelEncoder()

labels = label_encoder.fit_transform(labels)

num_labels = len(
    label_encoder.classes_
)

print("Dataset size:", len(df))
print("Number of classes:", num_labels)
print("Classes:", label_encoder.classes_)

train_texts, val_texts, train_labels, val_labels = train_test_split(
    texts,
    labels,
    test_size=0.20,
    random_state=SEED,
    stratify=labels
)

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)

train_encodings = tokenizer(
    train_texts,
    truncation=True,
    max_length=128
)

val_encodings = tokenizer(
    val_texts,
    truncation=True,
    max_length=128
)

train_dataset = ComplaintDataset(
    train_encodings,
    train_labels
)

val_dataset = ComplaintDataset(
    val_encodings,
    val_labels
)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=num_labels
)

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    learning_rate=2e-5,
    weight_decay=0.01,
    eval_strategy="epoch",
    save_strategy="no",
    logging_steps=50,
    fp16=torch.cuda.is_available(),
    dataloader_num_workers=0,
    report_to="none",
    seed=SEED
)

data_collator = DataCollatorWithPadding(
    tokenizer=tokenizer
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    data_collator=data_collator,
    compute_metrics=compute_metrics
)

with mlflow.start_run():

    trainer.train()

    results = trainer.evaluate()

    print("\nEvaluation Results:")
    print(results)

    mlflow.log_metrics({
        "accuracy": results["eval_accuracy"],
        "precision": results["eval_precision"],
        "recall": results["eval_recall"],
        "f1": results["eval_f1"]
    })

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

trainer.save_model(
    OUTPUT_DIR
)

tokenizer.save_pretrained(
    OUTPUT_DIR
)

os.makedirs(
    os.path.dirname(ENCODER_PATH),
    exist_ok=True
)

with open(
    ENCODER_PATH,
    "wb"
) as f:

    pickle.dump(
        label_encoder,
        f
    )

print("\nModel Training Completed Successfully!")
print("Model saved to:", OUTPUT_DIR)
print("Label Encoder:", ENCODER_PATH)