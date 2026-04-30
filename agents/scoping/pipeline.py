"""Pre-call and post-call pipeline orchestration.

Phase 1 (pre-call): research → briefing doc → SharePoint sites → Teams channel → meeting → notify
Phase 2 (post-call): transcript → analysis → proposal doc → notify
"""

from datetime import date

from wfdos_common.models.scoping import ScopingRequest, ScopingAnalysis
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
from wfdos_common.logging import get_logger

log = get_logger(__name__)


async def run_precall_pipeline(req: ScopingRequest) -> None:
    """Execute all Phase 1 steps in order."""
    company = req.organization.safe_name
    today = date.today().isoformat()
    log.info("scoping.precall.start", company=company)

    # Step 1: Prospect research
    log.info("scoping.precall.step_1.research.start", organization=req.organization.name)
    research = await research_prospect(req)
    log.info("scoping.precall.step_1.research.complete")

    # Step 2: Generate briefing doc
    log.info("scoping.precall.step_2.briefing.start")
    briefing_path = generate_briefing_doc(req, research)
    log.info("scoping.precall.step_2.briefing.complete", briefing_path=str(briefing_path))

    # Step 3: Create internal SharePoint site
    log.info("scoping.precall.step_3.internal_site.start")
    internal_site = await create_internal_client_site(company)
    log.info("scoping.precall.step_3.internal_site.complete")

    # Upload briefing doc to internal site (upload_document prepends Clients/)
    briefing_sp_url = await upload_document(
        briefing_path,
        f"{company}/Scoping/Briefing_{company}_{today}.docx",
    )
    log.info("scoping.precall.briefing.uploaded")

    # Step 4: Create client-facing SharePoint site
    log.info("scoping.precall.step_4.client_portal.start")
    portal_url = await create_client_portal_site(req)
    log.info("scoping.precall.step_4.client_portal.complete")

    # Step 5: Create Teams channel + welcome message
    log.info("scoping.precall.step_5.teams_channel.start")
    channel_info = await create_client_channel(req)
    await post_welcome_message(channel_info, req, portal_url)
    log.info("scoping.precall.step_5.teams_channel.complete")

    # Step 6: Schedule scoping meeting
    log.info("scoping.precall.step_6.meeting.start")
    meeting_info = await schedule_scoping_meeting(req)
    log.info("scoping.precall.step_6.meeting.complete")

    # Step 7: Notify CFA team
    log.info("scoping.precall.step_7.notify.start")
    await post_scoping_initiated(
        req=req,
        briefing_url=briefing_sp_url,
        internal_site_url=internal_site,
        portal_url=portal_url,
        channel_info=channel_info,
        meeting_info=meeting_info,
    )
    log.info("scoping.precall.complete", company=company)


async def run_postcall_pipeline(meeting_id: str, req: ScopingRequest) -> None:
    """Execute all Phase 2 steps in order."""
    company = req.organization.safe_name
    today = date.today().isoformat()
    log.info("scoping.postcall.start", company=company)

    # Step 1: Retrieve transcript
    log.info("scoping.postcall.step_1.transcript.start")
    transcript = await retrieve_transcript(meeting_id)
    log.info("scoping.postcall.step_1.transcript.complete", char_count=len(transcript))

    # Upload transcript to SharePoint (upload_document prepends Clients/)
    transcript_sp_path = f"{company}/Scoping/Transcript_{company}_{today}.txt"
    local_transcript = f"output/Transcript_{company}_{today}.txt"
    import os
    os.makedirs("output", exist_ok=True)
    with open(local_transcript, "w", encoding="utf-8") as f:
        f.write(transcript)
    await upload_document(local_transcript, transcript_sp_path)

    # Step 2: Analyze transcript against 5 scoping questions
    log.info("scoping.postcall.step_2.analysis.start")
    from agents.scoping.transcript_analysis import analyze_transcript
    analysis = await analyze_transcript(transcript, req)
    log.info("scoping.postcall.step_2.analysis.complete")

    # Step 3: Gaps identified as part of analysis
    log.info("scoping.postcall.step_3.gaps", gap_count=len(analysis.gaps))

    # Step 4: Generate proposal doc
    log.info("scoping.postcall.step_4.proposal.start")
    proposal_path = generate_proposal_doc(req, analysis)
    proposal_sp_url = await upload_document(
        proposal_path,
        f"{company}/Proposal/Proposal_{company}_{today}.docx",
    )
    log.info("scoping.postcall.step_4.proposal.complete", proposal_path=str(proposal_path))

    # Step 5: Notify CFA team
    log.info("scoping.postcall.step_5.notify.start")
    await post_scoping_complete(
        req=req,
        analysis=analysis,
        proposal_url=proposal_sp_url,
        transcript_url=transcript_sp_path,
    )
    log.info("scoping.postcall.complete", company=company)
