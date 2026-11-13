from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta

from library.issue_lifecycle import (
    STAGE_AVAILABLE,
    STAGE_CLOSED,
    STAGE_OVERDUE,
    STAGE_PENDING,
    stage_on,
)
from library.models import Issue

# ---- Ranges: This Month / Last Week / Last Month / Last Year ----
RANGE_LABELS = {
    "recent": "This Month",
    "week": "Last Week",
    "month": "Last Month",
    "year": "Last Year",
}

DEFAULT_RANGE = "recent"

# Green (light/fast) -> yellow (medium) -> red (heavy/slow).
WORKLOAD_STOPS = [
    (30, 126, 51),    # #1e7e33
    (242, 166, 35),   # #f2a623
    (226, 75, 74),    # #e24b4a
]


def _interpolate_workload_color(ratio):
    ratio = min(max(ratio, 0), 1)
    if ratio <= 0.5:
        (r1, g1, b1), (r2, g2, b2) = WORKLOAD_STOPS[0], WORKLOAD_STOPS[1]
        local = ratio / 0.5
    else:
        (r1, g1, b1), (r2, g2, b2) = WORKLOAD_STOPS[1], WORKLOAD_STOPS[2]
        local = (ratio - 0.5) / 0.5

    r = round(r1 + (r2 - r1) * local)
    g = round(g1 + (g2 - g1) * local)
    b = round(b1 + (b2 - b1) * local)
    return f"rgb({r}, {g}, {b})"


def workload_bar(avg_hours):
    """~20h counts as light/fast, ~60h+ counts as heavy/slow."""
    lo, hi = 20, 60
    ratio = (min(max(avg_hours, lo), hi) - lo) / (hi - lo)
    width_pct = round(15 + ratio * 85)  # 15% floor so the bar stays visible
    return {"widthPct": width_pct, "color": _interpolate_workload_color(ratio)}


def completion_rate(total_assigned, completed):
    return round((completed / total_assigned) * 100) if total_assigned else 0


def rate_color(rate):
    if rate >= 70:
        return "#1e7e33"
    if rate >= 50:
        return "#f2a623"
    return "#e24b4a"


def initials(name):
    parts = [part[0] for part in name.split() if part]
    return "".join(parts)[:2].upper()


# ==================== Time windows ====================

def _month_start_offset(day, months_back):
    index = day.year * 12 + (day.month - 1) - months_back
    return date(index // 12, index % 12 + 1, 1)


def month_window(year, month):
    """A whole calendar month, day 1 through its last day."""
    last_day = monthrange(year, month)[1]
    start = date(year, month, 1)
    return {
        "key": f"{year}-{month:02d}",
        "range": f"{year}-{month:02d}",
        "label": start.strftime("%B %Y"),
        "rangeLabel": start.strftime("%B %Y"),
        "start": start,
        "end": date(year, month, last_day),
        "step": "day",
        "compact_labels": True,   # x axis shows 1, 2, 3 ... (month is in the title)
    }


def range_window(range_key, today=None):
    today = today or date.today()
    if range_key not in RANGE_LABELS:
        range_key = DEFAULT_RANGE

    if range_key == "recent":
        window = month_window(today.year, today.month)
    elif range_key == "month":
        previous = _month_start_offset(today, 1)
        window = month_window(previous.year, previous.month)
    elif range_key == "week":
        start = today - timedelta(days=6)
        window = {
            "start": start, "end": today, "step": "day", "compact_labels": False,
            "label": f"{start.strftime('%d %b')} - {today.strftime('%d %b %Y')}",
        }
    else:  # year
        start = _month_start_offset(today, 11)
        window = {
            "start": start, "end": today, "step": "month", "compact_labels": False,
            "label": f"{start.strftime('%b %Y')} - {today.strftime('%b %Y')}",
        }

    window["range"] = range_key
    window["rangeLabel"] = RANGE_LABELS[range_key]
    window["key"] = None
    return window


def _points(window, today):
    """[(label, evaluate_on_day, is_future)] -- one per day (or per month)
    from the window's first day to its last, so the chart always spans the
    whole period even though the future part has no data yet."""
    points = []
    start, end = window["start"], window["end"]

    if window["step"] == "day":
        day = start
        while day <= end:
            label = str(day.day) if window["compact_labels"] else day.strftime("%d %b")
            points.append((label, min(day, today), day > today))
            day += timedelta(days=1)
        return points

    month_start = start.replace(day=1)
    while month_start <= end:
        month_end = month_start.replace(day=monthrange(month_start.year, month_start.month)[1])
        points.append((month_start.strftime("%b %y"), min(month_end, end, today), month_start > today))
        month_start = month_end + timedelta(days=1)
    return points


# ==================== Issue-derived counts ====================

def issues_by_assignee():
    grouped = defaultdict(list)
    for issue in Issue.query.filter(Issue.assignee_id.isnot(None)).all():
        grouped[issue.assignee_id].append(issue)
    return grouped


def _in_window(issue, window_start):
    """Not closed before the window began (otherwise it belongs to the past)."""
    return issue.closed_at is None or issue.closed_at.date() >= window_start


def _counts_on(issues, window_start, day, today):
    counts = {STAGE_CLOSED: 0, STAGE_AVAILABLE: 0, STAGE_PENDING: 0, STAGE_OVERDUE: 0}
    for issue in issues:
        if not _in_window(issue, window_start):
            continue
        stage = stage_on(issue, day, today)
        if stage is not None:
            counts[stage] += 1
    return counts


def _avg_resolution_days(issues, window, as_of):
    durations = [
        (issue.closed_at - issue.created_at).total_seconds() / 86400
        for issue in issues
        if issue.closed_at is not None
        and issue.created_at is not None
        and window["start"] <= issue.closed_at.date() <= as_of
    ]
    return round(sum(durations) / len(durations), 2) if durations else 0


def aggregate(issues, window, today=None):
    """Card numbers for one employee in `window`, taken at the window's last
    day that has already happened."""
    today = today or date.today()
    as_of = min(window["end"], today)
    counts = _counts_on(issues, window["start"], as_of, today)
    completed = counts[STAGE_CLOSED]
    available, pending, overdue = (
        counts[STAGE_AVAILABLE], counts[STAGE_PENDING], counts[STAGE_OVERDUE]
    )
    return {
        "totalAssigned": completed + available + pending + overdue,
        "completed": completed,
        "available": available,
        "pending": pending,
        "overdue": overdue,
        "avgResolutionDays": _avg_resolution_days(issues, window, as_of),
    }


def build_trend_series(issues, window, today=None):
    """One point per day from the first to the last day of the window.
    Days that have not happened yet are None, so the line stops at today but
    the axis still runs to the end of the month."""
    today = today or date.today()
    series = {"labels": [], "resolved": [], "available": [], "pending": [], "overdue": []}

    for label, day, is_future in _points(window, today):
        series["labels"].append(label)
        if is_future:
            counts = None
        else:
            counts = _counts_on(issues, window["start"], day, today)
        series["resolved"].append(counts[STAGE_CLOSED] if counts else None)
        series["available"].append(counts[STAGE_AVAILABLE] if counts else None)
        series["pending"].append(counts[STAGE_PENDING] if counts else None)
        series["overdue"].append(counts[STAGE_OVERDUE] if counts else None)

    series["title"] = window["label"]
    return series


def _employee_row(emp, issues, window, today, with_detail=False):
    totals = aggregate(issues, window, today)
    avg_hours = round(totals["avgResolutionDays"] * 24, 1)
    rate = completion_rate(totals["totalAssigned"], totals["completed"])

    row = {
        "id": emp.id,
        "name": emp.username,
        "role": emp.job_title or "Member",
        "team": ", ".join(emp.categories) if emp.categories else "-",
        "initials": initials(emp.username),
        **totals,
        "avgResolutionHours": avg_hours,
        "completionRate": rate,
        "completionRateColor": rate_color(rate),
        "workload": workload_bar(avg_hours),
    }
    if with_detail:
        row["range"] = window["range"]
        row["rangeLabel"] = window["rangeLabel"]
        row["trend"] = build_trend_series(issues, window, today)
        row["bestPractices"] = [bp.note for bp in emp.best_practices]
    return row


def employee_list_summary(employees, window, today=None):
    """Per-employee summary for tables/lists (no trend/notes, to keep
    the payload small) -- used by the Individual list and Team panel."""
    today = today or date.today()
    grouped = issues_by_assignee()
    return [_employee_row(emp, grouped.get(emp.id, []), window, today) for emp in employees]


def employee_insights(per_employee):
    """Who has the lightest workload, and who needs the most attention."""
    if not per_employee:
        return None

    lightest = min(per_employee, key=lambda e: e["avgResolutionHours"])
    heaviest = max(per_employee, key=lambda e: e["avgResolutionHours"])
    return {
        "lightest": {
            "name": lightest["name"],
            "hours": lightest["avgResolutionHours"],
            "color": lightest["workload"]["color"],
        },
        "heaviest": {
            "name": heaviest["name"],
            "hours": heaviest["avgResolutionHours"],
            "color": heaviest["workload"]["color"],
        },
    }


def employee_summary(employee, window, today=None):
    """Full detail for one employee: stat cards, trend chart, best
    practices. Used by both the live Individual panel and the History
    Individual sub-panel so they stay consistent."""
    today = today or date.today()
    issues = issues_by_assignee().get(employee.id, [])
    return _employee_row(employee, issues, window, today, with_detail=True)


def team_summary(employees, window, today=None):
    """Team totals, per-person comparison chart, and completion-rate leaderboard."""
    per_employee = employee_list_summary(employees, window, today)

    totals = {
        "totalAssigned": sum(e["totalAssigned"] for e in per_employee),
        "completed": sum(e["completed"] for e in per_employee),
        "available": sum(e["available"] for e in per_employee),
        "pending": sum(e["pending"] for e in per_employee),
        "overdue": sum(e["overdue"] for e in per_employee),
    }
    rate = completion_rate(totals["totalAssigned"], totals["completed"])

    leaderboard = sorted(per_employee, key=lambda e: e["completionRate"], reverse=True)
    for idx, row in enumerate(leaderboard):
        row["rank"] = idx + 1

    chart = {
        "labels": [e["name"] for e in per_employee],
        "completed": [e["completed"] for e in per_employee],
        "available": [e["available"] for e in per_employee],
        "pending": [e["pending"] for e in per_employee],
        "overdue": [e["overdue"] for e in per_employee],
    }

    return {
        "range": window["range"],
        "rangeLabel": window["rangeLabel"],
        "totals": totals,
        "completionRate": rate,
        "completionRateColor": rate_color(rate),
        "employees": per_employee,
        "leaderboard": leaderboard,
        "chart": chart,
        "insights": employee_insights(per_employee),
    }
