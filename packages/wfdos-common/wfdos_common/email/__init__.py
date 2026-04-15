"""wfdos_common.email — outbound email via Microsoft Graph sendMail.

Migrated from agents/portal/email.py in Building-With-Agents/wfd-os#17.
The old path (agents/portal/email.py) now re-exports from here for one
deprecation cycle.

Public API (preserved):
- send_email(to, subject, body, html=bool) -> dict
- notify_internal(subject, body) -> dict

Never raises — always returns a status dict.

Implementation populated later in this same PR (commit: migrate email).
"""
