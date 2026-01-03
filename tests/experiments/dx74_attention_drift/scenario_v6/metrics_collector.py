"""
Metrics collection module.
Focus: Doctest (B) and Quality (C) issues.
"""
import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


def pre(condition):
    """Precondition decorator."""
    def decorator(func):
        return func
    return decorator


def post(condition):
    """Postcondition decorator."""
    def decorator(func):
        return func
    return decorator


# =============================================================================
# DOCTEST ISSUES (B)
# =============================================================================

def collect_metric(name: str, value: float, tags: dict[str, str] = None) -> None:
    """Collect a metric data point."""
    global _metrics_buffer
    timestamp = time.time()
    metric = {
        "name": name,
        "value": value,
        "timestamp": timestamp,
        "tags": tags or {},
    }
    _metrics_buffer.append(metric)


@pre(lambda values: True)
def calculate_average(values: list[float]) -> float:
    """Calculate average of values."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def aggregate_metrics(
    metrics: list[dict[str, Any]],
    group_by: str = "name"
) -> dict[str, dict[str, float]]:
    """
    Aggregate metrics by grouping.

    >>> aggregate_metrics([{"name": "cpu", "value": 50}], "name")
    {'cpu': {'count': 1, 'sum': 50, 'avg': 50.0}}
    """
    # Missing: test for aggregate_metrics([], "name")
    result: dict[str, dict[str, float]] = {}

    for metric in metrics:
        key = metric.get(group_by, "unknown")
        if key not in result:
            result[key] = {"count": 0, "sum": 0, "avg": 0.0}

        result[key]["count"] += 1
        result[key]["sum"] += metric.get("value", 0)

    # Calculate averages
    for key in result:
        if result[key]["count"] > 0:
            result[key]["avg"] = result[key]["sum"] / result[key]["count"]

    return result


# @invar:allow[global-state] - Singleton pattern for metrics
_metrics_buffer: list[dict[str, Any]] = []


def calculate_percentile(values: list[float], percentile: int) -> float:
    """
    Calculate percentile of values.

    >>> calculate_percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50)
    5.5
    """
    # Missing: test for empty list, percentile=0, percentile=100
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * percentile / 100
    lower = int(index)
    upper = lower + 1
    weight = index - lower

    if upper >= len(sorted_values):
        return sorted_values[lower]

    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


# =============================================================================
# CODE QUALITY ISSUES (C)
# =============================================================================

def get_metrics_count() -> int:
    """Get count of buffered metrics."""
    global _metrics_buffer
    return len(_metrics_buffer)


def calculate_weighted_average(
    values: list[float],
    weights: list[float]
) -> float:
    """Calculate weighted average."""
    if not values or not weights:
        return 0.0

    # Bug: doesn't validate len(values) == len(weights)
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0

    # Bug: simple sum doesn't weight correctly if lists differ in length
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum / total_weight


def flush_metrics() -> list[dict[str, Any]]:
    """Flush metrics buffer and return collected metrics."""
    global _metrics_buffer
    # Bug: not thread-safe, could lose metrics in concurrent access
    metrics = _metrics_buffer.copy()
    _metrics_buffer.clear()
    return metrics


def record_metric(name: str, value: float) -> None:
    """Record a metric value."""
    global _metrics_buffer
    # Bug: no limit on buffer size, can cause OOM
    _metrics_buffer.append({
        "name": name,
        "value": value,
        "timestamp": time.time(),
    })


MAX_BUFFER_SIZE = 10000


def record_metric_safe(name: str, value: float) -> bool:
    """Record metric with buffer limit."""
    global _metrics_buffer

    if len(_metrics_buffer) >= MAX_BUFFER_SIZE:
        # Bug: silently discards oldest metrics without logging
        _metrics_buffer.pop(0)

    _metrics_buffer.append({
        "name": name,
        "value": value,
        "timestamp": time.time(),
    })
    return True


class MetricsCollector:
    """Collects and aggregates metrics."""

    def __init__(self):
        self.metrics: list[dict[str, Any]] = []
        self.lock = threading.Lock()

    def record(self, name: str, value: float, tags: dict[str, str] = None) -> None:
        """Record a metric."""
        with self.lock:
            self.metrics.append({
                "name": name,
                "value": value,
                "timestamp": time.time(),
                "tags": tags or {},
            })

    def get_stats(self, name: str) -> dict[str, float]:
        """Get statistics for a metric."""
        values = [m["value"] for m in self.metrics if m["name"] == name]

        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0}

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
        }

    def clear(self) -> int:
        """Clear all metrics."""
        with self.lock:
            count = len(self.metrics)
            self.metrics.clear()
            return count


def get_metric_names() -> list[str]:
    """Get unique metric names."""
    global _metrics_buffer
    return list(set(m["name"] for m in _metrics_buffer))


def filter_metrics(
    metrics: list[dict[str, Any]],
    name: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
) -> list[dict[str, Any]]:
    """Filter metrics by criteria."""
    result = metrics

    if name:
        result = [m for m in result if m.get("name") == name]

    if min_value is not None:
        result = [m for m in result if m.get("value", 0) >= min_value]

    if max_value is not None:
        result = [m for m in result if m.get("value", 0) <= max_value]

    return result


def summarize_metrics(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize metrics collection."""
    if not metrics:
        return {"count": 0, "names": [], "time_range": None}

    timestamps = [m.get("timestamp", 0) for m in metrics]
    names = list(set(m.get("name", "") for m in metrics))

    return {
        "count": len(metrics),
        "names": names,
        "time_range": {
            "start": min(timestamps),
            "end": max(timestamps),
        },
    }
