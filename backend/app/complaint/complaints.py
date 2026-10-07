import os
import pickle
import numpy as np
import onnxruntime as ort

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session
from transformers import AutoTokenizer
from prometheus_client import Counter, Histogram , Gauge
import time
from app.complaint.decode import get_admin_location
from app.db.db import get_db
from app.db.model import User, Complaint, ComplaintCategory, Department, Admin , PredictionLog

router = APIRouter(prefix="/api", tags=["Complaints"])

prediction_counter = Counter(
    "nivada_predictions_total",
    "Total number of ML predictions"
)

prediction_category_counter = Counter(
    "nivada_predictions_by_category_total",
    "Predictions by category",
    ["category"]
)

prediction_error_counter = Counter(
    "nivada_prediction_errors_total",
    "Total number of ML prediction errors"
)

prediction_confidence = Histogram(
    "nivada_prediction_confidence",
    "ML prediction confidence"
)

prediction_latency = Histogram(
    "nivada_prediction_latency_seconds",
    "ML prediction latency"
)

low_confidence_counter = Counter(
    "nivada_low_confidence_predictions_total",
    "Predictions with confidence below threshold"
)

model_info = Gauge(
    "nivada_model_info",
    "Currently deployed Nivada ML model",
    ["model_version"]
)

model_info.labels(model_version="2").set(1)

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../model/model_2")
)

MODEL_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../production_model/model/model.onnx"
    )
)

TOKENIZER_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../production_model/model"
    )
)

ENCODER_PATH = os.path.join(
    BASE_DIR,
    "label_encoder1.pkl"
)

tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_PATH)

onnx_session = ort.InferenceSession(
    MODEL_PATH,
    providers=["CPUExecutionProvider"]
)

with open(ENCODER_PATH, "rb") as f:
    label_encoder = pickle.load(f)


def predict_category(text: str):
    start_time = time.time()

    try:
        inputs = tokenizer(
            text,
            return_tensors="np",
            truncation=True,
            max_length=128
        )

        ort_inputs = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64)
        }

        logits = onnx_session.run(
            ["logits"],
            ort_inputs
        )[0]

        probabilities = np.exp(
            logits - np.max(logits, axis=1, keepdims=True)
        )

        probabilities = probabilities / np.sum(
            probabilities,
            axis=1,
            keepdims=True
        )

        predicted_id = int(
            np.argmax(probabilities, axis=1)[0]
        )

        confidence = float(
            probabilities[0, predicted_id]
        )

        category_name = label_encoder.inverse_transform(
            [predicted_id]
        )[0]

        if confidence < 0.60:
            low_confidence_counter.inc()
            category_name = "Other"

        prediction_category_counter.labels(
            category=category_name
        ).inc()
        
        prediction_counter.inc()
        print("PREDICTION FUNCTION CALLED")
        print("COUNTER BEFORE:", prediction_counter._value.get())
        prediction_confidence.observe(confidence)
        prediction_latency.observe(time.time() - start_time)

        return category_name, confidence
    
    except Exception:
        prediction_error_counter.inc()
        raise


def get_department_name(category_name: str):
    mapping = {
        "Animal and Stray Issues": "Animal Control",
        "Construction": "Building and Construction",
        "Documents": "Municipal Administration",
        "Drainage and Sewage": "Drainage and Sewerage",
        "Education": "Education",
        "Electricity": "Electricity",
        "Environment": "Environment",
        "Fire Emergency": "Fire and Emergency Services",
        "Healthcare": "Public Health",
        "Housing Properties": "Urban Planning",
        "Internet": "Municipal Administration",
        "Parking and Traffic": "Traffic Management",
        "Police": "Police",
        "Road": "Roads and Infrastructure",
        "Waste": "Waste Management",
        "Water": "Water Supply"
    }

    return mapping.get(category_name)


def find_assigned_admin(
    db: Session,
    department_id: int,
    village_id: int | None,
    taluka_id: int | None,
    district_id: int | None
):
    if village_id is not None:
        admin = db.query(Admin).filter(
            Admin.role == "officer",
            Admin.department_id == department_id,
            Admin.village_id == village_id
        ).first()

        if admin:
            return admin

    if taluka_id is not None:
        admin = db.query(Admin).filter(
            Admin.role == "officer",
            Admin.department_id == department_id,
            Admin.taluka_id == taluka_id
        ).first()

        if admin:
            return admin

    if district_id is not None:
        admin = db.query(Admin).filter(
            Admin.role == "officer",
            Admin.department_id == department_id,
            Admin.district_id == district_id
        ).first()

        if admin:
            return admin

    return db.query(Admin).filter(
        Admin.role == "officer",
        Admin.department_id == department_id
    ).first()


@router.post("/complaints")
async def create_complaint(
    request: Request,
    description: str = Form(...),
    address: str = Form(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    country_id: int | None = Form(None),
    state_id: int | None = Form(None),
    district_id: int | None = Form(None),
    taluka_id: int | None = Form(None),
    village_id: int | None = Form(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    print("CREATE_COMPLAINT CALLED")
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User is not logged in"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    description = description.strip()
    address = address.strip()

    if len(description) < 10:
        raise HTTPException(
            status_code=400,
            detail="Complaint description must contain at least 10 characters"
        )

    if len(description) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Complaint description cannot exceed 2000 characters"
        )

    if not address:
        raise HTTPException(
            status_code=400,
            detail="Address is required"
        )

    if latitude is not None and longitude is not None:
        location = get_admin_location(
            db,
            latitude,
            longitude
        )

        if not location:
            raise HTTPException(
                status_code=400,
                detail="Unable to determine village from the given coordinates"
            )

        country_id = location["country_id"]
        state_id = location["state_id"]
        district_id = location["district_id"]
        taluka_id = location["taluka_id"]
        village_id = location["village_id"]

    category_name, confidence = predict_category(
        description
    )

    category = db.query(ComplaintCategory).filter(
        func.lower(ComplaintCategory.name)
        == category_name.lower()
    ).first()

    if not category:
        if category_name == "Other":
            category = db.query(ComplaintCategory).filter(
                func.lower(ComplaintCategory.name) == "other"
            ).first()

        if not category:
            raise HTTPException(
                status_code=500,
                detail=f"Category '{category_name}' does not exist in database"
            )

    department_name = get_department_name(
        category.name
    )

    if not department_name:
        raise HTTPException(
            status_code=500,
            detail=f"No department mapping found for category '{category.name}'"
        )

    department = db.query(Department).filter(
        func.lower(Department.name)
        == department_name.lower()
    ).first()

    if not department:
        raise HTTPException(
            status_code=500,
            detail=f"Department '{department_name}' does not exist in database"
        )

    assigned_admin = find_assigned_admin(
        db=db,
        department_id=department.id,
        village_id=village_id,
        taluka_id=taluka_id,
        district_id=district_id
    )

    print(
        "ASSIGNMENT:",
        "department=", department.id,
        "village=", village_id,
        "taluka=", taluka_id,
        "district=", district_id,
        "admin=", assigned_admin.id if assigned_admin else None
    )

    image_path = None

    if image:
        allowed_types = {
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/webp"
        }

        if image.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Only JPG, JPEG, PNG and WEBP images are allowed"
            )

        image_data = await image.read()

        if len(image_data) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Image size cannot exceed 5 MB"
            )

        upload_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../uploads/complaints"
            )
        )

        os.makedirs(
            upload_dir,
            exist_ok=True
        )

        extension = os.path.splitext(
            image.filename
        )[1].lower()

        filename = (
            f"user_{user_id}_"
            f"{os.urandom(8).hex()}"
            f"{extension}"
        )

        image_path = os.path.join(
            upload_dir,
            filename
        )

        with open(image_path, "wb") as f:
            f.write(image_data)

    complaint = Complaint(
        user_id=user_id,
        category_id=category.id,
        department_id=department.id,
        assigned_admin_id=(
            assigned_admin.id
            if assigned_admin
            else None
        ),
        complaint_text=description,
        address=address,
        latitude=latitude,
        longitude=longitude,
        country_id=country_id,
        state_id=state_id,
        district_id=district_id,
        taluka_id=taluka_id,
        village_id=village_id,
        image_path=image_path,
        status="pending",
        priority="medium",
        ai_confidence=confidence
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    prediction_log = PredictionLog(
        complaint_id=complaint.id,
        predicted_category=category.name,
        confidence=confidence,
        model_version="2"
    )

    db.add(prediction_log)
    db.commit()

    return {
        "success": True,
        "complaint_id": complaint.id,
        "complaint_number": f"NVD-{complaint.id:06d}",
        "category": category.name,
        "category_id": category.id,
        "department": department.name,
        "department_id": department.id,
        "assigned_admin_id": (
            assigned_admin.id
            if assigned_admin
            else None
        ),
        "country_id": country_id,
        "state_id": state_id,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "village_id": village_id,
        "confidence": round(confidence, 4),
        "status": complaint.status
    }

@router.get("/prediction-logs")
def get_prediction_logs(
    db: Session = Depends(get_db)
):
    logs = (
        db.query(PredictionLog)
        .order_by(PredictionLog.created_at.desc())
        .limit(100)
        .all()
    )

    return [
        {
            "id": log.id,
            "complaint_id": log.complaint_id,
            "predicted_category": log.predicted_category,
            "confidence": log.confidence,
            "model_version": log.model_version,
            "created_at": log.created_at
        }
        for log in logs
    ]