from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Boolean, Float, ForeignKey , DateTime
from sqlalchemy.sql import func
from app.db.db import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    email = Column(String, unique=True)
    password = Column(String)
    phone = Column(String)
    role = Column(String, default="citizen")
    created_at = Column(TIMESTAMP, server_default=func.now())

class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer)
    predicted_category = Column(String(100))
    confidence = Column(Float)
    model_version = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

    phone = Column(String)
    employee_code = Column(String, unique=True)
    designation = Column(String)

    department_id = Column(Integer, ForeignKey("departments.id"))

    country_id = Column(Integer, ForeignKey("countries.id"))
    state_id = Column(Integer, ForeignKey("states.id"))
    district_id = Column(Integer, ForeignKey("districts.id"))
    taluka_id = Column(Integer, ForeignKey("talukas.id"))
    village_id = Column(Integer, ForeignKey("villages.id"))

    role = Column(String, default="officer")
    created_at = Column(TIMESTAMP, server_default=func.now())


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Country(Base):
    __tablename__ = "countries"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)


class State(Base):
    __tablename__ = "states"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    country_id = Column(Integer, ForeignKey("countries.id"))


class District(Base):
    __tablename__ = "districts"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    state_id = Column(Integer, ForeignKey("states.id"))


class Taluka(Base):
    __tablename__ = "talukas"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    district_id = Column(Integer, ForeignKey("districts.id"))


class Village(Base):
    __tablename__ = "villages"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    taluka_id = Column(Integer, ForeignKey("talukas.id"))


class ComplaintCategory(Base):
    __tablename__ = "complaint_categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(Text)


class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("complaint_categories.id"))
    department_id = Column(Integer, ForeignKey("departments.id"))
    assigned_admin_id = Column(Integer, ForeignKey("admins.id"))
    complaint_text = Column(Text)
    address = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    country_id = Column(Integer, ForeignKey("countries.id"))
    state_id = Column(Integer, ForeignKey("states.id"))
    district_id = Column(Integer, ForeignKey("districts.id"))
    taluka_id = Column(Integer, ForeignKey("talukas.id"))
    village_id = Column(Integer, ForeignKey("villages.id"))
    image_path = Column(Text)
    status = Column(String, default="pending")
    priority = Column(String, default="medium")
    ai_confidence = Column(Float)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class ComplaintEvidence(Base):
    __tablename__ = "complaint_evidence"
    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"))
    file_path = Column(Text)
    file_type = Column(String)
    description = Column(Text)
    uploaded_at = Column(TIMESTAMP, server_default=func.now())


class ComplaintEmbedding(Base):
    __tablename__ = "complaint_embeddings"
    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"))
    embedding_id = Column(String)
    embedding_model = Column(String)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"))
    admin_id = Column(Integer, ForeignKey("admins.id"))
    assigned_by = Column(Integer, ForeignKey("admins.id"))
    assigned_at = Column(TIMESTAMP, server_default=func.now())
    status = Column(String, default="assigned")


class SLARule(Base):
    __tablename__ = "sla_rules"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("complaint_categories.id"))
    priority = Column(String)
    duration_hours = Column(Integer)
    active = Column(Boolean, default=True)


class ComplaintSLA(Base):
    __tablename__ = "complaint_sla"
    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"))
    sla_rule_id = Column(Integer, ForeignKey("sla_rules.id"))
    start_time = Column(TIMESTAMP, server_default=func.now())
    deadline = Column(TIMESTAMP)
    status = Column(String, default="active")


class Escalation(Base):
    __tablename__ = "escalations"
    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"))
    from_admin_id = Column(Integer, ForeignKey("admins.id"))
    to_admin_id = Column(Integer, ForeignKey("admins.id"))
    reason = Column(Text)
    level = Column(Integer)
    status = Column(String, default="pending")
    created_at = Column(TIMESTAMP, server_default=func.now())


class ComplaintHistory(Base):
    __tablename__ = "complaint_history"
    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"))
    performed_by = Column(Integer, ForeignKey("admins.id"))
    old_status = Column(String)
    new_status = Column(String)
    action = Column(String)
    description = Column(Text)
    timestamp = Column(TIMESTAMP, server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    complaint_id = Column(Integer, ForeignKey("complaints.id"))
    title = Column(String)
    message = Column(Text)
    notification_type = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class CitizenVerification(Base):
    __tablename__ = "citizen_verifications"
    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    verified = Column(Boolean)
    feedback = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    admin_id = Column(Integer)
    action = Column(String)
    entity_type = Column(String)
    entity_id = Column(Integer)
    description = Column(Text)
    timestamp = Column(TIMESTAMP, server_default=func.now())