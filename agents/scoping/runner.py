"""Run the full Phase 1 pipeline live with a real prospect."""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import asyncio
from dotenv import load_dotenv
load_dotenv(override=True)

from agents.scoping.models import ScopingRequest
from agents.scoping.pipeline import run_precall_pipeline


PAYLOAD = {
    "contact": {
        "first_name": "Alma",
        "last_name": "Rodriguez",
        "title": "Director of Workforce Services",
        "email": "alma@wsborderplex.com",
        "linkedin_url": "",
    },
    "organization": {
        "name": "Workforce Solutions Borderplex",
        "website_url": "https://wsborderplex.com",
        "industry": "Workforce Development",
        "employee_count": "50-100",
        "short_description": "Regional workforce board serving the El Paso and Borderplex region",
    },
    "notes": "Warm intro via Ritu. First external target for Waifinder consulting. Interested in labor market intelligence tooling for the Borderplex region.",
}


async def main():
    req = ScopingRequest.from_webhook(PAYLOAD)
    print(f"Starting Phase 1 for: {req.organization.name}")
    print(f"Contact: {req.contact.full_name} ({req.contact.title})")
    print(f"Industry: {req.organization.industry}")
    print("=" * 60)
    await run_precall_pipeline(req)


if __name__ == "__main__":
    asyncio.run(main())
