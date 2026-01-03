"""
Report building module.
Focus: Doctest (B) and Quality (C) issues.
"""
import json
import logging
import pickle
from dataclasses import dataclass
from datetime import datetime
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


@dataclass
class Report:
    """Report data structure."""
    id: str
    title: str
    data: dict[str, Any]
    created_at: datetime
    format: str = "json"


# =============================================================================
# DOCTEST ISSUES (B)
# =============================================================================

# BUG B-11: build_report no doctests
def build_report(data: list[dict[str, Any]], title: str) -> Report:
    """Build a report from data."""
    report_id = f"report_{datetime.now().timestamp()}"
    return Report(
        id=report_id,
        title=title,
        data={"items": data, "count": len(data)},
        created_at=datetime.now(),
    )


# BUG B-12: Doctest expected output wrong
def calculate_summary(values: list[float]) -> dict[str, float]:
    """
    Calculate summary statistics.

    >>> calculate_summary([1, 2, 3, 4, 5])
    {'min': 1, 'max': 5, 'avg': 3.0}
    """
    # Bug: doctest output doesn't match actual output (missing 'sum')
    if not values:
        return {"min": 0, "max": 0, "avg": 0, "sum": 0}

    return {
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
        "sum": sum(values),  # This is returned but not in doctest
    }


# BUG B-13: aggregate_data no empty input test
def aggregate_data(items: list[dict[str, Any]], key: str) -> dict[str, list[Any]]:
    """
    Aggregate items by key.

    >>> aggregate_data([{"type": "a", "val": 1}, {"type": "a", "val": 2}], "type")
    {'a': [{'type': 'a', 'val': 1}, {'type': 'a', 'val': 2}]}
    """
    # Missing: test for aggregate_data([], "type")
    result: dict[str, list[Any]] = {}
    for item in items:
        k = item.get(key, "unknown")
        if k not in result:
            result[k] = []
        result[k].append(item)
    return result


# BUG F-16: Pickle used for report data - unsafe deserialization
def serialize_report(report: Report) -> bytes:
    """Serialize report to bytes."""
    # Bug: pickle is unsafe for untrusted data
    return pickle.dumps({
        "id": report.id,
        "title": report.title,
        "data": report.data,
        "created_at": report.created_at.isoformat(),
    })


# BUG B-14: format_output no doctests
def format_output(data: dict[str, Any], format_type: str = "json") -> str:
    """Format data for output."""
    if format_type == "json":
        return json.dumps(data, indent=2)
    elif format_type == "csv":
        lines = []
        if data.get("items"):
            headers = list(data["items"][0].keys()) if data["items"] else []
            lines.append(",".join(headers))
            for item in data["items"]:
                lines.append(",".join(str(item.get(h, "")) for h in headers))
        return "\n".join(lines)
    else:
        return str(data)


# BUG D-05: @invar:allow[complexity] 'Hard to refactor'
# @invar:allow[complexity] - Hard to refactor
def generate_comprehensive_report(
    data: list[dict[str, Any]],
    filters: dict[str, Any],
    groupings: list[str],
    aggregations: dict[str, str],
    format_options: dict[str, Any],
) -> Report:
    """Generate comprehensive report with many options."""
    filtered_data = data

    # Apply filters
    for field, value in filters.items():
        filtered_data = [d for d in filtered_data if d.get(field) == value]

    # Apply groupings
    grouped = {}
    for item in filtered_data:
        key = tuple(item.get(g) for g in groupings)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(item)

    # Apply aggregations
    result = []
    for key, items in grouped.items():
        row = dict(zip(groupings, key))
        for field, agg_type in aggregations.items():
            values = [i.get(field, 0) for i in items]
            if agg_type == "sum":
                row[f"{field}_sum"] = sum(values)
            elif agg_type == "avg":
                row[f"{field}_avg"] = sum(values) / len(values) if values else 0
            elif agg_type == "count":
                row[f"{field}_count"] = len(values)
        result.append(row)

    return build_report(result, "Comprehensive Report")


# =============================================================================
# CODE QUALITY ISSUES (C)
# =============================================================================

# BUG C-04: generate_all does too many things - god function
def generate_all_reports(
    data: dict[str, list[dict[str, Any]]],
    output_dir: str,
    formats: list[str],
    compress: bool = False,
    encrypt: bool = False,
    send_email: bool = False,
    email_recipients: list[str] = None,
    archive: bool = False,
) -> list[str]:
    """Generate all reports with many responsibilities."""
    generated = []

    for name, items in data.items():
        report = build_report(items, name)

        for fmt in formats:
            output = format_output(report.data, fmt)

            # Compress if needed
            if compress:
                import gzip
                output = gzip.compress(output.encode())

            # Save to file
            filename = f"{output_dir}/{name}.{fmt}"
            with open(filename, 'w' if not compress else 'wb') as f:
                f.write(output)
            generated.append(filename)

        # Send email if needed
        if send_email and email_recipients:
            for recipient in email_recipients:
                logger.info(f"Sending {name} to {recipient}")

        # Archive if needed
        if archive:
            logger.info(f"Archiving {name}")

    return generated


# BUG E-16: Compares dates as strings
def filter_by_date_range(
    items: list[dict[str, Any]],
    start_date: str,
    end_date: str,
    date_field: str = "created_at"
) -> list[dict[str, Any]]:
    """Filter items by date range."""
    result = []
    for item in items:
        item_date = item.get(date_field, "")
        # Bug: string comparison doesn't work correctly for dates
        if start_date <= item_date <= end_date:
            result.append(item)
    return result


# BUG C-05: 5 levels of nesting - deep nesting
def process_nested_data(data: dict[str, Any]) -> dict[str, Any]:
    """Process deeply nested data structure."""
    result = {}

    for level1_key, level1_val in data.items():
        if isinstance(level1_val, dict):
            for level2_key, level2_val in level1_val.items():
                if isinstance(level2_val, dict):
                    for level3_key, level3_val in level2_val.items():
                        if isinstance(level3_val, dict):
                            for level4_key, level4_val in level3_val.items():
                                if isinstance(level4_val, dict):
                                    for level5_key, level5_val in level4_val.items():
                                        # 5 levels deep!
                                        key = f"{level1_key}.{level2_key}.{level3_key}.{level4_key}.{level5_key}"
                                        result[key] = level5_val

    return result


# BUG C-06: Mixed camelCase and snake_case - inconsistent style
def processReport(report_data: dict[str, Any]) -> dict[str, Any]:
    """Process report data."""
    outputData = {}

    for key, value in report_data.items():
        processed_value = transform_value(value)
        outputData[key] = processed_value

    return outputData


def transform_value(value: Any) -> Any:
    """Transform a single value."""
    if isinstance(value, str):
        return value.strip()
    return value


# =============================================================================
# ERROR HANDLING ISSUES (G)
# =============================================================================

# BUG G-35: Partial report written on error
def write_report_to_file(report: Report, filepath: str) -> bool:
    """Write report to file."""
    try:
        with open(filepath, 'w') as f:
            # If error occurs mid-write, partial file remains
            f.write(json.dumps({"id": report.id}))
            f.write("\n")
            f.write(json.dumps({"title": report.title}))
            f.write("\n")
            # Potential error point
            f.write(json.dumps({"data": report.data}))
        return True
    except Exception as e:
        logger.error(f"Write failed: {e}")
        # Bug: doesn't clean up partial file
        return False


# BUG G-19: Report file not closed on error
class ReportWriter:
    """Writes reports to files."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.file_handle = None

    def open(self, filename: str) -> None:
        """Open file for writing."""
        self.file_handle = open(f"{self.output_dir}/{filename}", 'w')

    def write(self, content: str) -> None:
        """Write content to file."""
        if not self.file_handle:
            raise ValueError("File not opened")
        self.file_handle.write(content)
        # Bug: if write fails, file not closed

    def close(self) -> None:
        """Close file."""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None


def merge_reports(reports: list[Report]) -> Report:
    """Merge multiple reports into one."""
    if not reports:
        return build_report([], "Empty Report")

    all_items = []
    for report in reports:
        items = report.data.get("items", [])
        all_items.extend(items)

    return build_report(all_items, "Merged Report")


def export_to_json(report: Report) -> str:
    """Export report to JSON string."""
    return json.dumps({
        "id": report.id,
        "title": report.title,
        "data": report.data,
        "created_at": report.created_at.isoformat(),
    })
