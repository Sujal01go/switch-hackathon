"""Automated test suite for Multi-Agent Engineering Team Phase 2 & Phase 3 workflow."""

import pytest
import shutil
import sqlite3
from pathlib import Path

from src.state import TaskType, TaskStatus
from src.db.task_store import TaskStore
from src.switch.client import SwitchClient
from src.switch.protocol import SwitchProtocol
from src.agents.codex import CodexLeadAgent
from src.agents.cursor import CursorDeveloperAgent
from src.agents.opencode import OpenCodeQAAgent
from src.workflow.graph import EngineeringTeamWorkflow
from src.git.repo_manager import GitRepoManager
from src.git.github_client import GitHubClient

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_tasks.db"
    return TaskStore(str(db_file))

@pytest.fixture
def mock_switch():
    messages = []
    def callback(s, r, b):
        messages.append((s, r, b))
    client = SwitchClient(on_message_callback=callback, deliver_live=False)
    client.intercepted = messages
    return client

@pytest.fixture
def clean_repo(tmp_path):
    """Create a temporary replica of the sample repo with the bug."""
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()
    source_dir = Path("sample_repo")
    
    shutil.copy(source_dir / "upload_buggy.py", repo_dir / "upload.py")
    shutil.copy(source_dir / "test_upload.py", repo_dir / "test_upload.py")
    return repo_dir

def test_task_store(temp_db):
    """Test SQLite task store saving and retrieval."""
    temp_db.save_task({
        "task_id": "TEST-01",
        "raw_request": "Fix upload bug",
        "task_type": "bug",
        "status": "analyzed",
        "repo_path": "/path/to/repo",
        "iteration_count": 1
    })
    
    task = temp_db.get_task("TEST-01")
    assert task is not None
    assert task["task_id"] == "TEST-01"
    assert task["task_type"] == "bug"
    assert task["status"] == "analyzed"

    temp_db.record_message("TEST-01", "Codex", "Cursor", "telegram", "Please investigate")
    msgs = temp_db.get_messages("TEST-01")
    assert len(msgs) == 1
    assert msgs[0]["sender"] == "Codex"

def test_switch_protocol():
    """Test Switch message addressing and envelope formatting."""
    targeted = SwitchProtocol.format_targeted_message("cursor", "Start investigation")
    assert targeted == "@cursor Start investigation"

    envelope = SwitchProtocol.format_switch_envelope("Admin", "room-123", "Hello")
    assert "BEGIN SWITCH MESSAGE" in envelope
    assert "room-123" in envelope

def test_codex_analysis(mock_switch):
    """Test Codex task classification and intake."""
    codex = CodexLeadAgent(mock_switch)
    analysis = codex.analyze_task(
        "Users are getting an internal server error when uploading PDFs larger than 10 MB.",
        "001",
        "/test/repo"
    )
    assert analysis["task_type"] == TaskType.BUG
    assert analysis["status"] == TaskStatus.ANALYZED
    assert len(mock_switch.intercepted) >= 1

def test_cursor_investigation(mock_switch, clean_repo):
    """Test Cursor repository inspection and root cause diagnosis."""
    cursor = CursorDeveloperAgent(mock_switch)
    inv = cursor.investigate(str(clean_repo), "Fix PDF upload error")
    assert "RuntimeError" in inv.root_cause or "buffer overflow" in inv.root_cause.lower()
    assert "upload.py" in inv.affected_files

def test_cursor_implementation(mock_switch, clean_repo):
    """Test Cursor implementation fix on upload.py."""
    cursor = CursorDeveloperAgent(mock_switch)
    inv = cursor.investigate(str(clean_repo), "Fix PDF upload error")
    imp = cursor.implement(str(clean_repo), inv)
    assert "upload.py" in imp.modified_files
    
    fixed_content = (clean_repo / "upload.py").read_text()
    assert "Buffer overflow" not in fixed_content

def test_opencode_review_after_fix(mock_switch, clean_repo):
    """Test OpenCode QA review and pytest execution on fixed repo."""
    cursor = CursorDeveloperAgent(mock_switch)
    inv = cursor.investigate(str(clean_repo), "Fix PDF upload error")
    imp = cursor.implement(str(clean_repo), inv)

    opencode = OpenCodeQAAgent(mock_switch)
    rev = opencode.review_and_test(str(clean_repo), imp)
    
    assert rev.verdict == "PASS"
    assert rev.tests_passed >= 4
    assert rev.tests_failed == 0

def test_full_phase2_workflow(mock_switch, temp_db, clean_repo):
    """End-to-end integration test of single-cycle workflow."""
    workflow = EngineeringTeamWorkflow(mock_switch, temp_db)
    final_state = workflow.run(
        raw_request="Users are getting an internal server error when uploading PDFs larger than 10 MB. Investigate and fix this.",
        repo_path=str(clean_repo),
        task_id="HACKATHON-001"
    )

    assert final_state.status == TaskStatus.COMPLETED
    assert final_state.investigation is not None
    assert final_state.implementation is not None
    assert final_state.review is not None
    assert final_state.review.verdict == "PASS"
    assert final_state.final_report is not None

# --- PHASE 3 TESTS: CORRECTION LOOPS, FAILURE HANDLING, AND CHECKPOINTING ---

def test_correction_loop_on_review_failure(mock_switch, temp_db, clean_repo):
    """Test Phase 3 review and correction loop where cycle 1 fails and cycle 2 corrects it."""
    workflow = EngineeringTeamWorkflow(mock_switch, temp_db, max_review_cycles=3)
    final_state = workflow.run(
        raw_request="Fix PDF upload bug with boundary check",
        repo_path=str(clean_repo),
        task_id="LOOP-001",
        simulate_initial_flaw=True  # triggers >= boundary flaw in cycle 1
    )

    # In cycle 1, OpenCode fails due to boundary flaw
    # In cycle 2, Cursor receives critique and fixes operator to >
    # In cycle 2, OpenCode review passes
    assert final_state.status == TaskStatus.COMPLETED
    assert final_state.iteration_count == 2
    assert final_state.review.verdict == "PASS"
    
    # Check that Codex nudged Cursor with QA findings
    nudge_messages = [b for _, _, b in mock_switch.intercepted if "review failed on attempt" in b.lower()]
    assert len(nudge_messages) >= 1

def test_human_rejection_halts_workflow(mock_switch, temp_db, clean_repo):
    """Test that human rejecting proposed changes terminates without final report."""
    workflow = EngineeringTeamWorkflow(mock_switch, temp_db)
    final_state = workflow.run(
        raw_request="Fix PDF upload issue",
        repo_path=str(clean_repo),
        task_id="REJECT-001",
        simulate_human_rejection=True
    )

    assert final_state.status == TaskStatus.FAILED
    assert "rejected by human developer" in final_state.error.lower()
    assert final_state.final_report is None

def test_interrupted_approval_workflow(mock_switch, temp_db, clean_repo, tmp_path):
    """Test LangGraph native interrupt_before and resume_with_approval for live Telegram."""
    ckpt_db = str(tmp_path / "interrupted_ckpt.db")
    workflow = EngineeringTeamWorkflow(
        mock_switch,
        temp_db,
        checkpoint_db_path=ckpt_db,
        interrupt_approval=True
    )

    # 1. Run until approval gate
    paused_state = workflow.run_until_approval(
        raw_request="Fix PDF upload 10MB limit bug",
        repo_path=str(clean_repo),
        task_id="INTERRUPT-001"
    )

    # Verify paused state
    assert paused_state.review is not None
    assert paused_state.review.verdict == "PASS"
    assert paused_state.status == TaskStatus.IN_REVIEW
    assert paused_state.final_report is None

    # 2. Resume with approval
    resumed_state = workflow.resume_with_approval(
        task_id="INTERRUPT-001",
        approved=True,
        comment="Approved by developer in Telegram"
    )

    # Verify completion
    assert resumed_state.status == TaskStatus.COMPLETED
    assert resumed_state.approval is not None
    assert resumed_state.approval.approved is True
    assert resumed_state.final_report is not None
    assert "Task #" in resumed_state.final_report

# --- PHASE 4 TESTS: GIT & GITHUB INTEGRATION, DIFF REVIEW, AND PR CREATION ---

def test_git_repo_manager_diff_and_branch(clean_repo):
    """Test git repository initialization, branch creation, and unified diff generation."""
    git_mgr = GitRepoManager(clean_repo)
    assert git_mgr.init_repo() is True
    assert git_mgr.is_git_repo() is True
    
    # Create isolated branch
    assert git_mgr.create_and_checkout_branch("fix/test-branch") is True
    assert git_mgr.get_current_branch() == "fix/test-branch"
    
    # Modify a file
    test_file = clean_repo / "upload.py"
    original = test_file.read_text(encoding="utf-8")
    test_file.write_text(original + "\n# Test git modification\n", encoding="utf-8")
    
    diff = git_mgr.get_diff()
    assert "Test git modification" in diff
    
    # Commit changes
    sha = git_mgr.commit_changes("fix: apply test modification")
    assert sha is not None
    assert len(sha) == 40  # 40-character SHA-1

def test_github_client_simulated_pr():
    """Test GitHub client fallback when unconfigured, generating structured PR."""
    client = GitHubClient(token="", repo="")
    assert client.is_configured() is False
    
    body = client.generate_pr_body(
        task_id="GH-001",
        request="Fix PDF upload bug",
        root_cause="Size validation overflow",
        modified_files=["upload.py"],
        review_summary="All 5 tests passed",
        tests_passed=5,
        iteration_count=1
    )
    assert "Task #GH-001" in body
    assert "upload.py" in body
    assert "Verdict" in body
    
    res = client.create_pull_request(
        title="fix: resolve PDF upload bug",
        body=body,
        head_branch="fix/task-gh-001"
    )
    assert res["success"] is True
    assert res["mode"] == "simulated"
    assert "pull/101" in res["pr_url"]

def test_full_workflow_with_git_commit_and_pr(mock_switch, temp_db, clean_repo):
    """Test full workflow execution including git branch, commit, and PR creation upon approval."""
    workflow = EngineeringTeamWorkflow(mock_switch, temp_db)
    final_state = workflow.run(
        raw_request="Fix PDF upload internal server error for files > 10MB",
        repo_path=str(clean_repo),
        task_id="PHASE4-001"
    )

    assert final_state.status == TaskStatus.COMPLETED
    assert final_state.approval is not None
    assert final_state.approval.approved is True
    assert final_state.pr_url is not None
    assert "pull" in final_state.pr_url
    assert final_state.git_branch == "fix/task-phase4-001"
    assert final_state.pr_url in final_state.final_report

    # Verify Telegram transcript contains PR announcement
    pr_announcements = [b for _, _, b in mock_switch.intercepted if "PR:" in b]
    assert len(pr_announcements) >= 1

# --- PHASE 5 TESTS: TIMEOUT SAFEGUARDS & FAILURE BOUNDARY CONDITIONS ---

def test_opencode_timeout_handling(mock_switch, clean_repo):
    """Test that OpenCode QA agent catches test timeouts gracefully without crashing."""
    from unittest.mock import patch
    import subprocess
    from src.state import ImplementationReport
    opencode = OpenCodeQAAgent(mock_switch, test_timeout_seconds=5)
    
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=5)):
        review = opencode.review_and_test(
            repo_path=str(clean_repo),
            implementation=ImplementationReport(modified_files=["upload.py"]),
            iteration=1
        )
    
    assert review.verdict == "FAIL"
    assert "timed out" in review.critique.lower()

def test_max_review_cycles_exceeded(mock_switch, temp_db, clean_repo):
    """Test that workflow terminates with clear failure report when review repeatedly fails."""
    from src.state import ReviewReport
    workflow = EngineeringTeamWorkflow(mock_switch, temp_db, max_review_cycles=2)
    workflow.opencode.review_and_test = lambda *args, **kwargs: ReviewReport(
        verdict="FAIL",
        tests_executed=5,
        tests_passed=3,
        tests_failed=2,
        critique="Persistent boundary regression across all attempts",
        iteration=kwargs.get("iteration", 1)
    )

    final_state = workflow.run(
        raw_request="Fix PDF upload bug with persistent failure",
        repo_path=str(clean_repo),
        task_id="FAIL-MAX-001"
    )

    assert final_state.status == TaskStatus.FAILED
    assert "maximum review attempts" in final_state.error.lower()

    # Check alert was sent to Switch / Telegram
    alerts = [b for _, _, b in mock_switch.intercepted if "exceeded maximum automated review attempts" in b.lower()]
    assert len(alerts) >= 1

# --- MULTI-PROJECT & ADVANCED INTERACTIVE FEATURE TESTS ---

def test_project_manager_file_explorer_and_read(tmp_path):
    """Test ProjectManager file tree generation, file reading, and safe undo."""
    from src.project_manager import ProjectManager
    test_proj = tmp_path / "custom_app"
    test_proj.mkdir()
    (test_proj / "main.py").write_text("print('Hello from custom app')\n", encoding="utf-8")
    (test_proj / "config.json").write_text('{"name": "custom_app"}\n', encoding="utf-8")

    pm = ProjectManager(default_projects_dir=tmp_path)
    ok, _, resolved = pm.set_active_project(str(test_proj))
    assert ok is True
    assert pm.active_project == resolved

    # Test file tree
    tree = pm.get_project_files_tree()
    assert "main.py" in tree
    assert "config.json" in tree

    # Test file reading
    ok_read, content = pm.read_project_file("main.py")
    assert ok_read is True
    assert "Hello from custom app" in content

    # Test non-existent file
    ok_fail, err = pm.read_project_file("missing.py")
    assert ok_fail is False
    assert "does not exist" in err

def test_universal_multilang_opencode_review(mock_switch, tmp_path):
    """Test OpenCode multi-language static verification for Python, JSON, and HTML."""
    from src.agents.opencode import OpenCodeQAAgent
    from src.state import ImplementationReport

    opencode = OpenCodeQAAgent(mock_switch)
    test_repo = tmp_path / "web_project"
    test_repo.mkdir()

    # Valid Python and JSON files
    (test_repo / "server.py").write_text("def run():\n    return 42\n", encoding="utf-8")
    (test_repo / "data.json").write_text('{"status": "ok", "count": 10}\n', encoding="utf-8")
    (test_repo / "index.html").write_text("<!DOCTYPE html><html><body><h1>Title</h1></body></html>\n", encoding="utf-8")

    imp = ImplementationReport(modified_files=["server.py", "data.json", "index.html"])
    rev = opencode.review_and_test(str(test_repo), imp)
    assert rev.verdict == "PASS"
    assert rev.tests_passed >= 3

    # Introduce invalid JSON syntax to test QA failure detection
    (test_repo / "broken.json").write_text('{"unclosed": "json",\n', encoding="utf-8")
    imp_fail = ImplementationReport(modified_files=["broken.json"])
    rev_fail = opencode.review_and_test(str(test_repo), imp_fail)
    assert rev_fail.verdict == "FAIL"
    assert "Invalid JSON" in rev_fail.critique

def test_codex_interactive_diff_and_tree(mock_switch):
    """Test Codex lead displaying diff, file trees, and task history in Telegram format."""
    from src.agents.codex import CodexLeadAgent

    codex = CodexLeadAgent(mock_switch)
    
    # Test diff display
    sample_diff = "--- a/upload.py\n+++ b/upload.py\n@@ -20,2 +20,2 @@\n- old\n+ new"
    codex.display_diff(sample_diff, "DIFF-001")
    assert any("Code Diff for #DIFF-001" in b for _, _, b in mock_switch.intercepted)

    # Test project files display
    codex.display_project_files("portfolio", ["index.html", "style.css", "main.js"])
    assert any("Files in `portfolio`" in b for _, _, b in mock_switch.intercepted)





def test_cursor_react_chatbot_generation_and_opencode_review(mock_switch, tmp_path):
    """Test that Cursor creates real React TSX Chatbot component and wires it into App.tsx without touching README."""
    from src.agents.cursor import CursorDeveloperAgent
    from src.agents.opencode import OpenCodeQAAgent

    react_repo = tmp_path / "prompt-wars-replica"
    react_repo.mkdir()
    (react_repo / "README.md").write_text("# Prompt Wars\nOriginal documentation.\n", encoding="utf-8")
    (react_repo / "package.json").write_text('{"name": "prompt-wars", "dependencies": {"react": "^19.0.0", "typescript": "^5.0.0"}}\n', encoding="utf-8")
    (react_repo / "tsconfig.json").write_text('{}\n', encoding="utf-8")
    src_dir = react_repo / "src"
    src_dir.mkdir()
    app_tsx = src_dir / "App.tsx"
    app_tsx.write_text(
        "import React from 'react';\n"
        "import { Navbar } from './components/Navbar';\n\n"
        "export function App() {\n"
        "  return (\n"
        "    <div className='app'>\n"
        "      <Navbar />\n"
        "      <main><h1>Welcome</h1></main>\n"
        "      <footer>Footer</footer>\n"
        "    </div>\n"
        "  );\n"
        "}\n"
        "export default App;\n",
        encoding="utf-8"
    )

    cursor = CursorDeveloperAgent(mock_switch)
    inv = cursor.investigate(str(react_repo), "add a chatbot feature in prompt-wars")

    # 1. Verify investigation didn't target README
    assert "README.md" not in inv.affected_files
    assert "src/components/Chatbot.tsx" in inv.affected_files
    assert "src/App.tsx" in inv.affected_files

    # 2. Implement feature
    imp = cursor.implement(str(react_repo), inv, raw_request="add a chatbot feature in prompt-wars")

    # 3. Verify files modified
    assert "src/components/Chatbot.tsx" in imp.modified_files
    assert "src/App.tsx" in imp.modified_files
    assert "README.md" not in imp.modified_files

    # 4. Verify README was NOT changed
    readme_content = (react_repo / "README.md").read_text(encoding="utf-8")
    assert "Implemented by Cursor" not in readme_content

    # 5. Verify Chatbot.tsx content
    chatbot_file = react_repo / "src" / "components" / "Chatbot.tsx"
    assert chatbot_file.exists()
    chatbot_code = chatbot_file.read_text(encoding="utf-8")
    assert "export const Chatbot" in chatbot_code
    assert "useState" in chatbot_code
    assert "AI Assistant" in chatbot_code
    assert "export default Chatbot" in chatbot_code

    # 6. Verify App.tsx was wired properly
    app_code = app_tsx.read_text(encoding="utf-8")
    assert "import { Chatbot } from './components/Chatbot'" in app_code
    assert "<Chatbot />" in app_code

    # 7. OpenCode validates the TSX syntax
    opencode = OpenCodeQAAgent(mock_switch)
    rev = opencode.review_and_test(str(react_repo), imp)
    assert rev.verdict == "PASS"
    assert rev.tests_failed == 0


def test_cursor_python_service_generation(mock_switch, tmp_path):
    """Test that Cursor creates functional Python chatbot module with unit test block."""
    from src.agents.cursor import CursorDeveloperAgent
    from src.agents.opencode import OpenCodeQAAgent

    py_repo = tmp_path / "backend_service"
    py_repo.mkdir()
    (py_repo / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")

    cursor = CursorDeveloperAgent(mock_switch)
    inv = cursor.investigate(str(py_repo), "create an ai chatbot service")
    assert "chatbot.py" in inv.affected_files

    imp = cursor.implement(str(py_repo), inv, raw_request="create an ai chatbot service")
    assert "chatbot.py" in imp.modified_files

    chatbot_py = py_repo / "chatbot.py"
    assert chatbot_py.exists()
    py_code = chatbot_py.read_text(encoding="utf-8")
    assert "class ChatbotService" in py_code
    assert "process_message" in py_code

    # OpenCode validates Python AST compilation
    opencode = OpenCodeQAAgent(mock_switch)
    rev = opencode.review_and_test(str(py_repo), imp)
    assert rev.verdict == "PASS"
    assert rev.tests_failed == 0
