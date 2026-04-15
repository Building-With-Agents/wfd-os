"""Pre-call and post-call pipeline orchestration.

Phase 1 (pre-call): research → briefing doc → SharePoint sites → Teams channel → meeting → notify
Phase 2 (post-call): transcript → analysis → proposal doc → notify
"""

from datetime import date

from agents.scoping.models import ScopingRequest, ScopingAnalysis
from agents.scoping.research import research_prospect
from agents.scoping.briefing import generate_briefing_doc
from agents.scoping.proposal import generate_proposal_doc
from wfdos_common.graph.sharepoint import (
    create_internal_client_site,
    create_client_portal_site,
    upload_document,
)
from wfdos_common.graph.teams import (
    create_client_channel,
    post_welcome_message,
    post_scoping_initiated,
    post_scoping_complete,
    schedule_scoping_meeting,
)
from wfdos_common.graph.transcript import retrieve_transcript


async def run_precall_pipeline(req: ScopingRequest) -> None:
    """Execute all Phase 1 steps in order."""
    company = req.organization.safe_name
    today = date.today().isoformat()
    print(f"[PIPELINE] Phase 1 starting for {company}")

    # Step 1: Prospect research
    print(f"[PIPELINE] Step 1 — Researching {req.organization.name}...")
    research = await research_prospect(req)
    print(f"[PIPELINE] Step 1 complete — research compiled")

    # Step 2: Generate briefing doc
    print(f"[PIPELINE] Step 2 — Generating briefing doc...")
    briefing_path = generate_briefing_doc(req, research)
    print(f"[PIPELINE] Step 2 complete — {briefing_path}")

    # Step 3: Create internal SharePoint site
    print(f"[PIPELINE] Step 3 — Creating internal client workspace...")
    internal_site = await create_internal_client_site(company)
    print(f"[PIPELINE] Step 3 complete — internal site ready")

    # Upload briefing doc to internal site (upload_document prepends Clients/)
    briefing_sp_url = await upload_document(
        briefing_path,
        f"{company}/Scoping/Briefing_{company}_{today}.docx",
    )
    print(f"[PIPELINE] Briefing doc uploaded to SharePoint")

    # Step 4: Create client-facing SharePoint site
    print(f"[PIPELINE] Step 4 — Creating client portal...")
    portal_url = await create_client_portal_site(req)
    print(f"[PIPELINE] Step 4 complete — client portal ready")

    # Step 5: Create Teams channel + welcome message
    print(f"[PIPELINE] Step 5 — Creating Teams channel...")
    channel_info = await create_client_channel(req)
    await post_welcome_message(channel_info, req, portal_url)
    print(f"[PIPELINE] Step 5 complete — Teams channel created")

    # Step 6: Schedule scoping meeting
    print(f"[PIPELINE] Step 6 — Scheduling scoping meeting...")
    meeting_info = await schedule_scoping_meeting(req)
    print(f"[PIPELINE] Step 6 complete — meeting scheduled")

    # Step 7: Notify CFA team
    print(f"[PIPELINE] Step 7 — Notifying CFA team...")
    await post_scoping_initiated(
        req=req,
        briefing_url=briefing_sp_url,
        internal_site_url=internal_site,
        portal_url=portal_url,
        channel_info=channel_info,
        meeting_info=meeting_info,
    )
    print(f"[PIPELINE] Phase 1 COMPLETE for {company}")


async def run_postcall_pipeline(meeting_id: str, req: ScopingRequest) -> None:
    """Execute all Phase 2 steps in order."""
    company = req.organization.safe_name
    today = date.today().isoformat()
    print(f"[PIPELINE] Phase 2 starting for {company}")

    # Step 1: Retrieve transcript
    print(f"[PIPELINE] Step 1 — Retrieving transcript...")
    transcript = await retrieve_transcript(meeting_id)
    print(f"[PIPELINE] Step 1 complete — transcript retrieved ({len(transcript)} chars)")

    # Upload transcript to SharePoint (upload_document prepends Clients/)
    transcript_sp_path = f"{company}/Scoping/Transcript_{company}_{today}.txt"
    local_transcript = f"output/Transcript_{company}_{today}.txt"
    import os
    os.makedirs("output", exist_ok=True)
    with open(local_transcript, "w", encoding="utf-8") as f:
        f.write(transcript)
    await upload_document(local_transcript, transcript_sp_path)

    # Step 2: Analyze transcript against 5 scoping questions
    print(f"[PIPELINE] Step 2 — Analyzing transcript...")
    from agents.scoping.transcript_analysis import analyze_transcript
    analysis = await analyze_transcript(transcript, req)
    print(f"[PIPELINE] Step 2 complete — analysis done")

    # Step 3: Gaps identified as part of analysis
    print(f"[PIPELINE] Step 3 — Gaps: {len(analysis.gaps)} found")

    # Step 4: Generate proposal doc
    print(f"[PIPELINE] Step 4 — Generating proposal...")
    proposal_path = generate_proposal_doc(req, analysis)
    proposal_sp_url = await upload_document(
        proposal_path,
        f"{company}/Proposal/Proposal_{company}_{today}.docx",
    )
    print(f"[PIPELINE] Step 4 complete — {proposal_path}")

    # Step 5: Notify CFA team
    print(f"[PIPELINE] Step 5 — Notifying CFA team...")
    await post_scoping_complete(
        req=req,
        analysis=analysis,
        proposal_url=proposal_sp_url,
        transcript_url=transcript_sp_path,
    )
    print(f"[PIPELINE] Phase 2 COMPLETE for {company}")
