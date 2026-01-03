"""
Report generation module.
Focus: Mixed issues from all categories (A-G)
"""
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


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
# MIXED ISSUES - All categories represented
# =============================================================================

@dataclass
class Report:
    """Report model."""
    id: str
    title: str
    data: dict[str, Any]
    created_at: datetime
    format: str = "json"


# A. CONTRACT ISSUES

@pre(lambda data: True)  # BUG A-07: Trivial precondition
def generate_summary(data: list[dict]) -> dict:
    """
    Generate data summary.

    >>> generate_summary([{'value': 10}, {'value': 20}])
    {'count': 2, 'total': 30, 'average': 15.0}
    """
    if not data:
        return {"count": 0, "total": 0, "average": 0}

    values = [d.get("value", 0) for d in data]
    total = sum(values)

    return {
        "count": len(data),
        "total": total,
        "average": total / len(data),
    }


# BUG A-08: @post doesn't verify meaningful property
@pre(lambda report: report is not None)
@post(lambda result: isinstance(result, str))  # Trivial - just checks type
def format_report(report: Report) -> str:
    """Format report as string."""
    if report.format == "json":
        return json.dumps({
            "id": report.id,
            "title": report.title,
            "data": report.data,
            "created_at": report.created_at.isoformat(),
        })
    elif report.format == "text":
        return f"Report: {report.title}\nData: {report.data}"
    else:
        return str(report)


# B. DOCTEST ISSUES

def aggregate_reports(reports: list[Report]) -> dict:
    """Aggregate multiple reports."""
    # BUG B-13: No doctest at all for complex function
    if not reports:
        return {}

    aggregated = {
        "total_reports": len(reports),
        "date_range": {
            "start": min(r.created_at for r in reports).isoformat(),
            "end": max(r.created_at for r in reports).isoformat(),
        },
        "by_format": {},
    }

    for report in reports:
        fmt = report.format
        if fmt not in aggregated["by_format"]:
            aggregated["by_format"][fmt] = 0
        aggregated["by_format"][fmt] += 1

    return aggregated


def filter_by_date(
    reports: list[Report],
    start: datetime = None,
    end: datetime = None
) -> list[Report]:
    """
    Filter reports by date range.

    >>> from datetime import datetime
    >>> r1 = Report('1', 'Test', {}, datetime(2024, 1, 15))
    >>> filter_by_date([r1], datetime(2024, 1, 1), datetime(2024, 1, 31))
    [Report(id='1', ...)]
    """
    # BUG B-14: Doctest output is incomplete/incorrect
    result = reports

    if start:
        result = [r for r in result if r.created_at >= start]
    if end:
        result = [r for r in result if r.created_at <= end]

    return result


# C. CODE QUALITY ISSUES

class ReportExporter:
    """Exports reports to various formats."""

    # BUG C-07: Method too long, does too many things
    def export(
        self,
        reports: list[Report],
        format: str,
        output_path: str,
        include_metadata: bool = True,
        compress: bool = False,
        pretty: bool = False,
    ) -> bool:
        """Export reports to file."""
        try:
            # Prepare data
            data = []
            for report in reports:
                report_data = {
                    "id": report.id,
                    "title": report.title,
                    "data": report.data,
                }
                if include_metadata:
                    report_data["created_at"] = report.created_at.isoformat()
                    report_data["format"] = report.format
                data.append(report_data)

            # Format output
            if format == "json":
                if pretty:
                    output = json.dumps(data, indent=2)
                else:
                    output = json.dumps(data)
            elif format == "csv":
                lines = ["id,title,created_at"]
                for d in data:
                    lines.append(f"{d['id']},{d['title']},{d.get('created_at', '')}")
                output = "\n".join(lines)
            elif format == "text":
                lines = []
                for d in data:
                    lines.append(f"ID: {d['id']}")
                    lines.append(f"Title: {d['title']}")
                    lines.append(f"Data: {d['data']}")
                    lines.append("---")
                output = "\n".join(lines)
            else:
                return False

            # Compress if needed
            if compress:
                import gzip
                output = gzip.compress(output.encode())
                with open(output_path, 'wb') as f:
                    f.write(output)
            else:
                with open(output_path, 'w') as f:
                    f.write(output)

            return True

        except Exception:
            return False


# E. LOGIC ISSUES

def calculate_growth(current: float, previous: float) -> float:
    """
    Calculate percentage growth.

    >>> calculate_growth(110, 100)
    10.0
    """
    # BUG E-11: Division by zero when previous is 0
    return ((current - previous) / previous) * 100


def get_trend(values: list[float]) -> str:
    """
    Determine trend from values.

    >>> get_trend([1, 2, 3, 4, 5])
    'increasing'
    """
    if len(values) < 2:
        return "insufficient_data"

    increasing = 0
    decreasing = 0

    for i in range(1, len(values)):
        if values[i] > values[i-1]:
            increasing += 1
        elif values[i] < values[i-1]:
            decreasing += 1

    # BUG E-12: Equal counts returns "stable" even if highly volatile
    if increasing > decreasing:
        return "increasing"
    elif decreasing > increasing:
        return "decreasing"
    else:
        return "stable"


# F. SECURITY ISSUES

# BUG F-07: Hardcoded API key for report service
REPORT_API_KEY = "rpt_api_key_secret_789xyz"


def send_report(report: Report, recipient: str) -> bool:
    """Send report to recipient."""
    # BUG F-08: No validation of recipient (could be any URL/email)
    print(f"Sending report {report.id} to {recipient}")
    return True


# G. ERROR HANDLING ISSUES

def parse_report_data(data_string: str) -> dict | None:
    """Parse report data from string."""
    try:
        return json.loads(data_string)
    except json.JSONDecodeError as e:
        # BUG G-21: Error message includes raw input data
        print(f"Failed to parse data: {data_string[:100]}... Error: {e}")
        return None


class ReportBuilder:
    """Builds reports incrementally."""

    def __init__(self):
        self.data: dict[str, Any] = {}
        self.errors: list[str] = []

    def add_section(self, name: str, content: Any) -> "ReportBuilder":
        """Add a section to the report."""
        try:
            self.data[name] = content
        except Exception:
            # BUG G-22: Catches exception but doesn't record what went wrong
            self.errors.append(f"Failed to add section: {name}")
        return self

    def build(self) -> Report | None:
        """Build the final report."""
        if self.errors:
            # BUG G-23: Returns None but doesn't expose what errors occurred
            return None

        return Report(
            id=f"rpt_{datetime.now().timestamp()}",
            title=self.data.get("title", "Untitled"),
            data=self.data,
            created_at=datetime.now(),
        )


# D. ESCAPE HATCH ISSUES (in comments, representing @invar:allow)

# @invar:allow[complexity] - "Business requirement"
# BUG D-05: Vague justification for complex function
def complex_calculation(
    data: list[dict],
    weights: dict[str, float],
    thresholds: dict[str, float],
    normalize: bool = True,
    include_outliers: bool = False,
) -> dict[str, Any]:
    """Complex calculation with many parameters."""
    results = {}

    for item in data:
        for key, value in item.items():
            if key not in results:
                results[key] = []
            results[key].append(value * weights.get(key, 1.0))

    if normalize:
        for key in results:
            max_val = max(results[key]) if results[key] else 1
            results[key] = [v / max_val for v in results[key]]

    if not include_outliers:
        for key in results:
            values = results[key]
            if len(values) > 4:
                mean = sum(values) / len(values)
                std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
                results[key] = [v for v in values if abs(v - mean) <= 2 * std]

    final = {}
    for key, values in results.items():
        threshold = thresholds.get(key, 0)
        final[key] = {
            "values": values,
            "above_threshold": sum(1 for v in values if v > threshold),
            "below_threshold": sum(1 for v in values if v <= threshold),
        }

    return final


# @invar:allow[no-type-hints] - "Dynamic typing needed"
# BUG D-06: Actually, type hints would help here
def dynamic_transform(data, transformers):
    """Apply dynamic transformations."""
    result = data
    for t in transformers:
        result = t(result)
    return result
