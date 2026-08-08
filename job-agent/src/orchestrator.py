import argparse
import asyncio
import os
import random
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env", override=True)

from state import (  # noqa: E402
    KillSwitchActive,
    DailyCeilingReached,
    BackoffActive,
    STAGES,
    load_config,
    preflight,
    new_run_id,
    start_stage,
    finish_stage,
    last_run_stage_status,
    most_recent_run_id,
)
import discovery  # noqa: E402
import scoring  # noqa: E402
import tailoring  # noqa: E402
import contacts  # noqa: E402
import outreach  # noqa: E402
import digest  # noqa: E402


def jitter_sleep():
    config = load_config()
    delay = random.randint(config["jitter_seconds_min"], config["jitter_seconds_max"])
    print(f"Jitter sleep: {delay}s")
    time.sleep(delay)


def run_discovery_stage():
    new_jobs, err = asyncio.run(discovery.run_discovery())
    if err:
        raise RuntimeError(f"discovery errored: {err}")
    return f"{len(new_jobs)} new jobs"


def run_scoring_stage():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None  # signals "skipped" to the caller
    scored, rejected, failed = scoring.run_scoring()
    return f"{len(scored)} passed threshold, {len(rejected)} rejected, {len(failed)} failed to score"


def run_tailoring_stage():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    # Only generates diffs + emails them for review; no PDF is rendered here.
    # A human must run `python3 tailoring.py --approve <job_id>` (or
    # --approve-all) before contacts/outreach/digest have any 'tailored'
    # jobs to work with — those stages will simply find nothing to do until
    # that happens, which is expected, not a failure.
    pending = tailoring.run_tailoring()
    return f"{len(pending)} resume diff(s) generated and sent for review — approve before contacts/digest can proceed"


def run_contacts_stage():
    contact_results, err = asyncio.run(contacts.run_contact_discovery())
    if err:
        raise RuntimeError(f"contact discovery errored: {err}")
    return f"processed {len(contact_results)} companies"


def run_outreach_digest_stage():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    n_drafted = outreach.run_outreach_drafting()

    digests = digest.build_all_digests()
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    config = load_config()
    n_sent = 0
    for d in digests:
        job = d["job"]
        subject = f"[Job Digest] {job['title']} @ {job['company']}"
        if gmail_address and gmail_app_password:
            digest.send_digest_email(
                subject, d["body"], d["resume_path"],
                gmail_address, gmail_app_password, config["digest_email_to"],
            )
            digest.mark_digested(job["id"])
            n_sent += 1
        else:
            print(f"  GMAIL not configured — digest built but not sent: {subject}")
    return f"{n_drafted} messages drafted, {n_sent} digest emails sent"


STAGE_RUNNERS = {
    "discovery": run_discovery_stage,
    "scoring": run_scoring_stage,
    "tailoring": run_tailoring_stage,
    "contacts": run_contacts_stage,
    "outreach_digest": run_outreach_digest_stage,
}


def hand_off_to_stage(run_id, stage_name, stage_index):
    """Run one stage under a state-tracked handoff: mark running, execute,
    record completed/skipped/failed. Raises on failure so the planner can
    stop the chain."""
    print(f"Stage {stage_index}/5: {stage_name}")
    stage_run_id = start_stage(run_id, stage_name)
    try:
        summary = STAGE_RUNNERS[stage_name]()
        if summary is None:
            finish_stage(stage_run_id, "skipped", result_summary="ANTHROPIC_API_KEY not set")
            print("  skipped: ANTHROPIC_API_KEY not set")
        else:
            finish_stage(stage_run_id, "completed", result_summary=summary)
            print(f"  {summary}")
    except Exception as e:
        finish_stage(stage_run_id, "failed", error=str(e))
        print(f"  failed: {e}")
        raise


def run(resume_run_id=None):
    try:
        preflight()
    except (KillSwitchActive, DailyCeilingReached, BackoffActive) as e:
        print(f"Run skipped: {e}")
        sys.exit(0)

    if resume_run_id:
        run_id = resume_run_id
        prior = last_run_stage_status(run_id)
        stages_to_run = [s for s in STAGES if prior.get(s) != "completed"]
        print(f"Resuming run {run_id} from stage(s): {', '.join(stages_to_run) or '(none — already complete)'}")
    else:
        run_id = new_run_id()
        stages_to_run = STAGES
        jitter_sleep()

    print(f"Run ID: {run_id}")

    for stage_name in stages_to_run:
        stage_index = STAGES.index(stage_name) + 1
        try:
            hand_off_to_stage(run_id, stage_name, stage_index)
        except Exception:
            print(f"Run stopped at stage '{stage_name}'. Resume later with: "
                  f"python3 orchestrator.py --resume {run_id}")
            sys.exit(1)

    print("Run complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", nargs="?", const="__last__", default=None,
                         help="Resume a run: pass a run_id, or omit the value to resume the most recent run")
    args = parser.parse_args()

    resume_id = args.resume
    if resume_id == "__last__":
        resume_id = most_recent_run_id()
        if not resume_id:
            print("No previous run found to resume.")
            sys.exit(1)

    run(resume_run_id=resume_id)
