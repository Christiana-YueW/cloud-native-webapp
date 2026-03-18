"""
Database metrics collection using SQLAlchemy event hooks.
"""
import logging
import time
from sqlalchemy import event
from sqlalchemy.engine import Engine
from app.metrics import send_timing

logger = logging.getLogger("csye6225")

# Prevent duplicate listener registration
_db_metrics_initialized = False


def setup_db_metrics() -> None:
    """
    Set up SQLAlchemy event listeners to track database query performance.
    
    This registers hooks that automatically time every SQL query executed
    through SQLAlchemy and send timing metrics to CloudWatch.
    
    Note: This function should only be called once during application startup.
    """
    global _db_metrics_initialized
    
    if _db_metrics_initialized:
        logger.warning("Database metrics already initialized, skipping")
        return
    
    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time."""
        conn.info.setdefault('query_start_time', []).append(time.perf_counter())
    
    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Calculate and send query duration metric."""
        start_times = conn.info.get('query_start_time', [])
        
        if not start_times:
            logger.warning("db_metrics_missing_start_time")
            return
        
        total_time = time.perf_counter() - start_times.pop()
        duration_ms = total_time * 1000
        
        # Determine operation type from SQL statement
        operation = _extract_operation(statement)
        
        # Send timing metric
        send_timing(f"db.{operation}.duration", duration_ms)
        
        # Log slow queries (> 100ms)
        if duration_ms > 100:
            logger.warning(
                f"slow_query operation={operation} duration_ms={duration_ms:.2f} "
                f"statement={statement[:100]}"
            )
    
    _db_metrics_initialized = True
    logger.info("Database metrics initialized")


def _extract_operation(statement: str) -> str:
    """
    Extract operation type from SQL statement.
    
    Returns: select, insert, update, delete, or other
    """
    statement_upper = statement.strip().upper()
    
    if statement_upper.startswith('SELECT'):
        return 'select'
    elif statement_upper.startswith('INSERT'):
        return 'insert'
    elif statement_upper.startswith('UPDATE'):
        return 'update'
    elif statement_upper.startswith('DELETE'):
        return 'delete'
    else:
        return 'other'