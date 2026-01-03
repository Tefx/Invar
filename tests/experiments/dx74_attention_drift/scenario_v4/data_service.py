"""
Data service module.
Focus: Doctest Coverage (B), Code Quality (C)
"""
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class DataRecord:
    """Data record model."""
    id: str
    name: str
    value: float
    timestamp: datetime
    metadata: dict[str, Any]


# =============================================================================
# B. DOCTEST ISSUES - Missing or inadequate documentation
# =============================================================================

def parse_json_data(json_string: str) -> dict:
    """Parse JSON string to dictionary."""
    # BUG B-05: No doctest at all
    return json.loads(json_string)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency string."""
    # BUG B-06: No doctest, unclear behavior
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def calculate_percentage(part: float, total: float) -> float:
    """
    Calculate percentage.

    >>> calculate_percentage(25, 100)
    25.0
    """
    # BUG B-07: Only happy path tested, no edge cases (total=0, negative)
    if total == 0:
        return 0.0
    return (part / total) * 100


def merge_dicts(dict1: dict, dict2: dict) -> dict:
    """
    Merge two dictionaries.

    >>> merge_dicts({'a': 1}, {'b': 2})
    {'a': 1, 'b': 2}
    """
    # BUG B-08: No doctest for conflict case (same key in both)
    result = dict1.copy()
    result.update(dict2)
    return result


# =============================================================================
# C. CODE QUALITY ISSUES - Duplication, naming, complexity
# =============================================================================

class DataProcessor:
    """Processes data records."""

    def __init__(self):
        self.records: list[DataRecord] = []

    # BUG C-01: Code duplication - process_batch and process_single share logic
    def process_single(self, record: DataRecord) -> dict:
        """Process a single record."""
        result = {
            "id": record.id,
            "name": record.name.strip().lower(),
            "value": round(record.value, 2),
            "timestamp": record.timestamp.isoformat(),
            "metadata": record.metadata.copy(),
        }

        if result["value"] < 0:
            result["status"] = "negative"
        elif result["value"] == 0:
            result["status"] = "zero"
        else:
            result["status"] = "positive"

        return result

    # BUG C-02: Nearly identical to process_single
    def process_batch(self, records: list[DataRecord]) -> list[dict]:
        """Process multiple records."""
        results = []
        for record in records:
            result = {
                "id": record.id,
                "name": record.name.strip().lower(),
                "value": round(record.value, 2),
                "timestamp": record.timestamp.isoformat(),
                "metadata": record.metadata.copy(),
            }

            if result["value"] < 0:
                result["status"] = "negative"
            elif result["value"] == 0:
                result["status"] = "zero"
            else:
                result["status"] = "positive"

            results.append(result)
        return results


class DataValidator:
    """Validates data records."""

    # BUG C-03: Poor naming - 'v', 'd', 'r' are unclear
    def v(self, d: dict) -> bool:
        """Validate data."""
        if not d:
            return False
        if "id" not in d:
            return False
        if "value" not in d:
            return False
        return True

    def r(self, d: dict) -> dict:
        """Process record."""
        return {"valid": self.v(d), "data": d}


class DataTransformer:
    """Transforms data records."""

    # BUG C-04: Overly complex method - should be broken down
    def transform_complex(
        self,
        data: list[dict],
        filters: list[str] = None,
        transformations: list[str] = None,
        aggregations: list[str] = None,
        sort_by: str = None,
        sort_order: str = "asc",
        limit: int = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Apply complex transformations to data."""
        result = data.copy()

        # Apply filters
        if filters:
            for f in filters:
                if f == "positive":
                    result = [r for r in result if r.get("value", 0) > 0]
                elif f == "negative":
                    result = [r for r in result if r.get("value", 0) < 0]
                elif f == "non_null":
                    result = [r for r in result if r.get("value") is not None]

        # Apply transformations
        if transformations:
            for t in transformations:
                if t == "uppercase":
                    for r in result:
                        if "name" in r:
                            r["name"] = r["name"].upper()
                elif t == "round":
                    for r in result:
                        if "value" in r:
                            r["value"] = round(r["value"], 2)
                elif t == "add_timestamp":
                    for r in result:
                        r["processed_at"] = datetime.now().isoformat()

        # Apply aggregations
        agg_results = {}
        if aggregations:
            values = [r.get("value", 0) for r in result]
            for a in aggregations:
                if a == "sum":
                    agg_results["sum"] = sum(values)
                elif a == "avg":
                    agg_results["avg"] = sum(values) / len(values) if values else 0
                elif a == "count":
                    agg_results["count"] = len(result)
                elif a == "min":
                    agg_results["min"] = min(values) if values else None
                elif a == "max":
                    agg_results["max"] = max(values) if values else None

        # Apply sorting
        if sort_by:
            reverse = sort_order == "desc"
            result = sorted(result, key=lambda x: x.get(sort_by, 0), reverse=reverse)

        # Apply pagination
        if offset:
            result = result[offset:]
        if limit:
            result = result[:limit]

        return {
            "data": result,
            "aggregations": agg_results,
            "total": len(data),
            "filtered": len(result),
        }


# =============================================================================
# MORE CODE QUALITY ISSUES
# =============================================================================

# BUG C-05: Magic numbers without constants
def calculate_score(value: float) -> str:
    """Calculate score category."""
    if value >= 90:
        return "A"
    elif value >= 80:
        return "B"
    elif value >= 70:
        return "C"
    elif value >= 60:
        return "D"
    else:
        return "F"


# BUG C-06: Inconsistent naming style (mixed camelCase and snake_case)
def processData(inputData: dict) -> dict:
    """Process input data."""
    outputData = {}
    for key, val in inputData.items():
        processed_value = val * 2 if isinstance(val, (int, float)) else val
        outputData[key] = processed_value
    return outputData


# =============================================================================
# ADDITIONAL DOCTEST ISSUES
# =============================================================================

def filter_records(records: list[dict], field: str, value: Any) -> list[dict]:
    """
    Filter records by field value.

    >>> filter_records([{'a': 1}, {'a': 2}], 'a', 1)
    [{'a': 1}]
    """
    # BUG B-09: No doctest for missing field, empty list, None value
    return [r for r in records if r.get(field) == value]


def group_by(records: list[dict], key: str) -> dict[Any, list[dict]]:
    """Group records by key."""
    # BUG B-10: No doctest at all
    result: dict[Any, list[dict]] = {}
    for record in records:
        group_key = record.get(key)
        if group_key not in result:
            result[group_key] = []
        result[group_key].append(record)
    return result


def flatten_dict(d: dict, prefix: str = "") -> dict[str, Any]:
    """
    Flatten nested dictionary.

    >>> flatten_dict({'a': {'b': 1}})
    {'a.b': 1}
    """
    # BUG B-11: No doctest for list values, empty dict, deep nesting
    result = {}
    for key, value in d.items():
        new_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten_dict(value, new_key))
        else:
            result[new_key] = value
    return result


def safe_get(d: dict, path: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary value.

    >>> safe_get({'a': {'b': 1}}, 'a.b')
    1
    """
    # BUG B-12: Only tests happy path
    keys = path.split(".")
    current = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is default:
            return default
    return current
