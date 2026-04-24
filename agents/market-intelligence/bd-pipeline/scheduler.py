"""
Waifinder BD Pipeline — Scheduler

Schedules:
- 4:00 AM PST daily: Agent 15 market discovery
- 5:00 AM PST daily: full pipeline (run_agents.py)
- Every 15 minutes: Agent 13 content distribution
- Every 30 minutes: Agent 13 signal polling
- Every 6 hours: Agent 12 escalation check
- Sunday 6:00 AM PST: Agent 15 weekly summary
- Monday 7:00 AM PST: weekly report

Usage:
    python scheduler.py --deployment waifinder-national
    python scheduler.py --run-now
"""
import os
import sys
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from agent15 import run_discovery as agent15_discovery
from agent15 import weekly_summary as agent15_weekly_summary
from ingest import ingest, DEFAULT_QUERIES
from enrich import enrich
from suppression import run_suppression
from populate_prospects import populate
from agent12 import score_companies
from agent14 import run_agent14
from agent13 import distribute_content, process_sequence_touches, poll_for_replies
from notify import send_escalation_alerts, send_weekly_summary, send_partial_contact_digest

try:
    import schedule
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "schedule"])
    import schedule


def market_discovery(deployment_id):
    """4:00 AM PST — Agent 15 market discovery."""
    print(f"\n{'='*60}")
    print(f"Market Discovery: {datetime.now().isoformat()}")
    print(f"{'='*60}")
    try:
        agent15_discovery(deployment_id)
    except Exception as e:
        # Non-fatal — pipeline continues if discovery fails
        print(f"Agent 15 error (non-fatal): {e}")


def discovery_weekly(deployment_id):
    """Sunday 6:00 AM PST — Agent 15 weekly summary."""
    print(f"\n[{datetime.now().strftime('%H:%M')}] Agent 15 weekly summary")
    try:
        agent15_weekly_summary(deployment_id)
    except Exception as e:
        print(f"Agent 15 weekly summary error: {e}")


def daily_pipeline(deployment_id, region):
    """5:00 AM PST — full pipeline run."""
    print(f"\n{'='*60}")
    print(f"Daily Pipeline: {datetime.now().isoformat()}")
    print(f"{'='*60}")

    ingest(deployment_id, region, DEFAULT_QUERIES)
    enrich(deployment_id)
    run_suppression(deployment_id)
    populate(deployment_id, region)
    score_companies(deployment_id, region)
    send_escalation_alerts(deployment_id)

    print(f"Daily pipeline complete: {datetime.now().isoformat()}")


def distribution_loop(deployment_id, region):
    """Every 15 minutes — process pending content."""
    print(f"\n[{datetime.now().strftime('%H:%M')}] Distribution loop")
    try:
        distribute_content(deployment_id, region)
    except Exception as e:
        print(f"Distribution error: {e}")


def touch_loop(deployment_id):
    """Every 30 minutes — send pending Touch 2/3."""
    print(f"\n[{datetime.now().strftime('%H:%M')}] Touch processing loop")
    try:
        process_sequence_touches(deployment_id)
    except Exception as e:
        print(f"Touch processing error: {e}")


def reply_loop(deployment_id):
    """Every 30 minutes — poll inbox for replies."""
    print(f"\n[{datetime.now().strftime('%H:%M')}] Reply polling loop")
    try:
        poll_for_replies(deployment_id)
    except Exception as e:
        print(f"Reply polling error: {e}")


def escalation_check(deployment_id):
    """Every 6 hours — check for tier changes."""
    print(f"\n[{datetime.now().strftime('%H:%M')}] Escalation check")
    try:
        send_escalation_alerts(deployment_id)
    except Exception as e:
        print(f"Escalation check error: {e}")


def weekly_report(deployment_id):
    """Monday 7:00 AM PST — weekly summary."""
    print(f"\n[{datetime.now().strftime('%H:%M')}] Weekly report")
    try:
        send_weekly_summary(deployment_id)
    except Exception as e:
        print(f"Weekly report error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Waifinder BD Scheduler")
    parser.add_argument("--deployment", default="waifinder-national")
    parser.add_argument("--region", default="Greater Seattle")
    parser.add_argument("--run-now", action="store_true",
                        help="Run full pipeline immediately then start scheduler")
    args = parser.parse_args()

    dep = args.deployment
    region = args.region

    if args.run_now:
        daily_pipeline(dep, region)

    # Schedule all loops
    schedule.every().day.at("04:00").do(market_discovery, dep)
    schedule.every().day.at("05:00").do(daily_pipeline, dep, region)
    schedule.every(15).minutes.do(distribution_loop, dep, region)
    schedule.every(30).minutes.do(touch_loop, dep)
    schedule.every(30).minutes.do(reply_loop, dep)
    schedule.every(6).hours.do(escalation_check, dep)
    schedule.every().sunday.at("06:00").do(discovery_weekly, dep)
    schedule.every().monday.at("07:00").do(weekly_report, dep)
    schedule.every().monday.at("07:00").do(send_partial_contact_digest, dep)

    print(f"\nScheduler active — {dep}")
    print(f"  04:00 daily:     Agent 15 market discovery")
    print(f"  05:00 daily:     Full pipeline (includes Agent 14)")
    print(f"  Every 15 min:    Content distribution")
    print(f"  Every 30 min:    Signal polling")
    print(f"  Every 6 hours:   Escalation check")
    print(f"  Sunday 06:00:    Agent 15 weekly summary")
    print(f"  Monday 07:00:    Weekly report + partial contact digest")
    print("Press Ctrl+C to stop\n")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
