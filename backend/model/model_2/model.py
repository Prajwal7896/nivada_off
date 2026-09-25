import os
import random
import numpy as np
import torch

SEED = 42

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

MODEL_NAME = "distilbert-base-uncased"

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATA_PATH = os.path.join(
    BASE_DIR,
    "3_cleaned.csv"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "fast_model2"
)

ENCODER_PATH = os.path.join(
    BASE_DIR,
    "label_encoder1.pkl"
)