from fastapi import APIRouter, Form, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.db import get_db
from app.db.model import (
    Admin,
    Department,
    Country,
    State,
    District,
    Taluka,
    Village
)

router = APIRouter()


@router.post("/officer/register")
def officer_register(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    employee_code: str = Form(...),
    designation: str = Form(...),
    department_id: str = Form(...),
    country_id: str = Form(...),
    state_id: str = Form(...),
    district_id: str = Form(...),
    taluka_id: str = Form(...),
    village_id: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    if password != confirm_password:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "password",
                "message": "Passwords do not match."
            }
        )

    if db.query(Admin).filter(Admin.email == email).first():
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "email",
                "message": "Email already registered."
            }
        )

    if db.query(Admin).filter(Admin.employee_code == employee_code).first():
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "employee_code",
                "message": "Employee code already registered."
            }
        )

    try:
        department_id = int(department_id)
        country_id = int(country_id)
        state_id = int(state_id)
        district_id = int(district_id)
        taluka_id = int(taluka_id)
        village_id = int(village_id)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "invalid_id",
                "message": "Invalid geographic or department ID."
            }
        )

    if not db.query(Department).filter(Department.id == department_id).first():
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "department",
                "message": "Selected department does not exist."
            }
        )

    if not db.query(Country).filter(Country.id == country_id).first():
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "country",
                "message": "Selected country does not exist."
            }
        )

    if not db.query(State).filter(State.id == state_id, State.country_id == country_id).first():
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "state",
                "message": "Selected state does not belong to the selected country."
            }
        )

    if not db.query(District).filter(District.id == district_id, District.state_id == state_id).first():
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "district",
                "message": "Selected district does not belong to the selected state."
            }
        )

    if not db.query(Taluka).filter(Taluka.id == taluka_id, Taluka.district_id == district_id).first():
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "taluka",
                "message": "Selected taluka does not belong to the selected district."
            }
        )

    if not db.query(Village).filter(Village.id == village_id, Village.taluka_id == taluka_id).first():
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "village",
                "message": "Selected village does not belong to the selected taluka."
            }
        )

    admin = Admin(
        username=name,
        email=email,
        password=password,
        phone=phone,
        employee_code=employee_code,
        designation=designation,
        department_id=department_id,
        country_id=country_id,
        state_id=state_id,
        district_id=district_id,
        taluka_id=taluka_id,
        village_id=village_id,
        role="officer"
    )

    try:
        db.add(admin)
        db.commit()
        db.refresh(admin)
    except IntegrityError as e:
        db.rollback()
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "database",
                "message": str(e.orig)
            }
        )

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": "Officer registered successfully.",
            "admin_id": admin.id,
            "employee_code": admin.employee_code
        }
    )