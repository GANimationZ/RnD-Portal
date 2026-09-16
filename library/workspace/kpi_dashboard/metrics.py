"""
Semua perhitungan yang dulu dilakukan di static/javascript/workspace/
kpi-dashboard.js (interpolasi warna beban kerja, completion rate, ranking
leaderboard, agregasi rentang waktu, dsb) sekarang pindah ke sini.

kpi-dashboard.js versi baru cuma fetch endpoint /api/* di routes.py dan
merender field yang SUDAH JADI (angka, warna hex, persentase, label) ke
DOM/Chart.js -- tidak ada lagi logic matematis di sisi client selain hal
yang memang wajib di browser (Chart.js butuh dipanggil dari JS).
"""

from datetime import date, timedelta

# ---- Rentang waktu: Recent / Last Week / Last Month / Last Year ----
# Semua rentang dihitung relatif ke hari ini terhadap KPIRecord.period_date,
# jadi menambah rentang baru nanti cukup nambah 1 baris di sini.
RANGE_WINDOW_DAYS = {
    "recent": 14,   # ringkasan cepat ~2 minggu terakhir (default panel)
    "week": 7,      # 7 hari terakhir
    "month": 30,    # 30 hari terakhir
    "year": 365,    # 365 hari terakhir
}

RANGE_LABELS = {
    "recent": "Recent",
    "week": "Last Week",
    "month": "Last Month",
    "year": "Last Year",
}

DEFAULT_RANGE = "recent"

# Sama seperti WORKLOAD_STOPS versi JS lama: hijau (cepat/ringan) -> kuning
# (sedang) -> merah (lama/berat).
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
    """hours ~20 dianggap ringan/cepat, ~60+ dianggap berat/lama."""
    lo, hi = 20, 60
    ratio = (min(max(avg_hours, lo), hi) - lo) / (hi - lo)
    width_pct = round(15 + ratio * 85)  # floor 15% biar bar selalu kelihatan
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
    # Kalau rentangnya kosong (mis. karyawan baru), tetap tampilkan minimal
    # 1 titik data terakhir supaya panel tidak kosong total.
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
    """Ringkasan per-karyawan untuk tabel/list (tanpa trend & catatan,
    biar payload kecil) -- dipakai di panel Individual (daftar) & Team."""
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
                "name": emp.name,
                "role": emp.role,
                "team": emp.team,
                "initials": initials(emp.name),
                **totals,
                "avgResolutionHours": avg_hours,
                "completionRate": rate,
                "completionRateColor": rate_color(rate),
                "workload": bar,
            }
        )
    return result


def employee_insights(per_employee):
    """Setara renderEmployeeInsights() versi JS lama: siapa paling ringan &
    siapa paling perlu perhatian."""
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
    """Detail lengkap 1 karyawan: stat cards, trend chart, best practices.
    Dipakai baik oleh panel Individual (live) maupun sub-panel History
    Individual, supaya tampilannya konsisten (poin 2 & 3 permintaan)."""
    records = records_in_range(employee, range_key)
    totals = aggregate_records(records)
    avg_hours = round(totals["avgResolutionDays"] * 24, 1)
    bar = workload_bar(avg_hours)
    rate = completion_rate(totals["totalAssigned"], totals["completed"])

    return {
        "id": employee.id,
        "name": employee.name,
        "role": employee.role,
        "team": employee.team,
        "initials": initials(employee.name),
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
    """Setara renderTeamPanel() versi JS lama: totals tim, chart perbandingan
    per orang, dan leaderboard completion rate -- semua sudah dihitung di
    Python."""
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
