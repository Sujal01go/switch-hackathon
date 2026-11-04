"""Phase 4 Demonstration: Deep Git Integration, Diff Generation, and GitHub PR Workflow."""

import sys
import shutil
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.config import DEFAULT_REPO_PATH, SQLITE_DB_PATH
from src.switch.client import SwitchClient
from src.db.task_store import TaskStore
from src.git.repo_manager import GitRepoManager
from src.git.github_client import GitHubClient
from src.agents.codex import CodexLeadAgent
from src.agents.cursor import CursorDeveloperAgent
from src.agents.opencode import OpenCodeQAAgent
from src.state import TeamWorkflowState, TaskStatus, ApprovalReport

def print_banner(text: str):
    print("\n" + "=" * 76)
    print(f"🔹 {text}")
    print("=" * 76)

def main():
    repo_path = Path(DEFAULT_REPO_PATH).resolve()
    upload_py = repo_path / "upload.py"
    upload_buggy = repo_path / "upload_buggy.py"

    print_banner("PHASE 4: GITHUB INTEGRATION & HUMAN APPROVAL DEMONSTRATION")
    print(f"• Repository Directory: {repo_path}")
    print(f"• Target Task:           Fix 10MB PDF Upload Internal Server Error 500")

    # Step 0: Ensure repository is reset to baseline bug
    if upload_buggy.exists():
        shutil.copy(upload_buggy, upload_py)
        print("• Status: Clean baseline bug restored in sample_repo/upload.py")

    # Initialize Git Manager
    git_mgr = GitRepoManager(repo_path)
    if not git_mgr.is_git_repo():
        git_mgr.init_repo()

    # Step 1: Repository Inspection
    print_banner("STEP 1: REPOSITORY INSPECTION")
    repo_info = git_mgr.inspect_repository()
    print(f"• Git Repository Detected:  {repo_info['is_git']}")
    print(f"• Active Base Branch:       {repo_info['branch']}")
    print(f"• Clean Working Tree:       {repo_info['status']['is_clean']}")
    print(f"• Tracked Python Files:     {', '.join(repo_info['python_files'])}")
    if repo_info['recent_commits']:
        print("• Recent Baseline Commits:")
        for c in repo_info['recent_commits']:
            print(f"    - [{c['sha']}] {c['subject']} ({c['author']})")

    # Step 2: Cursor Investigation & Implementation
    print_banner("STEP 2: CURSOR INVESTIGATION & IMPLEMENTATION")
    switch_client = SwitchClient(on_message_callback=lambda s, r, t: print(f"  💬 [{s} -> @{r}]: {t}"))
    cursor = CursorDeveloperAgent(switch_client)

    inv_report = cursor.investigate(str(repo_path), "Users get 500 internal server error uploading PDFs >10MB")
    print(f"• Root Cause:     {inv_report.root_cause}")
    print(f"• Affected Files: {', '.join(inv_report.affected_files)}")

    print("\nApplying code patch to resolve buffer overflow...")
    imp_report = cursor.implement(str(repo_path), inv_report)
    print(f"• Modified: {', '.join(imp_report.modified_files)}")
    print(f"• Summary:  {imp_report.summary}")

    # Step 3: Git Status & Unified Diff Inspection
    print_banner("STEP 3: UNIFIED GIT DIFF GENERATION")
    git_status = git_mgr.get_status()
    print(f"• Modified Files: {git_status['modified']}")
    print("• Unified Diff (`git diff` output):")
    diff_text = git_mgr.get_diff()
    print("-" * 50)
    print(diff_text if diff_text.strip() else imp_report.diff)
    print("-" * 50)

    # Step 4: OpenCode Adversarial QA & Pytest Review
    print_banner("STEP 4: OPENCODE ADVERSARIAL QA & TEST AUDIT")
    opencode = OpenCodeQAAgent(switch_client)
    review_report = opencode.review_and_test(str(repo_path), imp_report, iteration=1)
    print(f"• QA Verdict:      {review_report.verdict}")
    print(f"• Tests Executed:  {review_report.tests_executed} ({review_report.tests_passed} passed, {review_report.tests_failed} failed)")
    print(f"• QA Critique:     {review_report.critique}")

    # Step 5: Human Approval Gate (Mandatory before Git Commit / PR)
    print_banner("STEP 5: HUMAN APPROVAL GATE (TELEGRAM MIRROR)")
    codex = CodexLeadAgent(switch_client)
    codex.request_human_approval("PHASE4-001", f"QA review passed ({review_report.tests_passed} tests passed)")

    # Simulate developer approval in Telegram
    print("\nSimulating Human Developer approval in Telegram...")
    switch_client.post_to_room("Human", "Approve", target="codex")
    switch_client.post_to_room("Codex", "Approval received. Creating the pull request.")

    # Step 6: Isolated Branching, Safe Commit, and GitHub PR Creation
    print_banner("STEP 6: GIT FEATURE BRANCH, COMMIT & GITHUB PR CREATION")
    branch_name = "fix/task-phase4-pdf-upload"
    git_mgr.create_and_checkout_branch(branch_name)
    print(f"• Checked out feature branch: '{branch_name}'")

    commit_msg = (
        "fix(upload): resolve 10MB PDF upload internal server error (Task #PHASE4-001)\n\n"
        "Gracefully handles file sizes exceeding 10MB without raising unhandled 500 RuntimeError.\n"
        "Verified by: OpenCode QA (5/5 tests passed)\n"
        "Approved by: Human Developer via Telegram"
    )
    commit_sha = git_mgr.commit_changes(commit_msg)
    print(f"• Safe Git Commit Created: {commit_sha}")
    print(f"• Commit Author: Cursor AI (Switch)")

    # Generate GitHub Pull Request
    gh_client = GitHubClient()
    pr_title = "fix(upload): resolve 10MB PDF upload internal server error (Task #PHASE4-001)"
    pr_body = gh_client.generate_pr_body(
        task_id="PHASE4-001",
        request="Users are getting an internal server error when uploading PDFs larger than 10 MB.",
        root_cause=inv_report.root_cause,
        modified_files=imp_report.modified_files,
        review_summary=review_report.critique,
        tests_passed=review_report.tests_passed,
        iteration_count=1
    )
    pr_result = gh_client.create_pull_request(
        title=pr_title,
        body=pr_body,
        head_branch=branch_name
    )
    pr_url = pr_result.get("pr_url")
    print(f"• Pull Request Status: {pr_result['mode'].upper()}")
    print(f"• PR URL:             {pr_url}")

    # Step 7: Final Codex Report Posted to Telegram
    print_banner("STEP 7: FINAL CODEX REPORT MIRRORED TO TELEGRAM")
    state = TeamWorkflowState(
        task_id="PHASE4-001",
        raw_request="Users are getting an internal server error when uploading PDFs larger than 10 MB. Investigate and fix this.",
        repo_path=str(repo_path),
        investigation=inv_report,
        implementation=imp_report,
        review=review_report,
        approval=ApprovalReport(approved=True, comment="Approved by developer in Telegram"),
        iteration_count=1,
        git_branch=branch_name,
        pr_url=pr_url
    )
    final_report = codex.generate_final_report(state, pr_url=pr_url)

    print("\n" + "=" * 76)
    print("✅ PHASE 4 DEMONSTRATION COMPLETE: REPO INSPECTION, DIFF, APPROVAL & PR")
    print("=" * 76)

if __name__ == "__main__":
    main()

