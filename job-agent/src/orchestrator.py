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
    load_config,
    preflight,
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


def run():
    try:
        preflight()
    except (KillSwitchActive, DailyCeilingReached, BackoffActive) as e:
        print(f"Run skipped: {e}")
        sys.exit(0)

    jitter_sleep()

    print("Stage 1/5: discovery")
    new_jobs, err = asyncio.run(discovery.run_discovery())
    if err:
        print(f"Discovery errored, stopping run: {err}")
        sys.exit(1)
    print(f"  {len(new_jobs)} new jobs")

    if os.environ.get("ANTHROPIC_API_KEY"):
        print("Stage 2/5: scoring")
        scored, rejected = scoring.run_scoring()
        print(f"  {len(scored)} passed threshold, {len(rejected)} rejected")

        print("Stage 3/5: resume tailoring")
        tailored = tailoring.run_tailoring()
        print(f"  {len(tailored)} resumes tailored")
    else:
        print("Stages 2-3 skipped: ANTHROPIC_API_KEY not set")

    print("Stage 4/5: contact discovery")
    contact_results, err = asyncio.run(contacts.run_contact_discovery())
    if err:
        print(f"Contact discovery errored: {err}")
    else:
        print(f"  processed {len(contact_results)} companies")

    if os.environ.get("ANTHROPIC_API_KEY"):
        print("Stage 5/5: outreach drafting + digest")
        n_drafted = outreach.run_outreach_drafting()
        print(f"  {n_drafted} messages drafted")

        digests = digest.build_all_digests()
        gmail_address = os.environ.get("GMAIL_ADDRESS")
        gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
        config = load_config()
        for d in digests:
            job = d["job"]
            subject = f"[Job Digest] {job['title']} @ {job['company']}"
            if gmail_address and gmail_app_password:
                digest.send_digest_email(
                    subject, d["body"], d["resume_path"],
                    gmail_address, gmail_app_password, config["digest_email_to"],
                )
                digest.mark_digested(job["id"])
                print(f"  digest sent: {subject}")
            else:
                print(f"  GMAIL not configured — digest built but not sent: {subject}")
    else:
        print("Stage 5 skipped: ANTHROPIC_API_KEY not set")

    print("Run complete.")


if __name__ == "__main__":
    run()
