"""
HTML email templates for WFD OS consulting inquiries.

Two templates:
  - render_submitter_confirmation(inquiry, reference_number)
      -> (subject, html_body)  shown to the person who submitted the form
  - render_internal_notification(inquiry, reference_number)
      -> (subject, html_body)  shown to the CFA team (Ritu) for action

Both share a common purple header + dark footer so they feel like they
come from the same brand. Rendered inline styles only (no <style> blocks,
no external CSS) so they survive Outlook's HTML sanitizer.

Design tokens (kept in one place for easy tweaking):
  brand purple       #6B46C1
  brand purple light #E9D8FD
  brand purple hover #7C3AED
  ink                #1F2937
  ink-soft           #4B5563
  muted              #6B7280
  border             #E5E7EB
  surface            #F9FAFB
  footer             #1F2937
"""
from __future__ import annotations

import html as htmllib
import os
from typing import Any

BRAND_PURPLE = "#6B46C1"
BRAND_PURPLE_LIGHT = "#E9D8FD"
INK = "#1F2937"
INK_SOFT = "#4B5563"
MUTED = "#6B7280"
BORDER = "#E5E7EB"
SURFACE = "#F9FAFB"


def _esc(s: Any) -> str:
    """HTML-escape a value, treating None / empty as 'Not specified'."""
    if s is None:
        return "Not specified"
    text = str(s).strip()
    if not text:
        return "Not specified"
    return htmllib.escape(text)


def _dashboard_url() -> str:
    return os.getenv("INTERNAL_DASHBOARD_URL", "http://localhost:3000/internal")


def _header_html() -> str:
    return f"""
  <!-- Header -->
  <div style="background: {BRAND_PURPLE}; padding: 24px; border-radius: 8px 8px 0 0; text-align: center;">
    <h1 style="color: white; margin: 0; font-size: 24px; font-family: Arial, sans-serif;">Computing for All</h1>
    <p style="color: {BRAND_PURPLE_LIGHT}; margin: 4px 0 0; font-family: Arial, sans-serif;">AI Consulting</p>
  </div>
"""


def _footer_html() -> str:
    return f"""
  <!-- Footer -->
  <div style="background: {INK}; padding: 20px; border-radius: 0 0 8px 8px; text-align: center;">
    <p style="color: #9CA3AF; font-size: 12px; margin: 0; font-family: Arial, sans-serif;">
      Computing for All &middot; Bellevue, WA &middot;
      <a href="http://computingforall.org/ai-consulting" style="color: #A78BFA; text-decoration: none;">computingforall.org/ai-consulting</a>
    </p>
  </div>
"""


def _numbered_step(n: int, text: str) -> str:
    return f"""
      <div style="display: flex; align-items: flex-start; margin-bottom: 12px;">
        <span style="background: {BRAND_PURPLE}; color: white; border-radius: 50%; width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; margin-right: 12px; flex-shrink: 0; line-height: 24px; text-align: center;">{n}</span>
        <p style="color: {INK_SOFT}; margin: 2px 0; line-height: 1.5; font-family: Arial, sans-serif;">{text}</p>
      </div>
"""


def _info_row(label: str, value: str) -> str:
    return f"""
        <tr>
          <td style="color: {MUTED}; font-size: 14px; padding: 4px 0; width: 40%; font-family: Arial, sans-serif;">{htmllib.escape(label)}</td>
          <td style="color: {INK}; font-size: 14px; font-weight: 500; padding: 4px 0; font-family: Arial, sans-serif;">{_esc(value)}</td>
        </tr>"""


def render_submitter_confirmation(inquiry: Any, reference_number: str) -> tuple[str, str]:
    """Render the confirmation email for the person who submitted the form."""
    first_name = (inquiry.contact_name or "").strip().split()[0] if inquiry.contact_name else "there"

    subject = f"Your CFA project inquiry — {reference_number}"

    info_table = (
        _info_row("Organization", inquiry.organization_name)
        + _info_row("Project type", inquiry.project_area)
        + _info_row("Timeline", inquiry.timeline)
        + _info_row("Budget", inquiry.budget_range)
    )

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; background: #ffffff;">
{_header_html()}
  <!-- Body -->
  <div style="background: {SURFACE}; padding: 32px; border: 1px solid {BORDER}; border-top: none;">
    <h2 style="color: {INK}; font-size: 20px; margin-top: 0; font-family: Arial, sans-serif;">Thank you, {_esc(first_name)}!</h2>
    <p style="color: {INK_SOFT}; line-height: 1.6; font-family: Arial, sans-serif;">
      We&rsquo;ve received your project inquiry and are excited to learn more about what you&rsquo;re building.
    </p>

    <!-- Reference number box -->
    <div style="background: white; border: 2px solid {BRAND_PURPLE}; border-radius: 8px; padding: 16px 20px; margin: 24px 0; text-align: center;">
      <p style="color: {MUTED}; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 4px; font-family: Arial, sans-serif;">Your reference number</p>
      <p style="color: {BRAND_PURPLE}; font-size: 28px; font-weight: bold; margin: 0; letter-spacing: 2px; font-family: 'Courier New', monospace;">{_esc(reference_number)}</p>
    </div>

    <!-- Inquiry summary -->
    <div style="background: white; border: 1px solid {BORDER}; border-radius: 8px; padding: 16px 20px; margin: 24px 0;">
      <p style="color: {MUTED}; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 12px; font-family: Arial, sans-serif;">Your inquiry</p>
      <table style="width: 100%; border-collapse: collapse;">
        {info_table}
      </table>
    </div>

    <h3 style="color: {INK}; font-size: 16px; font-family: Arial, sans-serif;">What happens next</h3>
    <div style="margin: 0;">
      {_numbered_step(1, "Our team reviews your project description")}
      {_numbered_step(2, "We reach out within 24 hours to schedule a 30-minute scoping conversation")}
      {_numbered_step(3, "You receive a fixed-price proposal before anything starts")}
    </div>

    <p style="color: {INK_SOFT}; line-height: 1.6; margin-top: 24px; font-family: Arial, sans-serif;">
      Questions in the meantime? Reply to this email or reach us at
      <a href="mailto:ritu@computingforall.org" style="color: {BRAND_PURPLE}; text-decoration: none;">ritu@computingforall.org</a>
    </p>

    <p style="color: {INK_SOFT}; line-height: 1.6; margin-top: 24px; margin-bottom: 0; font-family: Arial, sans-serif;">
      We look forward to speaking with you.<br><br>
      <strong style="color: {INK};">Ritu Bahl</strong><br>
      Executive Director<br>
      Computing for All
    </p>
  </div>
{_footer_html()}
</body>
</html>"""

    return subject, html


def render_internal_notification(inquiry: Any, reference_number: str) -> tuple[str, str]:
    """Render the internal notification email for Ritu."""
    subject = f"\U0001F514 New inquiry: {inquiry.organization_name} — {reference_number}"

    coalition_str = "Yes" if getattr(inquiry, "is_coalition_member", False) else "No"

    # Contact info rows
    contact_table = (
        _info_row("Organization", inquiry.organization_name)
        + _info_row("Contact", inquiry.contact_name)
        + _info_row("Email", inquiry.email)
        + _info_row("Phone", inquiry.phone)
        + _info_row("Coalition member", coalition_str)
        + _info_row("Project type", inquiry.project_area)
        + _info_row("Timeline", inquiry.timeline)
        + _info_row("Budget", inquiry.budget_range)
    )

    # Highlighted project narrative
    def _narrative_block(label: str, text: str) -> str:
        return f"""
    <div style="background: white; border-left: 4px solid {BRAND_PURPLE}; border-radius: 4px; padding: 12px 16px; margin: 12px 0;">
      <p style="color: {MUTED}; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 6px; font-family: Arial, sans-serif;">{htmllib.escape(label)}</p>
      <p style="color: {INK}; font-size: 14px; line-height: 1.6; margin: 0; font-family: Arial, sans-serif; white-space: pre-wrap;">{_esc(text)}</p>
    </div>"""

    dashboard_url = _dashboard_url()

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; background: #ffffff;">
{_header_html()}
  <!-- Body -->
  <div style="background: {SURFACE}; padding: 32px; border: 1px solid {BORDER}; border-top: none;">
    <h2 style="color: {INK}; font-size: 20px; margin-top: 0; font-family: Arial, sans-serif;">New project inquiry received</h2>
    <p style="color: {INK_SOFT}; line-height: 1.6; margin: 0 0 20px; font-family: Arial, sans-serif;">
      A new inquiry just came in through the consulting intake form.
    </p>

    <!-- Reference number box -->
    <div style="background: white; border: 2px solid {BRAND_PURPLE}; border-radius: 8px; padding: 16px 20px; margin: 24px 0; text-align: center;">
      <p style="color: {MUTED}; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 4px; font-family: Arial, sans-serif;">Reference number</p>
      <p style="color: {BRAND_PURPLE}; font-size: 28px; font-weight: bold; margin: 0; letter-spacing: 2px; font-family: 'Courier New', monospace;">{_esc(reference_number)}</p>
    </div>

    <!-- Contact summary -->
    <div style="background: white; border: 1px solid {BORDER}; border-radius: 8px; padding: 16px 20px; margin: 24px 0;">
      <p style="color: {MUTED}; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 12px; font-family: Arial, sans-serif;">Contact &amp; project</p>
      <table style="width: 100%; border-collapse: collapse;">
        {contact_table}
      </table>
    </div>

    <!-- Project narrative -->
    <h3 style="color: {INK}; font-size: 16px; margin: 24px 0 8px; font-family: Arial, sans-serif;">Project details</h3>
    {_narrative_block("What they need built", inquiry.project_description)}
    {_narrative_block("Problem it solves", inquiry.problem_statement)}
    {_narrative_block("What success looks like", inquiry.success_criteria)}

    <!-- CTA -->
    <div style="text-align: center; margin: 32px 0 8px;">
      <a href="{_esc(dashboard_url)}"
         style="display: inline-block; background: {BRAND_PURPLE}; color: white; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: bold; font-family: Arial, sans-serif; font-size: 14px;">
        Review in dashboard &rarr;
      </a>
    </div>
    <p style="color: {MUTED}; font-size: 12px; text-align: center; margin: 4px 0 0; font-family: Arial, sans-serif;">
      {_esc(dashboard_url)}
    </p>
  </div>
{_footer_html()}
</body>
</html>"""

    return subject, html
