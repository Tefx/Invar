"""
Report Engine module for generating and formatting reports.
Provides utilities for building, rendering, and exporting reports.
"""
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
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


class ReportFormat(Enum):
    """Supported report output formats."""
    HTML = "html"
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    PLAIN = "plain"


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    title: str
    author: str = "System"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    include_header: bool = True
    include_footer: bool = True
    page_size: int = 50


@dataclass
class ReportSection:
    """A section within a report."""
    title: str
    content: str
    order: int = 0
    visible: bool = True


@dataclass
class TableColumn:
    """Definition of a table column."""
    name: str
    key: str
    width: int = 0
    alignment: str = "left"
    formatter: Callable | None = None


class TextFormatter:
    """Utilities for text formatting in reports."""

    @staticmethod
    @pre(lambda text: isinstance(text, str))
    def truncate(text: str, max_length: int, suffix: str = "...") -> str:
        """
        Truncate text to maximum length.

        >>> TextFormatter.truncate("Hello World", 8)
        'Hello...'
        >>> TextFormatter.truncate("Hi", 10)
        'Hi'
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix

    @staticmethod
    @pre(lambda text: isinstance(text, str))
    @post(lambda result: isinstance(result, str))
    def pad_right(text: str, width: int, char: str = " ") -> str:
        """
        Pad text to the right.

        >>> TextFormatter.pad_right("hello", 10)
        'hello     '
        >>> TextFormatter.pad_right("hi", 5, "-")
        'hi---'
        """
        if len(text) >= width:
            return text
        return text + char * (width - len(text))

    @staticmethod
    @pre(lambda text: isinstance(text, str))
    def pad_left(text: str, width: int, char: str = " ") -> str:
        """
        Pad text to the left.

        >>> TextFormatter.pad_left("hello", 10)
        '     hello'
        >>> TextFormatter.pad_left("42", 5, "0")
        '00042'
        """
        if len(text) >= width:
            return text
        return char * (width - len(text)) + text

    @staticmethod
    def center(text: str, width: int, char: str = " ") -> str:
        """
        Center text within width.

        >>> TextFormatter.center("hi", 6)
        '  hi  '
        >>> TextFormatter.center("hello", 5)
        'hello'
        """
        if len(text) >= width:
            return text
        padding = width - len(text)
        left_pad = padding // 2
        right_pad = padding - left_pad
        return char * left_pad + text + char * right_pad

    @staticmethod
    def wrap_text(text: str, width: int) -> list[str]:
        """
        Wrap text to specified width.

        >>> TextFormatter.wrap_text("hello world", 6)
        ['hello', 'world']
        >>> TextFormatter.wrap_text("hi", 10)
        ['hi']
        """
        if len(text) <= width:
            return [text]

        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if not current_line:
                current_line = word
            elif len(current_line) + 1 + len(word) <= width:
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines


class NumberFormatter:
    """Utilities for number formatting in reports."""

    @staticmethod
    @pre(lambda value: isinstance(value, (int, float)))
    def format_number(value: int | float, decimals: int = 2) -> str:
        """
        Format number with thousand separators.

        >>> NumberFormatter.format_number(1234567.89)
        '1,234,567.89'
        >>> NumberFormatter.format_number(1000)
        '1,000.00'
        """
        return f"{value:,.{decimals}f}"

    @staticmethod
    @pre(lambda value: isinstance(value, (int, float)))
    def format_percent(value: float, decimals: int = 1) -> str:
        """
        Format value as percentage.

        >>> NumberFormatter.format_percent(0.756)
        '75.6%'
        >>> NumberFormatter.format_percent(1.0)
        '100.0%'
        """
        return f"{value * 100:.{decimals}f}%"

    @staticmethod
    @pre(lambda bytes_value: isinstance(bytes_value, (int, float)))
    def format_bytes(bytes_value: int) -> str:
        """
        Format bytes to human readable string.

        >>> NumberFormatter.format_bytes(1024)
        '1.00 KB'
        >>> NumberFormatter.format_bytes(1048576)
        '1.00 MB'
        >>> NumberFormatter.format_bytes(500)
        '500.00 B'
        """
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(bytes_value)

        for unit in units[:-1]:
            if abs(value) < 1024:
                return f"{value:.2f} {unit}"
            value /= 1024

        return f"{value:.2f} {units[-1]}"

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format duration in human readable form.

        >>> NumberFormatter.format_duration(3661)
        '1h 1m 1s'
        >>> NumberFormatter.format_duration(45)
        '45s'
        >>> NumberFormatter.format_duration(125)
        '2m 5s'
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours}h {minutes}m {secs}s"


class DateFormatter:
    """Utilities for date formatting in reports."""

    DEFAULT_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    @classmethod
    @pre(lambda cls, dt: isinstance(dt, datetime))
    def format_date(cls, dt: datetime, fmt: str | None = None) -> str:
        """
        Format datetime object to string.

        >>> from datetime import datetime
        >>> DateFormatter.format_date(datetime(2024, 1, 15))
        '2024-01-15'
        """
        return dt.strftime(fmt or cls.DEFAULT_FORMAT)

    @classmethod
    def format_relative(cls, dt: datetime) -> str:
        """
        Format datetime as relative time.

        >>> from datetime import datetime, timedelta
        >>> now = datetime.now()
        >>> DateFormatter.format_relative(now - timedelta(minutes=5))
        '5 minutes ago'
        """
        now = datetime.now()
        diff = now - dt

        if diff.days > 365:
            years = diff.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "just now"

    @classmethod
    def format_range(cls, start: datetime, end: datetime) -> str:
        """
        Format date range.

        >>> from datetime import datetime
        >>> DateFormatter.format_range(datetime(2024, 1, 1), datetime(2024, 1, 31))
        '2024-01-01 to 2024-01-31'
        """
        return f"{cls.format_date(start)} to {cls.format_date(end)}"


class HTMLBuilder:
    """Builder for HTML report content."""

    def __init__(self):
        self.content: list[str] = []

    @pre(lambda self, level: 1 <= level <= 6)
    def add_heading(self, text: str, level: int = 1) -> "HTMLBuilder":
        """
        Add heading element.

        >>> builder = HTMLBuilder()
        >>> builder.add_heading("Title", 1).content
        ['<h1>Title</h1>']
        """
        self.content.append(f"<h{level}>{text}</h{level}>")
        return self

    @pre(lambda self, text: isinstance(text, str))
    def add_paragraph(self, text: str) -> "HTMLBuilder":
        """
        Add paragraph element.

        >>> builder = HTMLBuilder()
        >>> builder.add_paragraph("Hello").content
        ['<p>Hello</p>']
        """
        self.content.append(f"<p>{text}</p>")
        return self

    def add_list(self, items: list[str], ordered: bool = False) -> "HTMLBuilder":
        """
        Add list element.

        >>> builder = HTMLBuilder()
        >>> builder.add_list(["a", "b"]).content
        ['<ul><li>a</li><li>b</li></ul>']
        """
        tag = "ol" if ordered else "ul"
        items_html = "".join(f"<li>{item}</li>" for item in items)
        self.content.append(f"<{tag}>{items_html}</{tag}>")
        return self

    def add_table(self, headers: list[str], rows: list[list[str]]) -> "HTMLBuilder":
        """
        Add table element.

        >>> builder = HTMLBuilder()
        >>> builder.add_table(["A", "B"], [["1", "2"]]).content[0]
        '<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></table>'
        """
        header_html = "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
        rows_html = ""
        for row in rows:
            rows_html += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        self.content.append(f"<table><thead>{header_html}</thead><tbody>{rows_html}</tbody></table>")
        return self

    def add_raw(self, html_content: str) -> "HTMLBuilder":
        """
        Add raw HTML content.

        >>> builder = HTMLBuilder()
        >>> builder.add_raw("<div>custom</div>").content
        ['<div>custom</div>']
        """
        self.content.append(html_content)
        return self

    def add_image(self, src: str, alt: str = "") -> "HTMLBuilder":
        """
        Add image element.

        >>> builder = HTMLBuilder()
        >>> builder.add_image("photo.jpg", "Photo").content
        ['<img src="photo.jpg" alt="Photo">']
        """
        self.content.append(f'<img src="{src}" alt="{alt}">')
        return self

    def build(self) -> str:
        """
        Build final HTML string.

        >>> builder = HTMLBuilder()
        >>> builder.add_heading("Title").add_paragraph("Text").build()
        '<h1>Title</h1><p>Text</p>'
        """
        return "".join(self.content)


class MarkdownBuilder:
    """Builder for Markdown report content."""

    def __init__(self):
        self.lines: list[str] = []

    @pre(lambda self, level: 1 <= level <= 6)
    def add_heading(self, text: str, level: int = 1) -> "MarkdownBuilder":
        """
        Add heading.

        >>> builder = MarkdownBuilder()
        >>> builder.add_heading("Title", 2).lines
        ['## Title', '']
        """
        self.lines.append("#" * level + " " + text)
        self.lines.append("")
        return self

    @pre(lambda self, text: isinstance(text, str))
    def add_paragraph(self, text: str) -> "MarkdownBuilder":
        """
        Add paragraph.

        >>> builder = MarkdownBuilder()
        >>> builder.add_paragraph("Hello world").lines
        ['Hello world', '']
        """
        self.lines.append(text)
        self.lines.append("")
        return self

    def add_list(self, items: list[str], ordered: bool = False) -> "MarkdownBuilder":
        """
        Add list.

        >>> builder = MarkdownBuilder()
        >>> builder.add_list(["a", "b"]).lines
        ['- a', '- b', '']
        """
        for i, item in enumerate(items):
            prefix = f"{i + 1}." if ordered else "-"
            self.lines.append(f"{prefix} {item}")
        self.lines.append("")
        return self

    def add_code_block(self, code: str, language: str = "") -> "MarkdownBuilder":
        """
        Add code block.

        >>> builder = MarkdownBuilder()
        >>> builder.add_code_block("print('hi')", "python").lines
        ['```python', "print('hi')", '```', '']
        """
        self.lines.append(f"```{language}")
        self.lines.append(code)
        self.lines.append("```")
        self.lines.append("")
        return self

    def add_table(self, headers: list[str], rows: list[list[str]]) -> "MarkdownBuilder":
        """
        Add table.

        >>> builder = MarkdownBuilder()
        >>> builder.add_table(["A", "B"], [["1", "2"]]).lines[0]
        '| A | B |'
        """
        header_line = "| " + " | ".join(headers) + " |"
        separator = "| " + " | ".join(["---"] * len(headers)) + " |"
        self.lines.append(header_line)
        self.lines.append(separator)
        for row in rows:
            self.lines.append("| " + " | ".join(row) + " |")
        self.lines.append("")
        return self

    def build(self) -> str:
        """
        Build final Markdown string.

        >>> builder = MarkdownBuilder()
        >>> builder.add_heading("Title").build()
        '# Title\\n'
        """
        return "\n".join(self.lines)


class CSVBuilder:
    """Builder for CSV report content."""

    def __init__(self, delimiter: str = ","):
        self.delimiter = delimiter
        self.rows: list[list[str]] = []

    def add_row(self, values: list[Any]) -> "CSVBuilder":
        """
        Add a row of values.

        >>> builder = CSVBuilder()
        >>> builder.add_row(["a", "b", "c"]).rows
        [['a', 'b', 'c']]
        """
        self.rows.append([str(v) for v in values])
        return self

    def add_header(self, headers: list[str]) -> "CSVBuilder":
        """
        Add header row.

        >>> builder = CSVBuilder()
        >>> builder.add_header(["Col1", "Col2"]).rows
        [['Col1', 'Col2']]
        """
        self.rows.insert(0, headers)
        return self

    @pre(lambda self, value: isinstance(value, str))
    def _escape_value(self, value: str) -> str:
        """Escape CSV value if needed."""
        if self.delimiter in value or '"' in value or '\n' in value:
            return '"' + value.replace('"', '""') + '"'
        return value

    def build(self) -> str:
        """
        Build final CSV string.

        >>> builder = CSVBuilder()
        >>> builder.add_row(["a", "b"]).add_row(["c", "d"]).build()
        'a,b\\nc,d'
        """
        lines = []
        for row in self.rows:
            escaped = [self._escape_value(v) for v in row]
            lines.append(self.delimiter.join(escaped))
        return "\n".join(lines)


class TemplateEngine:
    """Simple template engine for report generation."""

    VARIABLE_PATTERN = re.compile(r'\{\{\s*(\w+)\s*\}\}')

    def __init__(self, template: str):
        self.template = template

    @pre(lambda self, context: isinstance(context, dict))
    def render(self, context: dict[str, Any]) -> str:
        """
        Render template with context.

        >>> engine = TemplateEngine("Hello {{ name }}!")
        >>> engine.render({"name": "World"})
        'Hello World!'
        """
        result = self.template

        def replace(match):
            key = match.group(1)
            return str(context.get(key, match.group(0)))

        return self.VARIABLE_PATTERN.sub(replace, result)

    def render_html(self, context: dict[str, Any]) -> str:
        """
        Render template with HTML-escaped context.

        >>> engine = TemplateEngine("Value: {{ data }}")
        >>> engine.render_html({"data": "<script>alert(1)</script>"})
        'Value: <script>alert(1)</script>'
        """
        result = self.template

        def replace(match):
            key = match.group(1)
            value = context.get(key, match.group(0))
            return str(value)

        return self.VARIABLE_PATTERN.sub(replace, result)


class ReportAggregator:
    """Aggregation utilities for report data."""

    @staticmethod
    @pre(lambda values: isinstance(values, list))
    def sum(values: list[int | float]) -> float:
        """
        Calculate sum of values.

        >>> ReportAggregator.sum([1, 2, 3, 4, 5])
        15
        """
        return sum(values)

    @staticmethod
    @pre(lambda values: isinstance(values, list))
    def average(values: list[int | float]) -> float:
        """
        Calculate average of values.

        >>> ReportAggregator.average([1, 2, 3, 4, 5])
        3.0
        """
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def minimum(values: list[int | float]) -> float | None:
        """
        Find minimum value.

        >>> ReportAggregator.minimum([3, 1, 4, 1, 5])
        1
        >>> ReportAggregator.minimum([])
        """
        return min(values) if values else None

    @staticmethod
    def maximum(values: list[int | float]) -> float | None:
        """
        Find maximum value.

        >>> ReportAggregator.maximum([3, 1, 4, 1, 5])
        5
        >>> ReportAggregator.maximum([])
        """
        return max(values) if values else None

    @staticmethod
    @pre(lambda values: isinstance(values, list))
    def count(values: list[Any]) -> int:
        """
        Count non-None values.

        >>> ReportAggregator.count([1, None, 3, None, 5])
        3
        """
        return sum(1 for v in values if v is not None)

    @staticmethod
    def group_by(items: list[dict], key: str) -> dict[str, list[dict]]:
        """
        Group items by key value.

        >>> items = [{"type": "a", "val": 1}, {"type": "b", "val": 2}, {"type": "a", "val": 3}]
        >>> grouped = ReportAggregator.group_by(items, "type")
        >>> len(grouped["a"])
        2
        """
        groups: dict[str, list[dict]] = {}
        for item in items:
            group_key = str(item.get(key, ""))
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(item)
        return groups


class ReportGenerator:
    """Main report generation engine."""

    def __init__(self, config: ReportConfig):
        self.config = config
        self.sections: list[ReportSection] = []
        self.data: dict[str, Any] = {}

    @pre(lambda self, section: isinstance(section, ReportSection))
    def add_section(self, section: ReportSection) -> "ReportGenerator":
        """
        Add section to report.

        >>> config = ReportConfig(title="Test")
        >>> gen = ReportGenerator(config)
        >>> section = ReportSection(title="Intro", content="Hello")
        >>> gen.add_section(section).sections[0].title
        'Intro'
        """
        self.sections.append(section)
        self.sections.sort(key=lambda s: s.order)
        return self

    @pre(lambda self, key, value: isinstance(key, str))
    def set_data(self, key: str, value: Any) -> "ReportGenerator":
        """
        Set report data value.

        >>> config = ReportConfig(title="Test")
        >>> gen = ReportGenerator(config)
        >>> gen.set_data("count", 42).data["count"]
        42
        """
        self.data[key] = value
        return self

    def generate(self, format: ReportFormat = ReportFormat.HTML) -> str:
        """
        Generate report in specified format.

        >>> config = ReportConfig(title="Test Report")
        >>> gen = ReportGenerator(config)
        >>> gen.add_section(ReportSection("Intro", "Content"))
        <...>
        >>> "Test Report" in gen.generate(ReportFormat.HTML)
        True
        """
        if format == ReportFormat.HTML:
            return self._generate_html()
        elif format == ReportFormat.MARKDOWN:
            return self._generate_markdown()
        elif format == ReportFormat.JSON:
            return self._generate_json()
        elif format == ReportFormat.CSV:
            return self._generate_csv()
        else:
            return self._generate_plain()

    def _generate_html(self) -> str:
        """Generate HTML report."""
        builder = HTMLBuilder()

        if self.config.include_header:
            builder.add_heading(self.config.title, 1)
            builder.add_paragraph(f"Author: {self.config.author}")
            builder.add_paragraph(f"Generated: {datetime.now().strftime(self.config.date_format)}")

        for section in self.sections:
            if section.visible:
                builder.add_heading(section.title, 2)
                builder.add_raw(section.content)

        if self.config.include_footer:
            builder.add_raw("<hr>")
            builder.add_paragraph("End of Report")

        return builder.build()

    def _generate_markdown(self) -> str:
        """Generate Markdown report."""
        builder = MarkdownBuilder()

        if self.config.include_header:
            builder.add_heading(self.config.title, 1)
            builder.add_paragraph(f"**Author:** {self.config.author}")
            builder.add_paragraph(f"**Generated:** {datetime.now().strftime(self.config.date_format)}")

        for section in self.sections:
            if section.visible:
                builder.add_heading(section.title, 2)
                builder.add_paragraph(section.content)

        return builder.build()

    def _generate_json(self) -> str:
        """Generate JSON report."""
        report_data = {
            "title": self.config.title,
            "author": self.config.author,
            "generated_at": datetime.now().isoformat(),
            "sections": [
                {"title": s.title, "content": s.content}
                for s in self.sections if s.visible
            ],
            "data": self.data
        }
        return json.dumps(report_data, indent=2, default=str)

    def _generate_csv(self) -> str:
        """Generate CSV report (sections only)."""
        builder = CSVBuilder()
        builder.add_header(["Section", "Content"])
        for section in self.sections:
            if section.visible:
                builder.add_row([section.title, section.content])
        return builder.build()

    def _generate_plain(self) -> str:
        """Generate plain text report."""
        lines = []

        if self.config.include_header:
            lines.append("=" * 60)
            lines.append(self.config.title.center(60))
            lines.append("=" * 60)
            lines.append(f"Author: {self.config.author}")
            lines.append(f"Generated: {datetime.now().strftime(self.config.date_format)}")
            lines.append("")

        for section in self.sections:
            if section.visible:
                lines.append("-" * 40)
                lines.append(section.title)
                lines.append("-" * 40)
                lines.append(section.content)
                lines.append("")

        return "\n".join(lines)


class ChartDataBuilder:
    """Builder for chart data structures."""

    def __init__(self):
        self.labels: list[str] = []
        self.datasets: list[dict[str, Any]] = []

    def set_labels(self, labels: list[str]) -> "ChartDataBuilder":
        """
        Set chart labels.

        >>> builder = ChartDataBuilder()
        >>> builder.set_labels(["Jan", "Feb", "Mar"]).labels
        ['Jan', 'Feb', 'Mar']
        """
        self.labels = labels
        return self

    @pre(lambda self, name, data: isinstance(name, str))
    def add_dataset(self, name: str, data: list[float], color: str = "#000") -> "ChartDataBuilder":
        """
        Add dataset to chart.

        >>> builder = ChartDataBuilder()
        >>> builder.add_dataset("Sales", [100, 200, 300]).datasets[0]["label"]
        'Sales'
        """
        self.datasets.append({
            "label": name,
            "data": data,
            "backgroundColor": color
        })
        return self

    def build(self) -> dict[str, Any]:
        """
        Build chart data structure.

        >>> builder = ChartDataBuilder()
        >>> builder.set_labels(["A"]).add_dataset("X", [1]).build()
        {'labels': ['A'], 'datasets': [{'label': 'X', 'data': [1], 'backgroundColor': '#000'}]}
        """
        return {
            "labels": self.labels,
            "datasets": self.datasets
        }


class ReportScheduler:
    """Scheduler for automated report generation."""

    def __init__(self):
        self.schedules: list[dict[str, Any]] = []

    @pre(lambda self, name, interval: isinstance(name, str))
    def add_schedule(
        self,
        name: str,
        interval: timedelta,
        generator: Callable[[], str]
    ) -> "ReportScheduler":
        """
        Add scheduled report.

        >>> scheduler = ReportScheduler()
        >>> scheduler.add_schedule("daily", timedelta(days=1), lambda: "report").schedules[0]["name"]
        'daily'
        """
        self.schedules.append({
            "name": name,
            "interval": interval,
            "generator": generator,
            "last_run": None,
            "next_run": datetime.now()
        })
        return self

    def get_due_reports(self) -> list[str]:
        """
        Get names of reports due for generation.

        >>> scheduler = ReportScheduler()
        >>> scheduler.add_schedule("test", timedelta(seconds=0), lambda: "")
        <...>
        >>> "test" in scheduler.get_due_reports()
        True
        """
        now = datetime.now()
        due = []
        for schedule in self.schedules:
            if schedule["next_run"] <= now:
                due.append(schedule["name"])
        return due

    def run_schedule(self, name: str) -> str | None:
        """
        Run a specific scheduled report.

        >>> scheduler = ReportScheduler()
        >>> scheduler.add_schedule("test", timedelta(days=1), lambda: "result")
        <...>
        >>> scheduler.run_schedule("test")
        'result'
        """
        for schedule in self.schedules:
            if schedule["name"] == name:
                result = schedule["generator"]()
                schedule["last_run"] = datetime.now()
                schedule["next_run"] = datetime.now() + schedule["interval"]
                return result
        return None
