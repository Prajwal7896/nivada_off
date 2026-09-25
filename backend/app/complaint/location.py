from sqlalchemy import text
from sqlalchemy.orm import Session


def decode_location(
    db: Session,
    latitude: float,
    longitude: float
):
    query = text("""
        SELECT
            c.name AS country,
            s.name AS state,
            d.name AS district,
            t.name AS taluka,
            v.name AS village
        FROM villages v
        JOIN talukas t ON t.id = v.taluka_id
        JOIN districts d ON d.id = t.district_id
        JOIN states s ON s.id = d.state_id
        JOIN countries c ON c.id = s.country_id
        WHERE ST_Covers(
            v.geometry,
            ST_SetSRID(
                ST_Point(:longitude, :latitude),
                4326
            )
        )
        LIMIT 1
    """)

    result = db.execute(
        query,
        {
            "latitude": latitude,
            "longitude": longitude
        }
    ).mappings().first()

    if not result:
        return None

    return dict(result)