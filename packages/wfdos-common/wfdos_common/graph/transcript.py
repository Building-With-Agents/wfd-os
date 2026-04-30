"""Retrieve and process meeting transcripts from Microsoft Graph API."""

import asyncio
from wfdos_common.graph.auth import get_graph_client
from wfdos_common.graph import config


async def retrieve_transcript(meeting_id: str, max_wait_minutes: int = 120) -> str:
    """Retrieve the transcript for a Teams meeting.

    Polls every 5 minutes for up to max_wait_minutes (default 2 hours)
    until the transcript is available.
    """
    client = get_graph_client()

    if not meeting_id or not config.AZURE_TENANT_ID:
        print("[TRANSCRIPT] No meeting ID or credentials — returning empty transcript")
        return ""

    poll_interval = 5 * 60  # 5 minutes
    max_attempts = max_wait_minutes * 60 // poll_interval

    for attempt in range(max_attempts):
        try:
            # Get transcripts for the meeting
            transcripts = await client.communications.online_meetings.by_online_meeting_id(
                meeting_id
            ).transcripts.get()

            if transcripts and transcripts.value:
                # Get the first transcript's content
                transcript_id = transcripts.value[0].id
                content = await client.communications.online_meetings.by_online_meeting_id(
                    meeting_id
                ).transcripts.by_call_transcript_id(
                    transcript_id
                ).content.get()

                if content:
                    raw_text = content.decode("utf-8") if isinstance(content, bytes) else str(content)
                    cleaned = _clean_transcript(raw_text)
                    print(f"[TRANSCRIPT] Retrieved transcript ({len(cleaned)} chars)")
                    return cleaned

        except Exception as e:
            error_str = str(e)
            if "NotFound" in error_str or "404" in error_str:
                print(f"[TRANSCRIPT] Attempt {attempt + 1}/{max_attempts} — transcript not yet available")
            else:
                print(f"[TRANSCRIPT] Error on attempt {attempt + 1}: {e}")

        if attempt < max_attempts - 1:
            print(f"[TRANSCRIPT] Waiting 5 minutes before next attempt...")
            await asyncio.sleep(poll_interval)

    print(f"[TRANSCRIPT] Transcript not available after {max_wait_minutes} minutes")
    return ""


def _clean_transcript(raw: str) -> str:
    """Clean a raw Teams transcript into readable speaker-labeled text."""
    lines = raw.split("\n")
    cleaned = []
    current_speaker = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Teams VTT format typically has timestamps and speaker labels
        # Skip timestamp lines (e.g., "00:01:23.456 --> 00:01:25.789")
        if "-->" in line:
            continue

        # Skip numeric-only lines (subtitle indices)
        if line.isdigit():
            continue

        # Detect speaker labels (e.g., "<v Speaker Name>text</v>")
        if line.startswith("<v ") and ">" in line:
            speaker_end = line.index(">")
            speaker = line[3:speaker_end]
            text = line[speaker_end + 1:].replace("</v>", "").strip()
            if speaker != current_speaker:
                current_speaker = speaker
                cleaned.append(f"\n{speaker}:")
            if text:
                cleaned.append(f"  {text}")
        else:
            # Plain text line — append to current speaker
            if line:
                cleaned.append(f"  {line}")

    return "\n".join(cleaned)
