import os
import subprocess

from huggingface_hub import snapshot_download

REPO_ID = "sage7896/Nivada"
LOCAL_DIR = os.path.abspath(".")

snapshot_download(
    repo_id=REPO_ID,
    local_dir=LOCAL_DIR,
    allow_patterns=["production_model/model/*"]
)

print("Production model downloaded")
print("Location:", os.path.abspath("production_model/model"))

env = os.environ.copy()
env["PYTHONPATH"] = os.path.abspath("backend")

subprocess.run([
    "uvicorn",
    "main:app",
    "--host",
    "0.0.0.0",
    "--port",
    os.environ.get("PORT", "8000")
], cwd="backend", env=env)