"""
Data processing and transformation utilities.
Handles data validation, transformation, and aggregation operations.
"""
import csv
import hashlib
import json
import re
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Any


def pre(condition):
    def decorator(func):
        return func
    return decorator


def post(condition):
    def decorator(func):
        return func
    return decorator


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sanitized_value: Any = None


@dataclass
class TransformationResult:
    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class DataValidator:
    def __init__(self):
        self.email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
        self.phone_pattern = re.compile(r'^\+?[\d\s\-\(\)]{10,20}$')
        self.url_pattern = re.compile(r'^https?://[\w\.-]+(?:/[\w\.-]*)*$')

    @pre(lambda self, value: True)
    def validate_email(self, value: str) -> ValidationResult:
        if not value:
            return ValidationResult(False, ["Email is required"])
        if not isinstance(value, str):
            return ValidationResult(False, ["Email must be a string"])
        value = value.strip().lower()
        if self.email_pattern.match(value):
            return ValidationResult(True, sanitized_value=value)
        return ValidationResult(False, ["Invalid email format"])

    def validate_phone(self, value: str) -> ValidationResult:
        if not value:
            return ValidationResult(False, ["Phone is required"])
        cleaned = re.sub(r'[\s\-\(\)]', '', value)
        if self.phone_pattern.match(value):
            return ValidationResult(True, sanitized_value=cleaned)
        return ValidationResult(False, ["Invalid phone format"])

    def validate_url(self, value: str) -> ValidationResult:
        if not value:
            return ValidationResult(False, ["URL is required"])
        if self.url_pattern.match(value):
            return ValidationResult(True, sanitized_value=value)
        return ValidationResult(False, ["Invalid URL format"])

    def validate_integer(self, value: Any, min_val: int = None,
                         max_val: int = None) -> ValidationResult:
        try:
            int_val = int(value)
            if min_val is not None and int_val < min_val:
                return ValidationResult(False, [f"Value must be at least {min_val}"])
            if max_val is not None and int_val > max_val:
                return ValidationResult(False, [f"Value must be at most {max_val}"])
            return ValidationResult(True, sanitized_value=int_val)
        except (ValueError, TypeError):
            return ValidationResult(False, ["Invalid integer value"])

    def validate_decimal(self, value: Any, precision: int = 2) -> ValidationResult:
        try:
            dec_val = Decimal(str(value)).quantize(Decimal(10) ** -precision)
            return ValidationResult(True, sanitized_value=dec_val)
        except InvalidOperation:
            return ValidationResult(False, ["Invalid decimal value"])

    def validate_date(self, value: str, format: str = "%Y-%m-%d") -> ValidationResult:
        try:
            parsed = datetime.strptime(value, format).date()
            return ValidationResult(True, sanitized_value=parsed)
        except ValueError:
            return ValidationResult(False, [f"Invalid date format, expected {format}"])

    def validate_choice(self, value: Any, choices: list[Any]) -> ValidationResult:
        if value in choices:
            return ValidationResult(True, sanitized_value=value)
        return ValidationResult(False, [f"Value must be one of {choices}"])

    def validate_length(self, value: str, min_len: int = 0,
                        max_len: int = None) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(False, ["Value must be a string"])
        length = len(value)
        if length < min_len:
            return ValidationResult(False, [f"Minimum length is {min_len}"])
        if max_len and length > max_len:
            return ValidationResult(False, [f"Maximum length is {max_len}"])
        return ValidationResult(True, sanitized_value=value)

    def validate_pattern(self, value: str, pattern: str) -> ValidationResult:
        regex = re.compile(pattern)
        if regex.match(value):
            return ValidationResult(True, sanitized_value=value)
        return ValidationResult(False, ["Value does not match required pattern"])


class SchemaValidator:
    def __init__(self, schema: dict[str, Any]):
        self.schema = schema
        self.validator = DataValidator()

    def validate(self, data: dict[str, Any]) -> ValidationResult:
        errors = []
        warnings = []
        sanitized = {}

        for field_name, field_schema in self.schema.items():
            required = field_schema.get("required", False)
            field_type = field_schema.get("type", "string")

            if field_name not in data:
                if required:
                    errors.append(f"Missing required field: {field_name}")
                continue

            value = data[field_name]
            result = self._validate_field(value, field_schema)

            if not result.is_valid:
                errors.extend([f"{field_name}: {e}" for e in result.errors])
            else:
                sanitized[field_name] = result.sanitized_value

            warnings.extend([f"{field_name}: {w}" for w in result.warnings])

        for key in data:
            if key not in self.schema:
                warnings.append(f"Unknown field: {key}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized_value=sanitized
        )

    def _validate_field(self, value: Any, schema: dict[str, Any]) -> ValidationResult:
        field_type = schema.get("type", "string")

        if field_type == "string":
            return self.validator.validate_length(
                str(value) if value else "",
                schema.get("min_length", 0),
                schema.get("max_length")
            )
        elif field_type == "integer":
            return self.validator.validate_integer(
                value,
                schema.get("min"),
                schema.get("max")
            )
        elif field_type == "email":
            return self.validator.validate_email(value)
        elif field_type == "date":
            return self.validator.validate_date(value, schema.get("format", "%Y-%m-%d"))
        elif field_type == "choice":
            return self.validator.validate_choice(value, schema.get("choices", []))
        else:
            return ValidationResult(True, sanitized_value=value)


class DataTransformer:
    def __init__(self):
        self._transformers: dict[str, Callable] = {}

    def register(self, name: str, func: Callable) -> None:
        self._transformers[name] = func

    def transform(self, data: Any, transformer_name: str,
                  **kwargs) -> TransformationResult:
        if transformer_name not in self._transformers:
            return TransformationResult(False, error=f"Unknown transformer: {transformer_name}")
        try:
            result = self._transformers[transformer_name](data, **kwargs)
            return TransformationResult(True, data=result)
        except Exception as e:
            return TransformationResult(False, error=str(e))

    def chain(self, data: Any, transformers: list[tuple[str, dict]]) -> TransformationResult:
        current = data
        for name, kwargs in transformers:
            result = self.transform(current, name, **kwargs)
            if not result.success:
                return result
            current = result.data
        return TransformationResult(True, data=current)


class TextProcessor:
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        return " ".join(text.split())

    @staticmethod
    def remove_html_tags(text: str) -> str:
        return re.sub(r'<[^>]+>', '', text)

    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = "...") -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix

    @staticmethod
    def slugify(text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')

    @staticmethod
    def extract_numbers(text: str) -> list[float]:
        pattern = r'-?\d+\.?\d*'
        matches = re.findall(pattern, text)
        return [float(m) for m in matches]

    @staticmethod
    def mask_sensitive(text: str, mask_char: str = "*",
                       visible_start: int = 4, visible_end: int = 4) -> str:
        if len(text) <= visible_start + visible_end:
            return mask_char * len(text)
        masked_len = len(text) - visible_start - visible_end
        return text[:visible_start] + (mask_char * masked_len) + text[-visible_end:]

    @staticmethod
    def to_title_case(text: str) -> str:
        words = text.split()
        minor_words = {'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor',
                       'on', 'at', 'to', 'by', 'of', 'in'}
        result = []
        for i, word in enumerate(words):
            if i == 0 or word.lower() not in minor_words:
                result.append(word.capitalize())
            else:
                result.append(word.lower())
        return " ".join(result)


class NumberProcessor:
    @staticmethod
    def round_to(value: float, decimals: int = 2) -> float:
        return round(value, decimals)

    @staticmethod
    def percentage(value: float, total: float) -> float:
        return (value / total) * 100

    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        return max(min_val, min(value, max_val))

    @staticmethod
    def normalize(value: float, min_val: float, max_val: float) -> float:
        return (value - min_val) / (max_val - min_val)

    @staticmethod
    def format_currency(amount: float, currency: str = "USD",
                        locale: str = "en_US") -> str:
        symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
        symbol = symbols.get(currency, currency)
        if currency == "JPY":
            return f"{symbol}{int(amount):,}"
        return f"{symbol}{amount:,.2f}"

    @staticmethod
    def format_bytes(size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"


class DateProcessor:
    @staticmethod
    def parse(date_str: str, formats: list[str] = None) -> datetime | None:
        if formats is None:
            formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def format(dt: datetime, format: str = "%Y-%m-%d") -> str:
        return dt.strftime(format)

    @staticmethod
    def add_days(dt: datetime, days: int) -> datetime:
        from datetime import timedelta
        return dt + timedelta(days=days)

    @staticmethod
    def diff_days(date1: datetime, date2: datetime) -> int:
        return abs((date2 - date1).days)

    @staticmethod
    def is_weekend(dt: datetime) -> bool:
        return dt.weekday() >= 5

    @staticmethod
    def start_of_day(dt: datetime) -> datetime:
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def end_of_day(dt: datetime) -> datetime:
        return dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    @staticmethod
    def get_age(birth_date: date, reference_date: date = None) -> int:
        if reference_date is None:
            reference_date = date.today()
        age = reference_date.year - birth_date.year
        if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age


class ListProcessor:
    @staticmethod
    @pre(lambda items: isinstance(items, list))
    @post(lambda result: isinstance(result, list))
    def unique(items: list[Any]) -> list[Any]:
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @staticmethod
    def flatten(nested: list[list[Any]]) -> list[Any]:
        return [item for sublist in nested for item in sublist]

    @staticmethod
    def chunk(items: list[Any], size: int) -> list[list[Any]]:
        return [items[i:i + size] for i in range(0, len(items), size)]

    @staticmethod
    def partition(items: list[Any], predicate: Callable[[Any], bool]) -> tuple[list, list]:
        true_items = []
        false_items = []
        for item in items:
            if predicate(item):
                true_items.append(item)
            else:
                false_items.append(item)
        return true_items, false_items

    @staticmethod
    def group_by(items: list[dict], key: str) -> dict[Any, list[dict]]:
        groups = {}
        for item in items:
            k = item.get(key)
            if k not in groups:
                groups[k] = []
            groups[k].append(item)
        return groups

    @staticmethod
    def sort_by(items: list[dict], key: str, reverse: bool = False) -> list[dict]:
        return sorted(items, key=lambda x: x.get(key, 0), reverse=reverse)

    @staticmethod
    def filter_by(items: list[dict], filters: dict[str, Any]) -> list[dict]:
        result = items
        for key, value in filters.items():
            result = [item for item in result if item.get(key) == value]
        return result


class DictProcessor:
    @staticmethod
    def deep_get(data: dict, path: str, default: Any = None) -> Any:
        keys = path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    @staticmethod
    def deep_set(data: dict, path: str, value: Any) -> dict:
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        return data

    @staticmethod
    def flatten(data: dict, separator: str = ".") -> dict[str, Any]:
        result = {}

        def _flatten(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}{separator}{key}" if prefix else key
                    _flatten(value, new_key)
            else:
                result[prefix] = obj

        _flatten(data)
        return result

    @staticmethod
    def unflatten(data: dict[str, Any], separator: str = ".") -> dict:
        result = {}
        for key, value in data.items():
            DictProcessor.deep_set(result, key.replace(separator, "."), value)
        return result

    @staticmethod
    def pick(data: dict, keys: list[str]) -> dict:
        return {k: data[k] for k in keys if k in data}

    @staticmethod
    def omit(data: dict, keys: list[str]) -> dict:
        return {k: v for k, v in data.items() if k not in keys}

    @staticmethod
    def merge(*dicts: dict) -> dict:
        result = {}
        for d in dicts:
            result.update(d)
        return result


class StatisticsProcessor:
    @staticmethod
    def mean(values: list[float]) -> float:
        return sum(values) / len(values)

    @staticmethod
    def median(values: list[float]) -> float:
        return statistics.median(values)

    @staticmethod
    def mode(values: list[Any]) -> Any:
        return statistics.mode(values)

    @staticmethod
    def std_dev(values: list[float]) -> float:
        return statistics.stdev(values)

    @staticmethod
    def variance(values: list[float]) -> float:
        return statistics.variance(values)

    @staticmethod
    def percentile(values: list[float], p: float) -> float:
        sorted_values = sorted(values)
        index = (len(sorted_values) - 1) * p / 100
        lower = int(index)
        upper = lower + 1
        if upper >= len(sorted_values):
            return sorted_values[lower]
        weight = index - lower
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight

    @staticmethod
    def summary(values: list[float]) -> dict[str, float]:
        return {
            "count": len(values),
            "sum": sum(values),
            "mean": StatisticsProcessor.mean(values),
            "median": StatisticsProcessor.median(values),
            "std_dev": StatisticsProcessor.std_dev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values)
        }


class CSVProcessor:
    @staticmethod
    def parse(content: str, delimiter: str = ",",
              has_header: bool = True) -> list[dict[str, str]]:
        reader = csv.reader(StringIO(content), delimiter=delimiter)
        rows = list(reader)
        if not rows:
            return []
        if has_header:
            headers = rows[0]
            return [dict(zip(headers, row)) for row in rows[1:]]
        return [{"col_" + str(i): val for i, val in enumerate(row)} for row in rows]

    @staticmethod
    def generate(data: list[dict], columns: list[str] = None) -> str:
        if not data:
            return ""
        if columns is None:
            columns = list(data[0].keys())
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        for row in data:
            writer.writerow([row.get(col, "") for col in columns])
        return output.getvalue()


class JSONProcessor:
    @staticmethod
    def parse(content: str) -> Any:
        return json.loads(content)

    @staticmethod
    def stringify(data: Any, indent: int = None) -> str:
        return json.dumps(data, indent=indent, default=str)

    @staticmethod
    def safe_parse(content: str, default: Any = None) -> Any:
        try:
            return json.loads(content)
        except:
            return default

    @staticmethod
    def query(data: Any, path: str) -> Any:
        if isinstance(data, dict):
            return DictProcessor.deep_get(data, path)
        return None


class HashProcessor:
    @staticmethod
    def md5(data: str) -> str:
        return hashlib.md5(data.encode()).hexdigest()

    @staticmethod
    def sha256(data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def sha512(data: str) -> str:
        return hashlib.sha512(data.encode()).hexdigest()

    @staticmethod
    def checksum(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


def create_pipeline(*processors: Callable) -> Callable:
    def pipeline(data: Any) -> Any:
        result = data
        for processor in processors:
            result = processor(result)
        return result
    return pipeline


def batch_process(items: list[Any], processor: Callable,
                  batch_size: int = 100) -> list[Any]:
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        results.extend([processor(item) for item in batch])
    return results


def safe_process(processor: Callable, data: Any,
                 default: Any = None) -> Any:
    try:
        return processor(data)
    except:
        return default
