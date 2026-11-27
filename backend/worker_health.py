from datetime import datetime
from backend.app.db.db import SessionLocal
from backend.app.db.model import WorkerHeartbeat

STALE_AFTER_SECONDS = 60

def main():
    db = SessionLocal()
    try:
        workers = db.query(WorkerHeartbeat).order_by(
            WorkerHeartbeat.last_heartbeat_at.desc()
        ).all()

        if not workers:
            print("UNHEALTHY: No worker heartbeat records found.")
            raise SystemExit(1)

        now = datetime.utcnow()
        healthy_count = 0

        for worker in workers:
            age = (now - worker.last_heartbeat_at).total_seconds()
            healthy = worker.status == "running" and age <= STALE_AFTER_SECONDS

            if healthy:
                healthy_count += 1

            print(
                f"Worker: {worker.worker_id} | "
                f"Status: {worker.status} | "
                f"Heartbeat age: {age:.1f}s | "
                f"Health: {'HEALTHY' if healthy else 'UNHEALTHY'}"
            )

        if healthy_count == 0:
            print("OVERALL: UNHEALTHY")
            raise SystemExit(1)

        print(f"OVERALL: HEALTHY ({healthy_count} active worker(s))")

    finally:
        db.close()

if __name__ == "__main__":
    main()
