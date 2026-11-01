"""Who may use the learning-style engine while it is being tested: admins only."""

from socrat.config import Settings
from socrat.models import User


def is_admin(settings: Settings, user: User) -> bool:
    emails = {e.lower() for e in settings.admin_emails}
    return (
        f"{user.issuer}|{user.subject}" in settings.admin_subjects
        or user.subject in settings.admin_subjects
        or (user.admin_email is not None and user.admin_email in emails)
    )


def enabled(settings: Settings, user: User) -> bool:
    """The kill switch is on and this account is an admin."""
    return settings.style_engine_enabled and is_admin(settings, user)
