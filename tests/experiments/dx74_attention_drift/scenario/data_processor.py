"""Data processing module with planted exception handling bugs.

DX-74 Test Scenario - File 2/6
Bugs: 9 exception handling issues
"""

import json


def parse_json_data(data: str) -> dict:
    """Parse JSON data from a string."""
    try:
        return json.loads(data)
    # BUG-09: Bare except catches everything including KeyboardInterrupt
    except Exception:
        return {}


def process_records(records: list[dict]) -> list[dict]:
    """Process a list of records."""
    results = []
    for record in records:
        try:
            processed = transform_record(record)
            results.append(processed)
        # BUG-10: Bare except silently swallows errors
        except Exception:
            pass  # Silent failure
    return results


def transform_record(record: dict) -> dict:
    """Transform a single record."""
    return {"id": record.get("id"), "value": record.get("value", 0) * 2}


def read_data_file(filepath: str) -> str:
    """Read data from a file."""
    try:
        with open(filepath) as f:
            return f.read()
    # BUG-11: Bare except hides file errors
    except Exception:
        return ""


def write_data_file(filepath: str, data: str) -> bool:
    """Write data to a file."""
    try:
        with open(filepath, "w") as f:
            f.write(data)
        return True
    # BUG-12: Bare except with generic error handling
    except Exception as e:
        print(f"Error: {e}")
        return False


def validate_record(record: dict) -> bool:
    """Validate a record structure."""
    try:
        required = ["id", "name", "value"]
        return all(k in record for k in required)
    # BUG-13: Bare except for validation
    except Exception:
        return False


def merge_datasets(ds1: list, ds2: list) -> list:
    """Merge two datasets."""
    try:
        return ds1 + ds2
    # BUG-14: Overly broad exception handling
    except Exception:
        return []


def filter_records(records: list, predicate: callable) -> list:
    """Filter records by a predicate function."""
    results = []
    for r in records:
        try:
            if predicate(r):
                results.append(r)
        # BUG-15: Bare except in filter loop
        except Exception:
            continue
    return results


def aggregate_values(records: list, key: str) -> float:
    """Aggregate values from records."""
    total = 0.0
    for record in records:
        try:
            total += float(record.get(key, 0))
        # BUG-16: Bare except for type conversion
        except Exception:
            pass
    return total


def batch_process(items: list, batch_size: int = 10) -> list:
    """Process items in batches."""
    results = []
    try:
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            results.extend(process_batch(batch))
    # BUG-17: Bare except for batch processing
    except Exception:
        pass
    return results


def process_batch(batch: list) -> list:
    """Process a single batch."""
    return [{"processed": item} for item in batch]
