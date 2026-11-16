"""Who may be the assignee of an Issue.

Only an active Member whose scope (set in User Management) covers BOTH the
issue's Category and Event qualifies. Used by the assignee combobox, by Issue
creation (an issue cannot be registered while nobody qualifies) and by closing
an issue (it must have an assignee), so all three always agree.
"""

from library.models import User, UserCategoryScope, UserEventScope


def assignable_members(category, event):
    if not category or not event:
        return []
    return (
        User.query.filter_by(role="Member", is_active=True)
        .join(UserCategoryScope)
        .filter(UserCategoryScope.category == category)
        .join(UserEventScope, UserEventScope.user_id == User.id)
        .filter(UserEventScope.event == event)
        .order_by(User.username)
        .all()
    )


def find_assignable_member(user_id, category, event):
    """The member with this id if they qualify for category/event, else None."""
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None
    for member in assignable_members(category, event):
        if member.id == user_id:
            return member
    return None
