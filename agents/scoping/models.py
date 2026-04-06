"""Data models for the scoping pipeline."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Contact:
    first_name: str
    last_name: str
    title: str = ""
    email: str = ""
    linkedin_url: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class Organization:
    name: str
    website_url: str = ""
    industry: str = ""
    employee_count: str = ""
    short_description: str = ""

    @property
    def safe_name(self) -> str:
        """PascalCase name for file paths — no spaces or special chars."""
        return "".join(
            word.capitalize()
            for word in self.name.replace("-", " ").replace("_", " ").split()
            if word.isalnum() or word.replace(".", "").isalnum()
        )


@dataclass
class ScopingRequest:
    contact: Contact
    organization: Organization
    notes: str = ""

    @classmethod
    def from_webhook(cls, payload: dict) -> ScopingRequest:
        """Parse an Apollo webhook payload into a ScopingRequest."""
        c = payload.get("contact", {})
        o = payload.get("organization", {})
        return cls(
            contact=Contact(
                first_name=c.get("first_name", ""),
                last_name=c.get("last_name", ""),
                title=c.get("title", ""),
                email=c.get("email", ""),
                linkedin_url=c.get("linkedin_url", ""),
            ),
            organization=Organization(
                name=o.get("name", ""),
                website_url=o.get("website_url", ""),
                industry=o.get("industry", ""),
                employee_count=o.get("employee_count", ""),
                short_description=o.get("short_description", ""),
            ),
            notes=payload.get("notes", ""),
        )


@dataclass
class ResearchResult:
    """Output of prospect research."""
    company_overview: str = ""
    mission_and_strategy: str = ""
    recent_news: list[str] = field(default_factory=list)
    tech_landscape: str = ""
    likely_pain_points: list[str] = field(default_factory=list)
    suggested_questions: list[str] = field(default_factory=list)
    raw_sources: list[str] = field(default_factory=list)


@dataclass
class ScopingAnswer:
    """Answer to one of the 5 scoping questions from transcript analysis."""
    question: str
    answer: str
    confidence: str  # High / Medium / Low / Not Discussed
    direct_quote: str = ""


@dataclass
class ScopingAnalysis:
    """Full transcript analysis output."""
    answers: list[ScopingAnswer] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    followup_questions: list[str] = field(default_factory=list)
    problem_summary: str = ""
    champion: str = ""
    decision_maker: str = ""
    timeline_signal: str = ""
    budget_signal: str = ""
