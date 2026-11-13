from datetime import date, datetime, timedelta

from library.models import Issue

MEDIUM_FROM = 0.40
HIGH_FROM = 0.75

STAGE_AVAILABLE = "available"
STAGE_PENDING = "pending"
STAGE_OVERDUE = "overdue"
STAGE_CLOSED = "closed"


def _created_day(issue):
    return (issue.created_at or datetime.utcnow()).date()


def midpoint_day(issue):
    start = _created_day(issue)
    return start + timedelta(days=(issue.deadline - start).days / 2)


def elapsed_fraction(issue, today=None):
    today = today or date.today()
    start = _created_day(issue)
    total = (issue.deadline - start).days
    if total <= 0:
        return 1.0
    return max(0.0, (today - start).days / total)


def compute_priority(issue, today=None):
    fraction = elapsed_fraction(issue, today)
    if fraction >= HIGH_FROM:
        return "High"
    if fraction >= MEDIUM_FROM:
        return "Medium"
    return "Low"


def stage_on(issue, day, today=None):
    """Stage of `issue` at the end of `day` (None if it did not exist yet).

    Today's stage follows the real status (so "On Hold"/manual changes are
    respected). Earlier days are reconstructed from the dates, since no status
    history is stored."""
    today = today or date.today()
    if _created_day(issue) > day:
        return None
    if issue.closed_at is not None and issue.closed_at.date() <= day:
        return STAGE_CLOSED
    if issue.deadline < day:
        return STAGE_OVERDUE
    if day >= today:
        return STAGE_AVAILABLE if issue.status == "Open" else STAGE_PENDING
    return STAGE_PENDING if day >= midpoint_day(issue) else STAGE_AVAILABLE


def refresh_issues(today=None):
    """Called whenever issues or KPI are read (there is no background job).

    * Open issues past their midpoint become Pending.
    * Priority is recalculated for every issue that is not closed. A closed
      issue keeps the priority it had when it was closed."""
    today = today or date.today()
    for issue in Issue.query.filter(Issue.status != "Closed").all():
        if issue.status == "Open" and today >= midpoint_day(issue):
            issue.status = "Pending"
        priority = compute_priority(issue, today)
        if issue.priority != priority:
            issue.priority = priority
