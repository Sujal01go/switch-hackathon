"""CLI entry point and interactive demonstration runner for the Multi-Agent Engineering Team."""

import sys
import shutil
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.config import DEFAULT_REPO_PATH, SQLITE_DB_PATH
from src.switch.client import SwitchClient
from src.db.task_store import TaskStore
from src.workflow.graph import EngineeringTeamWorkflow

AGENT_ICONS = {
    "Codex": "👑 [Codex Lead]",
    "Cursor": "💻 [Cursor Dev]",
    "OpenCode": "🛡️ [OpenCode QA]",
    "Human": "👤 [Human Dev]",
    "Switch": "🔄 [Switch Hub]"
}

def print_telegram_stream(sender: str, recipient: str, text: str):
    """Visualizes the Telegram message feed mirrored through Switch infrastructure."""
    icon = AGENT_ICONS.get(sender, f"[{sender}]")
    print(f"\n{icon} -> @{recipient}:")
    print(f"   {text}")

def main():
    parser = argparse.ArgumentParser(
        description="Switch Multi-Agent Engineering Team - Live Workflow Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Execution Modes:
  normal       Full collaborative workflow: intake -> dev -> QA pass -> human approve -> commit & PR.
  correction   Demonstrates automated QA failure loop: attempt 1 boundary flaw -> OpenCode critique -> Cursor correction -> QA pass.
  reject       Human developer rejects the proposed changes -> workflow halts safely without git commit.
  interactive  Prompts you on the console for approval [y/n] when the agents complete implementation.
        """
    )
    parser.add_argument(
        "request",
        nargs="?",
        default="Users are getting an internal server error when uploading PDFs larger than 10 MB. Investigate and fix this.",
        help="Task description or bug report (default: PDF upload bug)"
    )
    parser.add_argument(
        "--repo",
        default=str(DEFAULT_REPO_PATH),
        help="Path to repository to inspect and fix (default: ./sample_repo)"
    )
    parser.add_argument(
        "--task-id",
        default="001",
        help="Task tracking identifier (default: 001)"
    )
    parser.add_argument(
        "--mode",
        choices=["normal", "correction", "reject", "interactive"],
        default="normal",
        help="Execution mode (normal, correction, reject, interactive)"
    )

    args = parser.parse_args()

    repo_path = Path(args.repo).resolve()
    upload_py = repo_path / "upload.py"
    upload_buggy = repo_path / "upload_buggy.py"

    # Reset sample_repo to clean baseline bug if running on sample_repo
    if upload_buggy.exists() and upload_py.exists():
        shutil.copy(upload_buggy, upload_py)

    print("=" * 72)
    print("🚀 FLIP THE SWITCH — MULTI-AGENT SOFTWARE ENGINEERING TEAM")
    print("=" * 72)
    print(f"• Mode:         {args.mode.upper()}")
    print(f"• Task ID:      #{args.task_id}")
    print(f"• Repository:   {repo_path}")
    print(f"• Raw Request:  \"{args.request}\"")
    print(f"• Agents:       Codex (Lead) • Cursor (Developer) • OpenCode (QA)")
    print(f"• Channel:      Switch Hub bridged to Telegram (-5449527038)")
    print("-" * 72)
    print("📡 LIVE TELEGRAM STREAM VIA SWITCH:")

    # Initialize Switch client with live stream callback
    switch_client = SwitchClient(on_message_callback=print_telegram_stream)
    task_store = TaskStore(SQLITE_DB_PATH)

    workflow = EngineeringTeamWorkflow(switch_client, task_store)

    simulate_flaw = (args.mode == "correction")
    simulate_reject = (args.mode == "reject")

    if args.mode == "interactive":
        # Interactive prompt for approval
        final_state = workflow.run(
            raw_request=args.request,
            repo_path=str(repo_path),
            task_id=args.task_id,
            simulate_initial_flaw=False,
            simulate_human_rejection=False
        )
    else:
        final_state = workflow.run(
            raw_request=args.request,
            repo_path=str(repo_path),
            task_id=args.task_id,
            simulate_initial_flaw=simulate_flaw,
            simulate_human_rejection=simulate_reject
        )

    print("\n" + "=" * 72)
    print(f"🏁 WORKFLOW FINISHED WITH STATUS: {final_state.status.upper()}")
    print("=" * 72)

    if final_state.git_branch:
        print(f"• Git Feature Branch:  {final_state.git_branch}")
    if final_state.pr_url:
        print(f"• GitHub Pull Request: {final_state.pr_url}")

    # Inspect SQLite task record
    saved_task = task_store.get_task(args.task_id)
    if saved_task:
        print(f"• Database Audit:      {SQLITE_DB_PATH}")
        print(f"• Total Iterations:    {saved_task['iteration_count']}")
        print(f"• Final State Status:  {saved_task['status']}")

    print("-" * 72)

if __name__ == "__main__":
    main()
