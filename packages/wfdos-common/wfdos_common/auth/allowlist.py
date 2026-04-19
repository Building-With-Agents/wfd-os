"""Email → role lookup driven by env-var allowlists.

This is intentionally simple: four comma-separated lists (admin, staff,
workforce-development, student) sourced from `settings.auth`. First
match wins in that order — a person on multiple lists gets the highest
tier.

Role ladder (highest → lowest privilege):
  admin                  — CFA ops (Gary, Ritu).
  staff                  — CFA team members (BD, marketing, training leads).
  workforce-development  — External customer users on a Waifinder
                           deployment — e.g. the Borderplex WFD director
                           using LaborPulse. NOT CFA staff; kept distinct
                           in audit logs + qa_feedback attribution.
  student                — Trainees on the talent-showcase side of the
                           platform.

Directors outrank students because LaborPulse access is their day job,
and we never want a student accidentally promoted into the LaborPulse
tier because of an allowlist collision.

The allowlists will migrate to a `users` table in the shared-infra DB
once the auth flow is exercised end-to-end — but starting env-driven
keeps the "every commit runnable with existing .env" invariant intact
for Phase 4.
"""

from __future__ import annotations


ALLOWED_ROLES = ("admin", "staff", "workforce-development", "student")


def _parse_list(csv: str) -> set[str]:
    return {e.strip().lower() for e in csv.split(",") if e.strip()}


def resolve_role(
    email: str,
    *,
    admin_csv: str,
    staff_csv: str,
    student_csv: str,
    workforce_development_csv: str = "",
) -> str | None:
    """Return the role for `email`, or None if not allowlisted.

    Matching is case-insensitive and whitespace-tolerant. The
    workforce-development kwarg defaults to empty for call-site
    backwards compatibility with existing tests that predate #59.
    """
    normalized = email.strip().lower()
    if not normalized:
        return None
    if normalized in _parse_list(admin_csv):
        return "admin"
    if normalized in _parse_list(staff_csv):
        return "staff"
    if normalized in _parse_list(workforce_development_csv):
        return "workforce-development"
    if normalized in _parse_list(student_csv):
        return "student"
    return None


def is_allowed(
    email: str,
    *,
    admin_csv: str,
    staff_csv: str,
    student_csv: str,
    workforce_development_csv: str = "",
) -> bool:
    return resolve_role(
        email,
        admin_csv=admin_csv,
        staff_csv=staff_csv,
        student_csv=student_csv,
        workforce_development_csv=workforce_development_csv,
    ) is not None


__all__ = ["ALLOWED_ROLES", "resolve_role", "is_allowed"]
