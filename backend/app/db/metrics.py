from prometheus_client import Gauge
from prometheus_client import Counter, Histogram

db_query_total = Counter(
    "civix_db_query_total",
    "Total database queries executed",
    ["operation"]
)

db_query_errors_total = Counter(
    "civix_db_query_errors_total",
    "Total database query execution errors",
    ["operation"]
)
db_query_errors_total.labels(operation="SELECT")
db_query_errors_total.labels(operation="INSERT")
db_query_errors_total.labels(operation="UPDATE")
db_query_errors_total.labels(operation="DELETE")

db_query_duration = Histogram(
    "civix_db_query_duration_seconds",
    "Database query execution duration",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5)
)
db_slow_queries_total = Counter(
    "civix_db_slow_queries_total",
    "Total database queries exceeding the slow query threshold",
    ["operation"]
)

db_slow_query_duration = Histogram(
    "civix_db_slow_query_duration_seconds",
    "Execution duration of slow database queries",
    ["operation"]
)

SLOW_QUERY_THRESHOLD_SECONDS = 0.5
db_slow_queries_total.labels(operation="SELECT")
db_slow_queries_total.labels(operation="INSERT")
db_slow_queries_total.labels(operation="UPDATE")
db_slow_queries_total.labels(operation="DELETE")

db_slow_query_duration.labels(operation="SELECT")
db_slow_query_duration.labels(operation="INSERT")
db_slow_query_duration.labels(operation="UPDATE")
db_slow_query_duration.labels(operation="DELETE")
db_pool_size = Gauge(
    "civix_db_pool_size",
    "Configured database connection pool size"
)

db_pool_checked_out = Gauge(
    "civix_db_pool_checked_out",
    "Connections currently checked out"
)

db_pool_checked_in = Gauge(
    "civix_db_pool_checked_in",
    "Connections currently idle in the pool"
)

db_pool_overflow = Gauge(
    "civix_db_pool_overflow",
    "Current database connection pool overflow"
)

db_pool_capacity = Gauge(
    "civix_db_pool_capacity",
    "Maximum database connection pool capacity"
)

def update_db_pool_metrics():
    from backend.app.db.db import engine

    pool = engine.pool

    db_pool_size.set(pool.size())
    db_pool_checked_out.set(pool.checkedout())
    db_pool_checked_in.set(pool.checkedin())
    db_pool_overflow.set(max(0, pool.overflow()))
    db_pool_capacity.set(pool.size() + engine.pool._max_overflow)
