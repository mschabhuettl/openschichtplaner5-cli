# src/openschichtplaner5_cli/visualization.py
"""
Data visualization capabilities for Schichtplaner5 CLI.
Creates charts, graphs, and visual reports.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from collections import defaultdict, Counter
import calendar

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.progress import BarColumn, Progress

console = Console()


class AsciiChart:
    """Create ASCII charts for terminal display."""

    @staticmethod
    def bar_chart(data: Dict[str, float], width: int = 50,
                  title: str = "Bar Chart", show_values: bool = True) -> str:
        """Create a horizontal bar chart."""
        if not data:
            return "No data to display"

        # Find max value for scaling
        max_value = max(data.values()) if data.values() else 1
        max_label_len = max(len(str(label)) for label in data.keys())

        lines = [f"\n{title}\n" + "=" * (width + max_label_len + 10)]

        for label, value in data.items():
            # Calculate bar width
            bar_width = int((value / max_value) * width) if max_value > 0 else 0
            bar = "█" * bar_width

            # Format line
            label_str = f"{label:>{max_label_len}}"
            value_str = f"{value:,.0f}" if show_values else ""

            lines.append(f"{label_str} │ {bar} {value_str}")

        return "\n".join(lines)

    @staticmethod
    def line_chart(data: List[Tuple[str, float]], width: int = 60,
                   height: int = 20, title: str = "Line Chart") -> str:
        """Create a line chart."""
        if not data:
            return "No data to display"

        # Extract values
        labels = [d[0] for d in data]
        values = [d[1] for d in data]

        if not values:
            return "No values to display"

        # Find range
        min_val = min(values)
        max_val = max(values)
        value_range = max_val - min_val if max_val != min_val else 1

        # Create grid
        grid = [[" " for _ in range(width)] for _ in range(height)]

        # Plot points
        for i, value in enumerate(values):
            x = int((i / (len(values) - 1)) * (width - 1)) if len(values) > 1 else width // 2
            y = height - 1 - int(((value - min_val) / value_range) * (height - 1))

            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = "●"

                # Connect with previous point
                if i > 0:
                    prev_x = int(((i - 1) / (len(values) - 1)) * (width - 1)) if len(values) > 1 else width // 2
                    prev_y = height - 1 - int(((values[i - 1] - min_val) / value_range) * (height - 1))

                    # Simple line drawing
                    steps = max(abs(x - prev_x), abs(y - prev_y))
                    for step in range(1, steps):
                        inter_x = int(prev_x + (x - prev_x) * step / steps)
                        inter_y = int(prev_y + (y - prev_y) * step / steps)
                        if 0 <= inter_x < width and 0 <= inter_y < height:
                            if grid[inter_y][inter_x] == " ":
                                grid[inter_y][inter_x] = "·"

        # Create output
        lines = [f"\n{title}", "=" * width]

        # Add Y-axis labels
        for i, row in enumerate(grid):
            y_value = max_val - (i / (height - 1)) * value_range if height > 1 else max_val
            y_label = f"{y_value:>8.1f} │"
            lines.append(y_label + "".join(row))

        # Add X-axis
        lines.append(" " * 10 + "└" + "─" * width)

        # Add X-axis labels (sample)
        if len(labels) > 0:
            label_line = " " * 11
            sample_indices = [0, len(labels) // 2, len(labels) - 1]
            for idx in sample_indices:
                if idx < len(labels):
                    pos = int((idx / (len(labels) - 1)) * (width - 1)) if len(labels) > 1 else width // 2
                    label_line += f"{labels[idx]:^10}"
            lines.append(label_line)

        return "\n".join(lines)

    @staticmethod
    def heatmap(data: Dict[str, Dict[str, float]],
                title: str = "Heatmap") -> Table:
        """Create a heatmap table."""
        if not data:
            return Table(title="No data")

        # Get all row and column keys
        row_keys = sorted(data.keys())
        col_keys = sorted(set(key for row in data.values() for key in row.keys()))

        # Find value range for coloring
        all_values = [v for row in data.values() for v in row.values()]
        min_val = min(all_values) if all_values else 0
        max_val = max(all_values) if all_values else 1
        value_range = max_val - min_val if max_val != min_val else 1

        # Create table
        table = Table(title=title, box=box.ROUNDED)
        table.add_column("", style="bold")

        for col in col_keys:
            table.add_column(str(col), justify="center")

        # Add rows
        for row_key in row_keys:
            row_data = [str(row_key)]

            for col_key in col_keys:
                value = data.get(row_key, {}).get(col_key, 0)

                # Color based on value
                normalized = (value - min_val) / value_range if value_range > 0 else 0
                if normalized < 0.33:
                    color = "green"
                elif normalized < 0.67:
                    color = "yellow"
                else:
                    color = "red"

                row_data.append(f"[{color}]{value:.0f}[/{color}]")

            table.add_row(*row_data)

        return table


class ScheduleVisualizer:
    """Visualize schedules and shift patterns."""

    @staticmethod
    def calendar_view(year: int, month: int,
                      schedule_data: List[Dict[str, Any]]) -> Panel:
        """Create a calendar view of schedule."""
        # Group schedule by date
        schedule_by_date = defaultdict(list)
        for entry in schedule_data:
            if entry.get('date'):
                schedule_by_date[entry['date']].append(entry)

        # Create calendar
        cal = calendar.monthcalendar(year, month)
        month_name = calendar.month_name[month]

        # Build calendar display
        lines = [f"{month_name} {year}".center(50)]
        lines.append("Mo  Tu  We  Th  Fr  Sa  Su")
        lines.append("-" * 27)

        for week in cal:
            week_line = []
            for day in week:
                if day == 0:
                    week_line.append("  ")
                else:
                    date_obj = date(year, month, day)

                    # Check if there's a schedule for this day
                    if date_obj in schedule_by_date:
                        # Has schedule - show in color
                        shifts = schedule_by_date[date_obj]
                        if len(shifts) > 1:
                            week_line.append(f"[bold red]{day:2}[/bold red]")
                        else:
                            week_line.append(f"[green]{day:2}[/green]")
                    else:
                        week_line.append(f"{day:2}")

            lines.append("  ".join(week_line))

        # Add legend
        lines.append("")
        lines.append("[green]●[/green] Single shift  [bold red]●[/bold red] Multiple shifts")

        return Panel("\n".join(lines), title="Schedule Calendar", border_style="blue")

    @staticmethod
    def shift_timeline(schedule_data: List[Dict[str, Any]],
                       days: int = 7) -> Table:
        """Create a timeline view of shifts."""
        # Sort by date
        sorted_schedule = sorted(
            schedule_data,
            key=lambda x: x.get('date', date.min)
        )

        # Create table
        table = Table(title=f"Shift Timeline ({days} days)", box=box.ROUNDED)
        table.add_column("Date", style="cyan")
        table.add_column("Weekday")
        table.add_column("Shift", style="yellow")
        table.add_column("Time")
        table.add_column("Location", style="green")

        # Add rows
        for entry in sorted_schedule[:days]:
            date_obj = entry.get('date')
            weekday = date_obj.strftime("%A") if date_obj else ""

            shift_info = entry.get('5SHIFT_related', {})
            workplace_info = entry.get('5WOPL_related', {})

            table.add_row(
                str(date_obj) if date_obj else "N/A",
                weekday,
                shift_info.get('name', 'Unknown'),
                shift_info.get('startend', 'N/A'),
                workplace_info.get('name', 'Unknown')
            )

        return table


class StatisticsVisualizer:
    """Visualize statistical data."""

    @staticmethod
    def absence_summary(absence_data: Dict[str, Any]) -> Layout:
        """Create absence summary visualization."""
        layout = Layout()

        # Top section - overview
        overview = Panel(
            f"""[bold]Absence Report Summary[/bold]

Year: {absence_data.get('year', 'N/A')}
Total Absences: {absence_data.get('total_absences', 0)}
Employees Affected: {len(absence_data.get('by_employee', {}))}
Leave Types Used: {len(absence_data.get('by_leave_type', {}))}""",
            title="Overview",
            border_style="green"
        )

        # Create charts
        by_type_chart = AsciiChart.bar_chart(
            absence_data.get('by_leave_type', {}),
            title="Absences by Leave Type"
        )

        # Top employees by absence
        by_employee = absence_data.get('by_employee', {})
        top_employees = dict(sorted(
            by_employee.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])

        employee_chart = AsciiChart.bar_chart(
            top_employees,
            title="Top 10 Employees by Absence Days"
        )

        # Layout
        layout.split_column(
            Layout(overview, size=8),
            Layout(by_type_chart, size=12),
            Layout(employee_chart, size=12)
        )

        return layout

    @staticmethod
    def shift_distribution(shift_data: Dict[str, Any]) -> Panel:
        """Visualize shift distribution."""
        lines = []

        # Overview
        lines.append(f"[bold]Shift Distribution Analysis[/bold]\n")
        lines.append(f"Period: {shift_data.get('period', {}).get('start', 'N/A')} to "
                     f"{shift_data.get('period', {}).get('end', 'N/A')}")
        lines.append(f"Total Shifts: {shift_data.get('total_shifts', 0)}")
        lines.append(f"Unique Employees: {shift_data.get('unique_employees', 0)}\n")

        # Shift type distribution
        shift_types = shift_data.get('shift_types', {})
        if shift_types:
            lines.append(AsciiChart.bar_chart(
                shift_types,
                title="Shifts by Type",
                width=40
            ))

        # Weekday distribution
        weekday_dist = shift_data.get('weekday_distribution', {})
        if weekday_dist:
            lines.append("\n[bold]Weekday Distribution:[/bold]")

            # Count total shifts per weekday
            weekday_totals = {}
            for day, shifts in weekday_dist.items():
                weekday_totals[day] = sum(shifts.values())

            lines.append(AsciiChart.bar_chart(
                weekday_totals,
                title="Shifts by Weekday",
                width=40
            ))

        return Panel("\n".join(lines), title="Shift Distribution", border_style="blue")


class DashboardCreator:
    """Create comprehensive dashboards."""

    @staticmethod
    def create_employee_dashboard(employee_data: Dict[str, Any],
                                  schedule_data: List[Dict[str, Any]],
                                  absence_data: List[Dict[str, Any]]) -> Layout:
        """Create employee dashboard."""
        layout = Layout()

        # Employee info panel
        emp_info = f"""[bold]{employee_data.get('name', '')} {employee_data.get('firstname', '')}[/bold]

ID: {employee_data.get('id', 'N/A')}
Position: {employee_data.get('position', 'N/A')}
Department: {employee_data.get('group', 'N/A')}
Email: {employee_data.get('email', 'N/A')}
Employment: {employee_data.get('empstart', 'N/A')} - {employee_data.get('empend', 'Present')}"""

        info_panel = Panel(emp_info, title="Employee Information", border_style="cyan")

        # Schedule summary
        current_month = datetime.now()
        schedule_panel = ScheduleVisualizer.calendar_view(
            current_month.year,
            current_month.month,
            schedule_data
        )

        # Absence summary
        absence_by_type = Counter()
        for absence in absence_data:
            type_name = absence.get('leave_type_name', f"Type {absence.get('leave_type_id', 'Unknown')}")
            absence_by_type[type_name] += 1

        absence_chart = AsciiChart.bar_chart(
            dict(absence_by_type),
            title="Absences by Type (Current Year)",
            width=30
        )

        # Layout
        layout.split_row(
            Layout(info_panel, name="info"),
            Layout(name="right")
        )

        layout["right"].split_column(
            Layout(schedule_panel, name="schedule"),
            Layout(absence_chart, name="absences")
        )

        return layout

    @staticmethod
    def create_operations_dashboard(stats: Dict[str, Any]) -> Table:
        """Create operations dashboard."""
        # Create main table
        table = Table(title="Operations Dashboard", box=box.DOUBLE_EDGE)

        # System status
        table.add_column("Metric", style="cyan", width=30)
        table.add_column("Value", style="green", width=20)
        table.add_column("Status", width=10)

        # Add metrics
        metrics = [
            ("Tables Loaded", stats.get('tables_loaded', 0), "✓"),
            ("Total Records", f"{stats.get('total_records', 0):,}", "✓"),
            ("Memory Usage (MB)", f"{stats.get('memory_usage_mb', 0):.1f}",
             "⚠" if stats.get('memory_usage_mb', 0) > 500 else "✓"),
            ("Active Operations", stats.get('active_operations', 0),
             "⚠" if stats.get('active_operations', 0) > 5 else "✓"),
            ("Cache Hit Rate", f"{stats.get('cache_hit_rate', 0):.1%}",
             "✓" if stats.get('cache_hit_rate', 0) > 0.8 else "⚠"),
        ]

        for metric, value, status in metrics:
            table.add_row(metric, str(value), status)

        return table


# Visualization CLI commands
def visualize_command(viz_type: str, data: Any, options: Dict[str, Any] = None):
    """Main visualization dispatcher."""
    options = options or {}

    if viz_type == "bar":
        chart = AsciiChart.bar_chart(data, **options)
        console.print(chart)

    elif viz_type == "line":
        chart = AsciiChart.line_chart(data, **options)
        console.print(chart)

    elif viz_type == "heatmap":
        table = AsciiChart.heatmap(data, **options)
        console.print(table)

    elif viz_type == "calendar":
        panel = ScheduleVisualizer.calendar_view(
            options.get('year', datetime.now().year),
            options.get('month', datetime.now().month),
            data
        )
        console.print(panel)

    elif viz_type == "timeline":
        table = ScheduleVisualizer.shift_timeline(data, options.get('days', 7))
        console.print(table)

    elif viz_type == "dashboard":
        if options.get('type') == 'employee':
            layout = DashboardCreator.create_employee_dashboard(
                options.get('employee_data', {}),
                options.get('schedule_data', []),
                options.get('absence_data', [])
            )
            console.print(layout)
        elif options.get('type') == 'operations':
            table = DashboardCreator.create_operations_dashboard(data)
            console.print(table)

    else:
        console.print(f"[error]Unknown visualization type: {viz_type}[/error]")