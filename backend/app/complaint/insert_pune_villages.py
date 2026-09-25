import os
import sys
import geopandas as gpd
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from backend.app.db.db import SessionLocal

GEOJSON_PATH = "backend/app/complaint/dataset/vb_soi_mh.GeoJSON"
TALUKA_ID = 8

gdf = gpd.read_file(GEOJSON_PATH)

gdf["district_clean"] = gdf["district"].astype(str).str.strip().str.lower()
gdf["taluka_clean"] = gdf["subdistric"].astype(str).str.strip().str.lower()

gdf = gdf[
    (gdf["district_clean"] == "sangli") &
    (gdf["taluka_clean"] == "palus")
].copy()

gdf = gdf.drop_duplicates(subset=["village", "vlcode"])

db = SessionLocal()

try:
    inserted = 0

    for _, row in gdf.iterrows():
        name = str(row["village"]).strip()
        vlcode = str(row["vlcode"]).strip()
        geometry = row.geometry

        if not name or geometry is None or geometry.is_empty:
            continue

        wkt = geometry.wkt

        db.execute(
            text("""
                INSERT INTO villages (name, taluka_id, vlcode, geometry)
                VALUES (
                    :name,
                    :taluka_id,
                    :vlcode,
                    ST_GeomFromText(:geometry, 4326)
                )
            """),
            {
                "name": name,
                "taluka_id": TALUKA_ID,
                "vlcode": vlcode,
                "geometry": wkt
            }
        )

        inserted += 1

    db.commit()

    print("=" * 50)
    print("PALUS VILLAGE IMPORT COMPLETED")
    print("=" * 50)
    print("GeoJSON villages :", len(gdf))
    print("Inserted          :", inserted)
    print("=" * 50)

except Exception as e:
    db.rollback()
    print("IMPORT FAILED")
    print(e)

finally:
    db.close()