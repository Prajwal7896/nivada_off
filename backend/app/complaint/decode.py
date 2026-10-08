from sqlalchemy import text
from sqlalchemy.orm import Session


def get_admin_location(
    db: Session,
    latitude: float,
    longitude: float
):
    print("VILLAGE LOOKUP LATITUDE:", latitude)
    print("VILLAGE LOOKUP LONGITUDE:", longitude)

    query = text("""
        SELECT
            v.id AS village_id,
            v.name AS village,
            t.id AS taluka_id,
            t.name AS taluka,
            d.id AS district_id,
            d.name AS district,
            s.id AS state_id,
            s.name AS state,
            c.id AS country_id,
            c.name AS country
        FROM villages v
        JOIN talukas t
            ON t.id = v.taluka_id
        JOIN districts d
            ON d.id = t.district_id
        JOIN states s
            ON s.id = d.state_id
        JOIN countries c
            ON c.id = s.country_id
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
    print("VILLAGE QUERY RESULT:", result)
    print("VILLAGE QUERY RESULT TYPE:", type(result))
    if not result:
        return None

    return dict(result)