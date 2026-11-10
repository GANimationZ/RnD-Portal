from datetime import date, datetime, timedelta

from library.extensions import db
from library.models import KPIRecord


def _week_start(day=None):
    day = day or date.today()
    return day - timedelta(days=day.weekday())


def _get_or_create_week_record(user_id, day=None):
    period_date = _week_start(day)
    record = KPIRecord.query.filter_by(user_id=user_id, period_date=period_date).first()
    if not record:
        record = KPIRecord(user_id=user_id, period_date=period_date)
        db.session.add(record)
        db.session.flush()
    return record


def record_assignment(user_id):
    if not user_id:
        return
    record = _get_or_create_week_record(user_id)
    record.total_assigned += 1
    record.pending += 1


def record_completion(user_id, created_at, already_assigned=True):
    """Called when an issue is marked Closed.

    `already_assigned=False` covers the "assign executor at close time"
    case -- total_assigned also needs +1 since record_assignment() was
    never called for this issue."""
    if not user_id:
        return

    record = _get_or_create_week_record(user_id)  # this week (the Close week)
    if not already_assigned:
        record.total_assigned += 1
    else:
        # Decrement pending on the CREATION week's record (where it was
        # incremented), not this week's -- otherwise it never clears.
        assignment_week_day = created_at.date() if created_at else None
        assignment_record = _get_or_create_week_record(user_id, assignment_week_day)
        assignment_record.pending = max(0, assignment_record.pending - 1)

    record.completed += 1

    if created_at:
        resolution_days = max(0.0, (datetime.utcnow() - created_at).total_seconds() / 86400)
        # Simple running average, weighted by completions so far.
        prior_completed = max(0, record.completed - 1)
        record.avg_resolution_days = round(
            ((record.avg_resolution_days * prior_completed) + resolution_days) / record.completed,
            2,
        )


def sync_overdue_flags():
    """Called on every /api/issues request: recomputes `overdue` on each
    assignee's current-week KPIRecord from issues that are still
    Open/Pending past their deadline. Reset-then-recount each call to
    avoid double-counting."""
    from library.models import Issue

    overdue_issues = Issue.query.filter(
        Issue.status.in_(["Open", "Pending"]),
        Issue.deadline < date.today(),
        Issue.assignee_id.isnot(None),
    ).all()

    counts = {}
    for issue in overdue_issues:
        counts[issue.assignee_id] = counts.get(issue.assignee_id, 0) + 1

    this_week = _week_start()
    for record in KPIRecord.query.filter_by(period_date=this_week).all():
        record.overdue = counts.get(record.user_id, 0)
