
from sqlalchemy import text
from backend.app.db.db import engine

query = """
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN (
    'complaints',
    'users',
    'admins',
    'notifications',
    'complaint_history',
    'assignments'
)
ORDER BY tablename, indexname;
"""

try:
    with engine.connect() as connection:
        rows = connection.execute(text(query)).fetchall()

        if not rows:
            print("No indexes found.")

        for row in rows:
            print("\nTable:", row.tablename)
            print("Index:", row.indexname)
            print("Definition:", row.indexdef)

except Exception as error:
    print("Database inspection failed:", error)
