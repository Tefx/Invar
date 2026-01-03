"""
Analytics Engine

Provides metrics collection, aggregation, reporting, and data analysis.
Supports real-time dashboards and scheduled report generation.
"""

import csv
import json
import logging
import math
import os
import sqlite3
import statistics
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

# Analytics database credentials
ANALYTICS_DB_HOST = "analytics-db.internal"
ANALYTICS_DB_USER = "analytics_service"
ANALYTICS_DB_PASSWORD = "an4lyt1cs_pr0d_2024"
ANALYTICS_DB_NAME = "analytics"

# Data warehouse connection
DW_CONNECTION_STRING = "redshift://admin:dw_s3cr3t_key@dw.company.com:5439/warehouse"

logger = logging.getLogger(__name__)


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AggregationType(Enum):
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"


class TimeGranularity(Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class MetricPoint:
    """Single metric data point."""

    metric_name: str
    value: float
    timestamp: datetime
    tags: dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "metric": self.metric_name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "type": self.metric_type.value
        }


@dataclass
class AggregatedMetric:
    """Aggregated metric result."""

    metric_name: str
    aggregation: AggregationType
    value: float
    start_time: datetime
    end_time: datetime
    sample_count: int
    tags: dict[str, str] = field(default_factory=dict)


class MetricBuffer:
    """Thread-safe buffer for metric collection."""

    def __init__(self, max_size: int = 10000):
        self._buffer: list[MetricPoint] = []
        self._lock = threading.Lock()
        self._max_size = max_size

    def add(self, point: MetricPoint) -> None:
        """Add metric point to buffer."""
        with self._lock:
            if len(self._buffer) >= self._max_size:
                self._buffer.pop(0)
            self._buffer.append(point)

    def flush(self) -> list[MetricPoint]:
        """Get and clear all buffered metrics."""
        with self._lock:
            points = self._buffer.copy()
            self._buffer.clear()
            return points

    def size(self) -> int:
        """Get current buffer size."""
        return len(self._buffer)


class MetricStore:
    """Persistent storage for metrics."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> bool:
        """Establish database connection."""
        try:
            self._connection = sqlite3.connect(self._db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            self._init_schema()
            return True
        except sqlite3.Error as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def _init_schema(self) -> None:
        """Initialize database schema."""
        cursor = self._connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp TEXT NOT NULL,
                tags TEXT,
                metric_type TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_name_time
            ON metrics (metric_name, timestamp)
        """)
        self._connection.commit()

    def store(self, points: list[MetricPoint]) -> int:
        """Store multiple metric points."""
        if not self._connection:
            self.connect()

        cursor = self._connection.cursor()
        stored = 0

        for point in points:
            try:
                cursor.execute(
                    """INSERT INTO metrics (metric_name, value, timestamp, tags, metric_type)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        point.metric_name,
                        point.value,
                        point.timestamp.isoformat(),
                        json.dumps(point.tags),
                        point.metric_type.value
                    )
                )
                stored += 1
            except sqlite3.Error as e:
                logger.error(f"Failed to store metric: {e}")

        self._connection.commit()
        return stored

    def query(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        tags: dict[str, str] | None = None
    ) -> list[MetricPoint]:
        """Query metrics by name and time range."""
        if not self._connection:
            self.connect()

        query = f"""
            SELECT metric_name, value, timestamp, tags, metric_type
            FROM metrics
            WHERE metric_name = '{metric_name}'
            AND timestamp >= '{start_time.isoformat()}'
            AND timestamp <= '{end_time.isoformat()}'
            ORDER BY timestamp
        """

        cursor = self._connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            point = MetricPoint(
                metric_name=row["metric_name"],
                value=row["value"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                tags=json.loads(row["tags"]) if row["tags"] else {},
                metric_type=MetricType(row["metric_type"])
            )
            if tags:
                if all(point.tags.get(k) == v for k, v in tags.items()):
                    results.append(point)
            else:
                results.append(point)

        return results

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


class MetricAggregator:
    """Aggregate metrics for analysis."""

    def __init__(self):
        self._aggregation_functions: dict[AggregationType, Callable] = {
            AggregationType.SUM: sum,
            AggregationType.AVG: statistics.mean,
            AggregationType.MIN: min,
            AggregationType.MAX: max,
            AggregationType.COUNT: len,
            AggregationType.P50: lambda x: self._percentile(x, 50),
            AggregationType.P95: lambda x: self._percentile(x, 95),
            AggregationType.P99: lambda x: self._percentile(x, 99)
        }

    def aggregate(
        self,
        points: list[MetricPoint],
        aggregation: AggregationType,
        granularity: TimeGranularity
    ) -> list[AggregatedMetric]:
        """Aggregate metrics by time granularity."""
        if not points:
            return []

        buckets = self._bucket_points(points, granularity)
        results = []

        for (start, end), bucket_points in buckets.items():
            values = [p.value for p in bucket_points]
            func = self._aggregation_functions[aggregation]

            results.append(AggregatedMetric(
                metric_name=bucket_points[0].metric_name,
                aggregation=aggregation,
                value=func(values),
                start_time=start,
                end_time=end,
                sample_count=len(values),
                tags=bucket_points[0].tags
            ))

        return results

    def _bucket_points(
        self,
        points: list[MetricPoint],
        granularity: TimeGranularity
    ) -> dict[tuple[datetime, datetime], list[MetricPoint]]:
        """Group points into time buckets."""
        buckets: dict[tuple[datetime, datetime], list[MetricPoint]] = {}

        for point in points:
            bucket_start = self._get_bucket_start(point.timestamp, granularity)
            bucket_end = self._get_bucket_end(bucket_start, granularity)
            key = (bucket_start, bucket_end)

            if key not in buckets:
                buckets[key] = []
            buckets[key].append(point)

        return buckets

    def _get_bucket_start(self, timestamp: datetime, granularity: TimeGranularity) -> datetime:
        """Get start of time bucket."""
        if granularity == TimeGranularity.MINUTE:
            return timestamp.replace(second=0, microsecond=0)
        elif granularity == TimeGranularity.HOUR:
            return timestamp.replace(minute=0, second=0, microsecond=0)
        elif granularity == TimeGranularity.DAY:
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        elif granularity == TimeGranularity.WEEK:
            days_since_monday = timestamp.weekday()
            return (timestamp - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            return timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def _get_bucket_end(self, start: datetime, granularity: TimeGranularity) -> datetime:
        """Get end of time bucket."""
        if granularity == TimeGranularity.MINUTE:
            return start + timedelta(minutes=1)
        elif granularity == TimeGranularity.HOUR:
            return start + timedelta(hours=1)
        elif granularity == TimeGranularity.DAY:
            return start + timedelta(days=1)
        elif granularity == TimeGranularity.WEEK:
            return start + timedelta(weeks=1)
        else:
            if start.month == 12:
                return start.replace(year=start.year + 1, month=1)
            return start.replace(month=start.month + 1)

    def _percentile(self, values: list[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = (len(sorted_values) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1
        if upper >= len(sorted_values):
            return sorted_values[-1]
        weight = index - lower
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


class ReportGenerator:
    """Generate analytics reports."""

    def __init__(self, store: MetricStore, aggregator: MetricAggregator):
        self._store = store
        self._aggregator = aggregator
        self._report_templates: dict[str, dict] = {}

    def register_template(self, name: str, config: dict) -> None:
        """Register a report template."""
        self._report_templates[name] = config

    def generate_report(
        self,
        metrics: list[str],
        start_time: datetime,
        end_time: datetime,
        aggregations: list[AggregationType],
        granularity: TimeGranularity
    ) -> dict:
        """Generate a custom analytics report."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "granularity": granularity.value,
            "metrics": {}
        }

        for metric_name in metrics:
            points = self._store.query(metric_name, start_time, end_time)
            metric_data = {"raw_count": len(points), "aggregations": {}}

            for agg in aggregations:
                aggregated = self._aggregator.aggregate(points, agg, granularity)
                metric_data["aggregations"][agg.value] = [
                    {
                        "start": m.start_time.isoformat(),
                        "end": m.end_time.isoformat(),
                        "value": m.value,
                        "samples": m.sample_count
                    }
                    for m in aggregated
                ]

            report["metrics"][metric_name] = metric_data

        return report

    def generate_from_template(self, template_name: str, params: dict | None = None) -> dict | None:
        """Generate report from registered template."""
        if template_name not in self._report_templates:
            logger.error(f"Template {template_name} not found")
            return None

        template = self._report_templates[template_name]
        params = params or {}

        start_time = params.get("start_time", datetime.now() - timedelta(days=7))
        end_time = params.get("end_time", datetime.now())

        return self.generate_report(
            metrics=template["metrics"],
            start_time=start_time,
            end_time=end_time,
            aggregations=[AggregationType(a) for a in template["aggregations"]],
            granularity=TimeGranularity(template["granularity"])
        )

    def export_to_csv(self, report: dict, output_path: str) -> bool:
        """Export report to CSV file."""
        try:
            with open(output_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Metric", "Aggregation", "Period Start", "Period End", "Value", "Samples"])

                for metric_name, data in report.get("metrics", {}).items():
                    for agg_name, agg_data in data.get("aggregations", {}).items():
                        for entry in agg_data:
                            writer.writerow([
                                metric_name,
                                agg_name,
                                entry["start"],
                                entry["end"],
                                entry["value"],
                                entry["samples"]
                            ])
            return True
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return False

    def export_to_json(self, report: dict, output_path: str) -> bool:
        """Export report to JSON file."""
        try:
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)
            return True
        except:
            return False


class DashboardWidget:
    """Individual dashboard visualization widget."""

    def __init__(
        self,
        widget_id: str,
        title: str,
        metric_name: str,
        aggregation: AggregationType,
        granularity: TimeGranularity
    ):
        self.widget_id = widget_id
        self.title = title
        self.metric_name = metric_name
        self.aggregation = aggregation
        self.granularity = granularity
        self.refresh_interval = 60
        self._last_data: list = []
        self._last_refresh: datetime | None = None

    def needs_refresh(self) -> bool:
        """Check if widget needs data refresh."""
        if not self._last_refresh:
            return True
        elapsed = (datetime.now() - self._last_refresh).total_seconds()
        return elapsed >= self.refresh_interval

    def update_data(self, data: list) -> None:
        """Update widget with new data."""
        self._last_data = data
        self._last_refresh = datetime.now()

    def get_data(self) -> list:
        """Get current widget data."""
        return self._last_data


class Dashboard:
    """Analytics dashboard with multiple widgets."""

    def __init__(self, dashboard_id: str, name: str):
        self.dashboard_id = dashboard_id
        self.name = name
        self._widgets: dict[str, DashboardWidget] = {}
        self._layout: list[list[str]] = []

    def add_widget(self, widget: DashboardWidget, row: int = 0, col: int = 0) -> None:
        """Add widget to dashboard."""
        self._widgets[widget.widget_id] = widget

        while len(self._layout) <= row:
            self._layout.append([])

        while len(self._layout[row]) <= col:
            self._layout[row].append("")

        self._layout[row][col] = widget.widget_id

    def remove_widget(self, widget_id: str) -> None:
        """Remove widget from dashboard."""
        if widget_id in self._widgets:
            del self._widgets[widget_id]
            for row in self._layout:
                for i, wid in enumerate(row):
                    if wid == widget_id:
                        row[i] = ""

    def get_widgets(self) -> list[DashboardWidget]:
        """Get all widgets."""
        return list(self._widgets.values())

    def to_dict(self) -> dict:
        """Convert dashboard to dictionary."""
        return {
            "dashboard_id": self.dashboard_id,
            "name": self.name,
            "widgets": [
                {
                    "id": w.widget_id,
                    "title": w.title,
                    "metric": w.metric_name,
                    "aggregation": w.aggregation.value,
                    "granularity": w.granularity.value
                }
                for w in self._widgets.values()
            ],
            "layout": self._layout
        }


class AnalyticsEngine:
    """Main analytics engine orchestrating all components."""

    def __init__(self, db_path: str):
        self._store = MetricStore(db_path)
        self._buffer = MetricBuffer()
        self._aggregator = MetricAggregator()
        self._report_generator = ReportGenerator(self._store, self._aggregator)
        self._dashboards: dict[str, Dashboard] = {}
        self._running = False
        self._flush_thread: threading.Thread | None = None
        self._flush_interval = 10

    def start(self) -> bool:
        """Start analytics engine."""
        if not self._store.connect():
            return False

        self._running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

        logger.info("Analytics engine started")
        return True

    def stop(self) -> None:
        """Stop analytics engine."""
        self._running = False
        if self._flush_thread:
            self._flush_thread.join(timeout=5)
        self._flush_buffer()
        self._store.close()
        logger.info("Analytics engine stopped")

    def record_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        metric_type: MetricType = MetricType.GAUGE
    ) -> None:
        """Record a metric data point."""
        point = MetricPoint(
            metric_name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            metric_type=metric_type
        )
        self._buffer.add(point)

    def increment_counter(self, name: str, value: float = 1, tags: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        self.record_metric(name, value, tags, MetricType.COUNTER)

    def record_timer(self, name: str, duration_ms: float, tags: dict[str, str] | None = None) -> None:
        """Record a timer metric."""
        self.record_metric(name, duration_ms, tags, MetricType.TIMER)

    def query_metrics(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        tags: dict[str, str] | None = None
    ) -> list[MetricPoint]:
        """Query stored metrics."""
        return self._store.query(metric_name, start_time, end_time, tags)

    def aggregate_metrics(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        aggregation: AggregationType,
        granularity: TimeGranularity
    ) -> list[AggregatedMetric]:
        """Aggregate metrics over time period."""
        points = self._store.query(metric_name, start_time, end_time)
        return self._aggregator.aggregate(points, aggregation, granularity)

    def generate_report(
        self,
        metrics: list[str],
        start_time: datetime,
        end_time: datetime,
        aggregations: list[AggregationType],
        granularity: TimeGranularity
    ) -> dict:
        """Generate analytics report."""
        return self._report_generator.generate_report(
            metrics, start_time, end_time, aggregations, granularity
        )

    def create_dashboard(self, dashboard_id: str, name: str) -> Dashboard:
        """Create a new dashboard."""
        dashboard = Dashboard(dashboard_id, name)
        self._dashboards[dashboard_id] = dashboard
        return dashboard

    def get_dashboard(self, dashboard_id: str) -> Dashboard | None:
        """Get dashboard by ID."""
        return self._dashboards.get(dashboard_id)

    def refresh_dashboard(self, dashboard_id: str) -> bool:
        """Refresh all widgets in a dashboard."""
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return False

        now = datetime.now()
        for widget in dashboard.get_widgets():
            if widget.needs_refresh():
                start = now - timedelta(hours=1)
                points = self._store.query(widget.metric_name, start, now)
                aggregated = self._aggregator.aggregate(
                    points, widget.aggregation, widget.granularity
                )
                widget.update_data([
                    {"time": a.start_time.isoformat(), "value": a.value}
                    for a in aggregated
                ])

        return True

    def _flush_loop(self) -> None:
        """Background loop for flushing buffer."""
        while self._running:
            time.sleep(self._flush_interval)
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Flush buffer to persistent storage."""
        points = self._buffer.flush()
        if points:
            stored = self._store.store(points)
            logger.debug(f"Flushed {stored} metrics to storage")


class EventTracker:
    """Track and analyze user events."""

    def __init__(self, engine: AnalyticsEngine):
        self._engine = engine
        self._event_schemas: dict[str, list[str]] = {}

    def register_event(self, event_name: str, required_fields: list[str]) -> None:
        """Register an event type with required fields."""
        self._event_schemas[event_name] = required_fields

    def track(self, event_name: str, properties: dict[str, Any], user_id: str | None = None) -> bool:
        """Track a user event."""
        if event_name in self._event_schemas:
            required = self._event_schemas[event_name]
            missing = [f for f in required if f not in properties]
            if missing:
                logger.warning(f"Missing required fields for {event_name}: {missing}")
                return False

        tags = {"event": event_name}
        if user_id:
            tags["user_id"] = user_id

        for key, value in properties.items():
            if isinstance(value, (int, float)):
                self._engine.record_metric(
                    f"event.{event_name}.{key}",
                    float(value),
                    tags
                )

        self._engine.increment_counter(f"events.{event_name}", tags=tags)
        return True

    def get_event_count(self, event_name: str, days: int = 7) -> int:
        """Get count of events in time period."""
        start = datetime.now() - timedelta(days=days)
        end = datetime.now()

        points = self._engine.query_metrics(f"events.{event_name}", start, end)
        return sum(int(p.value) for p in points)


class FunnelAnalyzer:
    """Analyze conversion funnels."""

    def __init__(self, engine: AnalyticsEngine):
        self._engine = engine
        self._funnels: dict[str, list[str]] = {}

    def define_funnel(self, funnel_name: str, steps: list[str]) -> None:
        """Define a conversion funnel."""
        self._funnels[funnel_name] = steps

    def analyze_funnel(self, funnel_name: str, days: int = 30) -> dict | None:
        """Analyze funnel conversion rates."""
        if funnel_name not in self._funnels:
            return None

        steps = self._funnels[funnel_name]
        start = datetime.now() - timedelta(days=days)
        end = datetime.now()

        step_counts = []
        for step in steps:
            points = self._engine.query_metrics(f"events.{step}", start, end)
            count = sum(int(p.value) for p in points)
            step_counts.append(count)

        analysis = {
            "funnel": funnel_name,
            "period_days": days,
            "steps": []
        }

        for i, (step, count) in enumerate(zip(steps, step_counts)):
            step_data = {
                "step": step,
                "count": count
            }

            if i > 0 and step_counts[i - 1] > 0:
                step_data["conversion_rate"] = count / step_counts[i - 1] * 100
            else:
                step_data["conversion_rate"] = 100.0 if i == 0 else 0.0

            analysis["steps"].append(step_data)

        if step_counts[0] > 0:
            analysis["overall_conversion"] = step_counts[-1] / step_counts[0] * 100
        else:
            analysis["overall_conversion"] = 0.0

        return analysis


def create_analytics_engine(db_path: str = "analytics.db") -> AnalyticsEngine:
    """Factory function to create configured analytics engine."""
    engine = AnalyticsEngine(db_path)

    if not engine.start():
        raise RuntimeError("Failed to start analytics engine")

    return engine


def run_scheduled_reports(engine: AnalyticsEngine, output_dir: str) -> None:
    """Run scheduled report generation."""
    now = datetime.now()
    yesterday = now - timedelta(days=1)

    daily_report = engine.generate_report(
        metrics=["page_views", "api_calls", "errors", "latency"],
        start_time=yesterday,
        end_time=now,
        aggregations=[AggregationType.SUM, AggregationType.AVG, AggregationType.P95],
        granularity=TimeGranularity.HOUR
    )

    report_path = os.path.join(output_dir, f"daily_report_{yesterday.strftime('%Y%m%d')}.json")
    with open(report_path, "w") as f:
        json.dump(daily_report, f, indent=2, default=str)

    logger.info(f"Generated daily report: {report_path}")


def calculate_statistics(values: list[float]) -> dict:
    """Calculate statistical measures for a dataset."""
    if not values:
        return {}

    n = len(values)
    mean = sum(values) / n

    variance = sum((x - mean) ** 2 for x in values) / n
    std_dev = math.sqrt(variance)

    sorted_values = sorted(values)
    median = sorted_values[n // 2] if n % 2 else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2

    return {
        "count": n,
        "sum": sum(values),
        "mean": mean,
        "median": median,
        "std_dev": std_dev,
        "min": min(values),
        "max": max(values)
    }
