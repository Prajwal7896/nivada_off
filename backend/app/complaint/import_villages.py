import os
import pandas as pd
import geopandas as gpd
from sqlalchemy import text
from backend.app.db.db import SessionLocal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GEOJSON_FILE = os.path.join(
    BASE_DIR,
    "dataset",
    "vb_soi_mh.GeoJSON"
)


def normalize_name(name):
    if name is None:
        return ""

    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .replace(".", "")
        .replace("'", "")
    )


def load_geojson():
    if not os.path.exists(GEOJSON_FILE):
        raise FileNotFoundError(
            f"GeoJSON not found: {GEOJSON_FILE}"
        )

    print(f"Loading: {GEOJSON_FILE}")

    gdf = gpd.read_file(GEOJSON_FILE)

    print(f"Records: {len(gdf)}")
    print(f"Columns: {list(gdf.columns)}")

    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    else:
        gdf = gdf.to_crs(4326)

    return gdf


def get_database_villages(db):
    query = text("""
        SELECT
            v.id,
            v.name,
            t.name AS taluka,
            d.name AS district,
            s.name AS state
        FROM villages v
        JOIN talukas t
            ON v.taluka_id = t.id
        JOIN districts d
            ON t.district_id = d.id
        JOIN states s
            ON d.state_id = s.id
        WHERE LOWER(TRIM(t.name)) = 'palus'
          AND LOWER(TRIM(d.name)) = 'sangli'
          AND LOWER(TRIM(s.name)) = 'maharashtra'
        ORDER BY v.name
    """)

    return db.execute(query).fetchall()


def update_villages(gdf):
    db = SessionLocal()

    try:
        villages = get_database_villages(db)

        print()
        print(f"Database villages found: {len(villages)}")
        print()

        gdf["normalized_village"] = (
            gdf["village"].apply(normalize_name)
        )

        updated = 0
        not_found = 0

        for village_id, db_name, taluka, district, state in villages:

            normalized_db_name = normalize_name(db_name)

            matches = gdf[
                gdf["normalized_village"] == normalized_db_name
            ]

            if matches.empty:
                print(f"NAME NOT FOUND: {db_name}")
                not_found += 1
                continue

            match = matches.iloc[0]

            geo_name = str(match["village"]).strip()
            geometry = match.geometry

            if geometry is None or geometry.is_empty:
                print(f"EMPTY GEOMETRY: {geo_name}")
                continue

            geometry_wkt = geometry.wkt

            query = text("""
                UPDATE villages
                SET
                    name = :geo_name,
                    geometry = ST_SetSRID(
                        ST_GeomFromText(:geometry),
                        4326
                    )
                WHERE id = :id
            """)

            result = db.execute(
                query,
                {
                    "id": village_id,
                    "geo_name": geo_name,
                    "geometry": geometry_wkt
                }
            )

            if result.rowcount > 0:
                print(
                    f"UPDATED: {db_name} -> {geo_name}"
                )
                updated += 1

        db.commit()

        print()
        print("=" * 50)
        print(f"Updated: {updated}")
        print(f"Not found: {not_found}")
        print("=" * 50)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def main():
    print("Village boundary import started")
    print()

    gdf = load_geojson()

    print()
    print(f"Total GeoJSON records: {len(gdf)}")

    update_villages(gdf)

    print()
    print("Import completed successfully")


if __name__ == "__main__":
    main()