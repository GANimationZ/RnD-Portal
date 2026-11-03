"""Derives a human display name from an email address, since the app no
longer collects a separate username at registration.

Example: "john.doe@test.com" -> "John Doe"
Only the first and last token of the local-part are used (middle names,
if any, are dropped), each capitalized.
"""

import re


def normalize_email(email):
    """Strip + lowercase, so "Bob@test.com" and "bob@test.com" map to the
    same DB value instead of registering as two different accounts."""
    return (email or "").strip().lower()


def is_valid_email_format(email):
    """Simple check (not a full RFC 5322 validator): just rejects the
    obvious non-emails like "abc" or a domain with no dot."""
    if "@" not in email:
        return False
    local_part, _, domain_part = email.rpartition("@")
    return bool(local_part) and "." in domain_part and not domain_part.startswith(".") and not domain_part.endswith(".")


def name_from_email(email):
    local_part = (email or "").split("@")[0]
    parts = [p for p in re.split(r"[._\-+]+", local_part) if p]

    if not parts:
        return "User"
    if len(parts) == 1:
        return parts[0].capitalize()

    return f"{parts[0].capitalize()} {parts[-1].capitalize()}"


def unique_display_name(base_name, exists_fn):
    """Appends " (2)", " (3)", ... until exists_fn(candidate) is False.
    exists_fn should check whether a User with that name already exists."""
    if not exists_fn(base_name):
        return base_name

    suffix = 2
    while True:
        candidate = f"{base_name} ({suffix})"
        if not exists_fn(candidate):
            return candidate
        suffix += 1
