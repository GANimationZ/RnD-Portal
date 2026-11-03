import re


def normalize_email(email):
    return (email or "").strip().lower()


def is_valid_email_format(email):
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
    if not exists_fn(base_name):
        return base_name

    suffix = 2
    while True:
        candidate = f"{base_name} ({suffix})"
        if not exists_fn(candidate):
            return candidate
        suffix += 1
