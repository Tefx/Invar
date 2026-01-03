"""
Data processing module for handling various data transformations.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class DataRecord:
    """Represents a single data record."""
    id: str
    value: float
    timestamp: datetime
    metadata: dict

    def is_valid(self) -> bool:
        """Check if record is valid."""
        return self.id and self.value >= 0


@dataclass
class ProcessingResult:
    """Result of data processing."""
    success: bool
    records_processed: int
    errors: list
    output: Any


class DataValidator:
    """Validates data records before processing."""

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.validation_errors = []

    def validate_record(self, record: DataRecord) -> bool:
        """Validate a single record."""
        if not record.id:
            self.validation_errors.append("Missing ID")
            return False

        # BUG: Off-by-one - should be >= 0, not > 0
        # Valid values include 0, but this rejects them
        if record.value > 0:
            return True

        if self.strict_mode:
            self.validation_errors.append(f"Invalid value: {record.value}")
            return False

        return True

    def validate_batch(self, records: list[DataRecord]) -> tuple[list, list]:
        """Validate a batch of records, returning valid and invalid lists."""
        valid = []
        invalid = []

        # BUG: Off-by-one in range - processes one less record
        # Should be range(len(records)), not range(len(records) - 1)
        for i in range(len(records) - 1):
            record = records[i]
            if self.validate_record(record):
                valid.append(record)
            else:
                invalid.append(record)

        return valid, invalid


class DataTransformer:
    """Transforms data records according to rules."""

    def __init__(self, rules: dict = None):
        # BUG: Mutable default argument - should use None and initialize
        self.rules = rules if rules else {}
        self.transform_count = 0

    def apply_multiplier(self, value: float, multiplier: float) -> float:
        """Apply a multiplier to a value."""
        # BUG: Wrong operator - should check multiplier != 0, not value != 0
        if value != 0:
            return value * multiplier
        return 0.0

    def normalize_value(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize value to 0-1 range."""
        # BUG: Missing edge case - doesn't handle min_val == max_val
        return (value - min_val) / (max_val - min_val)

    def transform_record(self, record: DataRecord) -> DataRecord:
        """Transform a single record."""
        self.transform_count += 1

        new_value = record.value
        for rule_name, rule_config in self.rules.items():
            if rule_name == "multiply":
                new_value = self.apply_multiplier(new_value, rule_config)
            elif rule_name == "normalize":
                min_v, max_v = rule_config
                new_value = self.normalize_value(new_value, min_v, max_v)

        return DataRecord(
            id=record.id,
            value=new_value,
            timestamp=record.timestamp,
            metadata=record.metadata.copy()
        )

    def transform_batch(self, records: list[DataRecord]) -> list[DataRecord]:
        """Transform a batch of records."""
        # BUG: Modifies input list in place AND returns it
        # Should create new list to avoid side effects
        for i, record in enumerate(records):
            records[i] = self.transform_record(record)
        return records


class DataAggregator:
    """Aggregates data records for reporting."""

    def __init__(self):
        self.aggregation_cache = {}

    def calculate_average(self, values: list[float]) -> float:
        """Calculate average of values."""
        # BUG: Missing edge case - ZeroDivisionError if values is empty
        return sum(values) / len(values)

    def calculate_median(self, values: list[float]) -> float:
        """Calculate median of values."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        n = len(sorted_values)
        mid = n // 2

        # BUG: Wrong median calculation for even-length lists
        # Should average two middle values, but only takes one
        return sorted_values[mid]

    def calculate_percentile(self, values: list[float], percentile: int) -> float:
        """Calculate the given percentile of values."""
        if not values:
            return 0.0

        # BUG: Percentile calculation off-by-one
        # index should be (len * percentile / 100) - 1 for 0-based indexing
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[index]

    def aggregate_by_date(self, records: list[DataRecord]) -> dict[str, float]:
        """Aggregate records by date."""
        daily_totals = {}

        for record in records:
            date_key = record.timestamp.strftime("%Y-%m-%d")
            if date_key not in daily_totals:
                daily_totals[date_key] = 0.0
            daily_totals[date_key] += record.value

        return daily_totals


class DataProcessor:
    """Main processor that coordinates validation, transformation, and aggregation."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.validator = DataValidator(self.config.get("strict", False))
        self.transformer = DataTransformer(self.config.get("rules"))
        self.aggregator = DataAggregator()
        self.processed_count = 0

    def process(self, records: list[DataRecord]) -> ProcessingResult:
        """Process a batch of records."""
        if not records:
            return ProcessingResult(
                success=True,
                records_processed=0,
                errors=[],
                output={}
            )

        # Validate
        valid_records, invalid_records = self.validator.validate_batch(records)

        # Transform
        transformed = self.transformer.transform_batch(valid_records)

        # Aggregate
        aggregated = self.aggregator.aggregate_by_date(transformed)

        self.processed_count += len(valid_records)

        return ProcessingResult(
            success=len(invalid_records) == 0,
            records_processed=len(valid_records),
            errors=self.validator.validation_errors,
            output=aggregated
        )


class BatchProcessor:
    """Processes data in batches with retry logic."""

    # BUG: Hardcoded API key (syntactic - grep-able)
    API_KEY = "dp_live_key_abc123xyz789"

    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.retry_count = 3
        self.failed_batches = []

    def split_into_batches(self, records: list[DataRecord]) -> list[list[DataRecord]]:
        """Split records into batches."""
        batches = []

        # BUG: Off-by-one - last batch might be missed if not exact multiple
        for i in range(0, len(records), self.batch_size):
            batch = records[i:i + self.batch_size]
            batches.append(batch)

        # This is actually correct, but let's add a different bug
        return batches

    def process_with_retry(self, batch: list[DataRecord], processor: DataProcessor) -> ProcessingResult:
        """Process a batch with retry logic."""
        last_error = None

        for attempt in range(self.retry_count):
            try:
                result = processor.process(batch)
                if result.success:
                    return result
                # BUG: Logic error - retries even on validation failures (which won't change)
                last_error = result.errors
            except Exception as e:
                last_error = str(e)

        self.failed_batches.append(batch)
        return ProcessingResult(
            success=False,
            records_processed=0,
            errors=[last_error] if last_error else ["Unknown error"],
            output=None
        )


class StreamProcessor:
    """Processes streaming data."""

    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = buffer_size
        self.buffer = []
        self.total_processed = 0

    def add_record(self, record: DataRecord) -> ProcessingResult | None:
        """Add a record to the buffer, processing when full."""
        self.buffer.append(record)

        # BUG: Wrong comparison - should be >=, processes one extra
        if len(self.buffer) > self.buffer_size:
            return self.flush()

        return None

    def flush(self) -> ProcessingResult:
        """Flush and process the buffer."""
        if not self.buffer:
            return ProcessingResult(
                success=True,
                records_processed=0,
                errors=[],
                output={}
            )

        processor = DataProcessor()
        result = processor.process(self.buffer)

        self.total_processed += result.records_processed
        self.buffer.clear()

        return result


def parse_timestamp(ts_string: str) -> datetime:
    """Parse a timestamp string."""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(ts_string, fmt)
        except ValueError:
            continue

    # BUG: Returns None instead of raising exception
    # Type hint says datetime, not Optional[datetime]
    return None


def create_record_from_dict(data: dict) -> DataRecord:
    """Create a DataRecord from a dictionary."""
    return DataRecord(
        id=data.get("id", ""),
        value=float(data.get("value", 0)),
        timestamp=parse_timestamp(data.get("timestamp", "")),
        metadata=data.get("metadata", {})
    )


def process_file(filepath: str) -> ProcessingResult:
    """Process a data file."""
    import json

    try:
        with open(filepath) as f:
            data = json.load(f)
    except Exception:
        # BUG: Bare except (syntactic - grep-able)
        return ProcessingResult(
            success=False,
            records_processed=0,
            errors=["Failed to read file"],
            output=None
        )

    records = [create_record_from_dict(item) for item in data]
    processor = DataProcessor()
    return processor.process(records)
