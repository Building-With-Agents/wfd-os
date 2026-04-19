"""Email → role lookup driven by env-var allowlists.

This is intentionally simple: three comma-separated lists (admin, staff,
student) sourced from `settings.auth`. First match wins in that order,
so a person on both admin + student lists is treated as admin.

The allowlists will migrate to a `users` table in the shared-infra DB
once the auth flow is exercised end-to-end — but starting env-driven
keeps the "every commit runnable with existing .env" invariant intact
for Phase 4.
"""

from __future__ import annotations


ALLOWED_ROLES = ("admin", "staff", "student")


def _parse_list(csv: str) -> set[str]:
    return {e.strip().lower() for e in csv.split(",") if e.strip()}


def resolve_role(
    email: str,
    *,
    admin_csv: str,
    staff_csv: str,
    student_csv: str,
) -> str | None:
    """Return the role for `email`, or None if not allowlisted.

    Matching is case-insensitive and whitespace-tolerant.
    """
    normalized = email.strip().lower()
    if not normalized:
        return None
    if normalized in _parse_list(admin_csv):
        return "admin"
    if normalized in _parse_list(staff_csv):
        return "staff"
    if normalized in _parse_list(student_csv):
        return "student"
    return None


def is_allowed(email: str, *, admin_csv: str, staff_csv: str, student_csv: str) -> bool:
    return resolve_role(
        email,
        admin_csv=admin_csv,
        staff_csv=staff_csv,
        student_csv=student_csv,
    ) is not None


__all__ = ["ALLOWED_ROLES", "resolve_role", "is_allowed"]
