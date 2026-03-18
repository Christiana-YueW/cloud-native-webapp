"""
Metrics module for CloudWatch custom metrics via StatsD.

This module provides a centralized way to send metrics to CloudWatch
through the CloudWatch Agent's StatsD interface.
"""
import statsd
import logging
from contextlib import contextmanager
import time
from typing import Optional

logger = logging.getLogger(__name__)

# StatsD client - will be initialized on first use
_statsd_client: Optional[statsd.StatsClient] = None


def get_statsd_client() -> Optional[statsd.StatsClient]:
    """
    Get or create the StatsD client.
    
    CloudWatch Agent listens on localhost:8125 by default.
    """
    global _statsd_client
    
    if _statsd_client is None:
        try:
            _statsd_client = statsd.StatsClient(
                host='127.0.0.1',
                port=8125,
                prefix='csye6225'
            )
        except Exception as e:
            logger.warning(f"Failed to initialize StatsD client: {e}")
            return None
    
    return _statsd_client


def increment_counter(metric_name: str, count: int = 1) -> None:
    """
    Increment a counter metric.
    
    Args:
        metric_name: Name of the metric (e.g., 'api.healthz.count')
        count: Amount to increment (default: 1)
    """
    client = get_statsd_client()
    if client:
        try:
            client.incr(metric_name, count)
        except Exception:
            # Silently fail - metrics are best-effort
            pass


def send_timing(metric_name: str, duration_ms: float) -> None:
    """
    Send a timing metric.
    
    Args:
        metric_name: Name of the timer metric (e.g., 'api.healthz.duration')
        duration_ms: Duration in milliseconds
    """
    client = get_statsd_client()
    if client:
        try:
            client.timing(metric_name, duration_ms)
        except Exception:
            # Silently fail - metrics are best-effort
            pass


@contextmanager
def timer(metric_name: str):
    """
    Context manager for timing operations.
    
    Usage:
        with timer('api.healthz.duration'):
            # your code here
            pass
    
    Args:
        metric_name: Name of the timer metric
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000  # Convert to milliseconds
        send_timing(metric_name, duration_ms)