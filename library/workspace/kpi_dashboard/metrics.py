"""All KPI calculations (workload color, completion rate, leaderboard
ranking, range aggregation) live here. kpi-dashboard.js just fetches
/api/* and renders the ready-made fields -- no math on the client side
beyond what Chart.js itself requires."""

from datetime import date, timedelta

# ---- Ranges: Recent / Last Week / Last Month / Last Year ----
# All ranges are relative to today via KPIRecord.period_date, so adding a
# new range later is a single line here.
RANGE_WINDOW_DAYS = {
    "recent": 14,   # default panel view, last ~2 weeks
    "week": 7,
    "month": 30,
    "year": 365,
}

RANGE_LABELS = {
    "recent": "Recent",
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


def cutoff_date(range_key):
    days = RANGE_WINDOW_DAYS.get(range_key, RANGE_WINDOW_DAYS[DEFAULT_RANGE])
    return date.today() - timedelta(days=days)


def records_in_range(employee, range_key):
    cutoff = cutoff_date(range_key)
    in_range = [r for r in employee.kpi_records if r.period_date >= cutoff]
    # If nothing falls in range (e.g. a brand new member), still show the
    # latest single record so the panel isn't completely empty.
    if in_range:
        return in_range
    return employee.kpi_records[-1:]


def aggregate_records(records):
    if not records:
        return {"totalAssigned": 0, "completed": 0, "pending": 0, "overdue": 0, "avgResolutionDays": 0}

    total_assigned = sum(r.total_assigned for r in records)
    completed = sum(r.completed for r in records)
    pending = sum(r.pending for r in records)
    overdue = sum(r.overdue for r in records)
    avg_days = round(sum(r.avg_resolution_days for r in records) / len(records), 2)

    return {
        "totalAssigned": total_assigned,
        "completed": completed,
        "pending": pending,
        "overdue": overdue,
        "avgResolutionDays": avg_days,
    }


def build_trend_series(records):
    return {
        "labels": [r.period_date.strftime("%d %b") for r in records],
        "resolved": [r.completed for r in records],
        "pending": [r.pending for r in records],
        "overdue": [r.overdue for r in records],
    }


def employee_list_summary(employees, range_key=DEFAULT_RANGE):
    """Per-employee summary for tables/lists (no trend/notes, to keep
    the payload small) -- used by the Individual list and Team panel."""
    result = []
    for emp in employees:
        records = records_in_range(emp, range_key)
        totals = aggregate_records(records)
        avg_hours = round(totals["avgResolutionDays"] * 24, 1)
        bar = workload_bar(avg_hours)
        rate = completion_rate(totals["totalAssigned"], totals["completed"])

        result.append(
            {
                "id": emp.id,
                "name": emp.username,
                "role": emp.job_title or "Member",
                "team": ", ".join(emp.categories) if emp.categories else "-",
                "initials": initials(emp.username),
                **totals,
                "avgResolutionHours": avg_hours,
                "completionRate": rate,
                "completionRateColor": rate_color(rate),
                "workload": bar,
            }
        )
    return result


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


def employee_summary(employee, range_key=DEFAULT_RANGE):
    """Full detail for one employee: stat cards, trend chart, best
    practices. Used by both the live Individual panel and the History
    Individual sub-panel so they stay consistent."""
    records = records_in_range(employee, range_key)
    totals = aggregate_records(records)
    avg_hours = round(totals["avgResolutionDays"] * 24, 1)
    bar = workload_bar(avg_hours)
    rate = completion_rate(totals["totalAssigned"], totals["completed"])

    return {
        "id": employee.id,
        "name": employee.username,
        "role": employee.job_title or "Member",
        "team": ", ".join(employee.categories) if employee.categories else "-",
        "initials": initials(employee.username),
        "range": range_key,
        "rangeLabel": RANGE_LABELS.get(range_key, range_key),
        **totals,
        "avgResolutionHours": avg_hours,
        "completionRate": rate,
        "completionRateColor": rate_color(rate),
        "workload": bar,
        "trend": build_trend_series(records),
        "bestPractices": [bp.note for bp in employee.best_practices],
    }


def team_summary(employees, range_key=DEFAULT_RANGE):
    """Team totals, per-person comparison chart, and completion-rate leaderboard."""
    per_employee = employee_list_summary(employees, range_key)

    totals = {
        "totalAssigned": sum(e["totalAssigned"] for e in per_employee),
        "completed": sum(e["completed"] for e in per_employee),
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
        "pending": [e["pending"] for e in per_employee],
        "overdue": [e["overdue"] for e in per_employee],
    }

    return {
        "range": range_key,
        "rangeLabel": RANGE_LABELS.get(range_key, range_key),
        "totals": totals,
        "completionRate": rate,
        "completionRateColor": rate_color(rate),
        "employees": per_employee,
        "leaderboard": leaderboard,
        "chart": chart,
        "insights": employee_insights(per_employee),
    }
