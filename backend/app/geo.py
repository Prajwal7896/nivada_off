from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.db import get_db
from app.db.model import (
    Country,
    State,
    District,
    Taluka,
    Village,
    Department
)

router = APIRouter(prefix="/api")


@router.get("/departments")
def get_departments(db: Session = Depends(get_db)):
    departments = db.query(Department).order_by(Department.name).all()

    return [
        {
            "id": department.id,
            "name": department.name
        }
        for department in departments
    ]


@router.get("/countries")
def get_countries(db: Session = Depends(get_db)):
    countries = db.query(Country).order_by(Country.name).all()

    return [
        {
            "id": country.id,
            "name": country.name
        }
        for country in countries
    ]


@router.get("/states/{country_id}")
def get_states(country_id: int, db: Session = Depends(get_db)):
    states = (
        db.query(State)
        .filter(State.country_id == country_id)
        .order_by(State.name)
        .all()
    )

    return [
        {
            "id": state.id,
            "name": state.name
        }
        for state in states
    ]


@router.get("/districts/{state_id}")
def get_districts(state_id: int, db: Session = Depends(get_db)):
    districts = (
        db.query(District)
        .filter(District.state_id == state_id)
        .order_by(District.name)
        .all()
    )

    return [
        {
            "id": district.id,
            "name": district.name
        }
        for district in districts
    ]


@router.get("/talukas/{district_id}")
def get_talukas(district_id: int, db: Session = Depends(get_db)):
    talukas = (
        db.query(Taluka)
        .filter(Taluka.district_id == district_id)
        .order_by(Taluka.name)
        .all()
    )

    return [
        {
            "id": taluka.id,
            "name": taluka.name
        }
        for taluka in talukas
    ]


@router.get("/villages/{taluka_id}")
def get_villages(taluka_id: int, db: Session = Depends(get_db)):
    villages = (
        db.query(Village)
        .filter(Village.taluka_id == taluka_id)
        .order_by(Village.name)
        .all()
    )

    return [
        {
            "id": village.id,
            "name": village.name
        }
        for village in villages
    ]