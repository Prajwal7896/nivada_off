import os
import shutil
import mlflow
from mlflow import MlflowClient

mlflow.set_tracking_uri("http://127.0.0.1:5000")

MODEL_NAME = "Nivada-Complaint-Classifier"
MODEL_VERSION = "2"

SOURCE = f"models:/{MODEL_NAME}/{MODEL_VERSION}"
LOCAL_DIR = os.path.abspath("production_model")

client = MlflowClient()

if os.path.exists(LOCAL_DIR):
    shutil.rmtree(LOCAL_DIR)

model_version = client.get_model_version(
    MODEL_NAME,
    MODEL_VERSION
)

mlflow.artifacts.download_artifacts(
    artifact_uri=f"runs:/{model_version.run_id}/model",
    dst_path=LOCAL_DIR
)

print("Production model downloaded")
print("Location:", LOCAL_DIR)