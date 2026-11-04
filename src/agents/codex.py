"""Codex - Engineering Lead Agent (Full Interactive Commands & Reporting)."""

import re
from typing import Dict, Any, Optional, List
from pathlib import Path
from src.state import TaskType, TaskStatus, TeamWorkflowState, ReviewReport
from src.switch.client import SwitchClient

GREETING_PATTERNS = [
    r"^(hi|hello|hii|heyy|hey|yo|sup|howdy|holla)(\s+(all|guys|everyone|there|team|bot|codex))?[\s!.]*$",
    r"^(good\s+(morning|afternoon|evening|day))[\s!.]*$"
]

QUESTION_PATTERNS = [
    r"^(what|how|who|can you|could you|where|why|is there|tell me|explain)[\s\w\?.-]*$"
]


class CodexLeadAgent:
    def __init__(self, switch_client: SwitchClient):
        self.name = "Codex"
        self.role = "Engineering Lead"
        self.switch = switch_client

    def is_greeting(self, text: str) -> bool:
        """Determine if a message is purely a greeting."""
        clean = text.strip().lower()
        for pattern in GREETING_PATTERNS:
            if re.match(pattern, clean):
                return True
        return False

    def is_casual_or_question(self, text: str) -> bool:
        """Determine if message is an informational inquiry rather than an engineering task."""
        clean = text.strip().lower()
        # Explicit code action verbs mean it's a task, not a question
        if any(w in clean for w in ["fix", "modify", "change", "implement", "patch", "refactor", "create file", "add file"]):
            return False

        for pattern in QUESTION_PATTERNS:
            if re.match(pattern, clean) or clean.endswith("?"):
                return True
        return False

    def respond_to_greeting(self, sender_name: str, active_project_name: str, active_project_path: str) -> None:
        """Respond politely to greetings without launching an unintended workflow."""
        greeting_msg = (
            f"👋 Hello {sender_name}! I am **Codex**, the Engineering Lead of your multi-agent AI team "
            f"(with **Cursor** as Developer and **OpenCode** as QA Reviewer).\n\n"
            f"📁 **Active Project**: `{active_project_name}`\n"
            f"📍 **Path**: `{active_project_path}`\n\n"
            f"**Quick Commands**:\n"
            f"• `/projects` — View all projects on your PC\n"
            f"• `/use <name>` — Switch projects (e.g. `/use portfolio`)\n"
            f"• `/files` — Browse active project files\n"
            f"• `/diff` — Inspect latest code diff\n"
            f"• `/status` — View system & agent health\n"
            f"• Or send any task (e.g. *'in sample_repo: fix the PDF upload bug'* or *'in portfolio: update title'*)"
        )
        self.switch.post_to_room(self.name, greeting_msg)

    def respond_to_inquiry(self, query: str, active_project_name: str, projects_list: list) -> None:
        """Answer informational questions directly without triggering development cycles."""
        q_lower = query.lower()
        if "project" in q_lower or "access" in q_lower or "list" in q_lower:
            proj_names = ", ".join([f"`{p['name']}`" for p in projects_list[:8]])
            reply = (
                f"ℹ️ **Project Access**:\n"
                f"We currently have access to all projects in `D:\\projects`, including: {proj_names}...\n\n"
                f"• Active Project: `{active_project_name}`\n"
                f"• Type `/projects` for the full list, or `/use <name>` to switch."
            )
        elif "who are you" in q_lower or "what can you do" in q_lower or "team" in q_lower or "help" in q_lower:
            reply = (
                f"ℹ️ **About Our Team**:\n"
                f"We are an autonomous AI Software Engineering Team coordinating via Switch:\n"
                f"• **Codex** (Lead): Analyzes requests, scopes tasks, and summarizes progress.\n"
                f"• **Cursor** (Developer): Inspects code, locates bugs, and implements patches.\n"
                f"• **OpenCode** (QA): Independently reviews diffs, tests code, and validates edge cases.\n\n"
                f"You always maintain full control: no changes are pushed or committed without your explicit approval."
            )
        else:
            reply = (
                f"ℹ️ I received your inquiry: \"{query}\".\n"
                f"To have the team make code changes, tell us what to modify and which project to target.\n"
                f"Example: `in sample_repo: fix PDF upload bug` or `in portfolio: change title in index.html`."
            )
        self.switch.post_to_room(self.name, reply)

    def display_diff(self, diff: str, task_id: Optional[str] = None) -> None:
        """Display code diff in Telegram."""
        if not diff or not diff.strip():
            self.switch.post_to_room(self.name, "ℹ️ No uncommitted diffs or pending modifications found.")
            return

        header = f"🔍 **Code Diff for #{task_id}**\n\n" if task_id else "🔍 **Current Code Diff**\n\n"
        diff_snippet = diff[:1500]
        if len(diff) > 1500:
            diff_snippet += "\n... (truncated for Telegram)"
        formatted = f"{header}```diff\n{diff_snippet}\n```"
        self.switch.post_to_room(self.name, formatted)

    def display_project_files(self, project_name: str, files: List[str]) -> None:
        """Display project file explorer tree."""
        if not files:
            self.switch.post_to_room(self.name, f"📁 No source files found in `{project_name}`.")
            return

        file_list = "\n".join([f"• `{f}`" for f in files])
        msg = (
            f"📁 **Files in `{project_name}`**:\n\n"
            f"{file_list}\n\n"
            f"👉 Type `/read <filename>` to inspect any file's code (e.g. `/read upload.py`)."
        )
        self.switch.post_to_room(self.name, msg)

    def display_file_content(self, filename: str, content: str) -> None:
        """Display code of a file."""
        ext = Path(filename).suffix.lstrip(".") or "text"
        msg = f"📄 **File: `{filename}`**\n\n```{ext}\n{content}\n```"
        self.switch.post_to_room(self.name, msg)

    def display_task_history(self, tasks: List[Dict[str, Any]]) -> None:
        """Display recent task execution audit trail."""
        if not tasks:
            self.switch.post_to_room(self.name, "ℹ️ No previous task records found in audit store.")
            return

        lines = ["📜 **Recent Task Execution History**:"]
        for t in tasks[-5:]:
            status_emoji = "✅" if t.get("status") in ["completed", "approved"] else "⚠️"
            pr = t.get("pr_url") or "None"
            lines.append(
                f"{status_emoji} **#{t.get('task_id')}** [{t.get('status', 'unknown').upper()}]\n"
                f"  • Request: \"{t.get('raw_request', '')[:45]}...\"\n"
                f"  • PR: {pr}"
            )
        self.switch.post_to_room(self.name, "\n\n".join(lines))

    def analyze_task(self, raw_request: str, task_id: str, repo_path: str) -> Dict[str, Any]:
        """Stage 2: Classify request, extract requirements, and announce task creation."""
        text_lower = raw_request.lower()
        if any(w in text_lower for w in ["error", "500", "crash", "bug", "fail", "broken", "exception", "overflow"]):
            task_type = TaskType.BUG
        elif any(w in text_lower for w in ["refactor", "cleanup", "reorganize", "structure"]):
            task_type = TaskType.REFACTOR
        elif any(w in text_lower for w in ["doc", "readme", "explain"]):
            task_type = TaskType.DOCUMENTATION
        else:
            task_type = TaskType.FEATURE

        proj_name = Path(repo_path).name
        summary_msg = f"Task #{task_id} created for `{proj_name}`. Class: {task_type.value.upper()}. Investigating: '{raw_request}'."
        self.switch.post_to_room(self.name, summary_msg)

        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": TaskStatus.ANALYZED,
            "repo_path": repo_path
        }

    def delegate_investigation(self, task_id: str, raw_request: str) -> None:
        """Stage 3: Delegate repository investigation to Cursor."""
        delegate_msg = f"Delegating investigation to Cursor for Task #{task_id}: {raw_request}"
        self.switch.post_to_room(self.name, delegate_msg, target="cursor")

    def delegate_review(self, task_id: str, modified_files: list) -> None:
        """Stage 5: Coordinate with OpenCode for independent review and testing."""
        files_str = ", ".join(modified_files) if modified_files else "modified code"
        review_msg = f"OpenCode is reviewing the implementation ({files_str}) for Task #{task_id}."
        self.switch.post_to_room(self.name, review_msg, target="opencode")

    def relay_review_failure(self, task_id: str, review: ReviewReport, max_cycles: int) -> None:
        """Correction Loop: Send QA findings back to Cursor for iterative refinement."""
        nudge_msg = (
            f"OpenCode review failed on attempt {review.iteration}/{max_cycles} for Task #{task_id}. "
            f"Findings: {review.critique}. Please revise the implementation to address these issues."
        )
        self.switch.post_to_room(self.name, nudge_msg, target="cursor")

    def report_max_failures(self, task_id: str, max_cycles: int) -> None:
        """Failure Handling: Escalate to human developer when max attempts are exceeded."""
        alert_msg = (
            f"⚠️ Task #{task_id} exceeded maximum automated review attempts ({max_cycles}) "
            f"without passing QA. Halting automated loop and escalating to human developer."
        )
        self.switch.post_to_room(self.name, alert_msg)

    def request_human_approval(self, task_id: str, review_summary: str) -> None:
        """Stage 6: Prompt human developer in Telegram for explicit approval."""
        approval_msg = (
            f"Changes for Task #{task_id} are ready for your approval. "
            f"{review_summary}. No changes have been pushed to remote. "
            f"Please reply 'Approve' to proceed, or type `/diff` to inspect changes."
        )
        self.switch.post_to_room(self.name, approval_msg)

    def generate_final_report(self, state: TeamWorkflowState, pr_url: Optional[str] = None) -> str:
        """Stage 7: Summarize the complete workflow result for the human in Telegram."""
        inv = state.investigation
        imp = state.implementation
        rev = state.review
        proj_name = Path(state.repo_path).name

        report = (
            f"📋 **Task #{state.task_id} Completed Final Report**\n\n"
            f"• **Target Project**: `{proj_name}`\n"
            f"• **Original Request**: {state.raw_request}\n"
            f"• **Root Cause**: {inv.root_cause if inv else 'N/A'}\n"
            f"• **Files Modified**: {', '.join(imp.modified_files) if imp else 'N/A'}\n"
            f"• **Implementation Summary**: {imp.summary if imp else 'N/A'}\n"
            f"• **Tests Executed**: {rev.tests_executed if rev else 0} ({rev.tests_passed if rev else 0} passed)\n"
            f"• **Review Result**: {rev.verdict if rev else 'N/A'} (Completed in {state.iteration_count} iteration(s))\n"
            f"• **Approval Status**: Approved by Developer\n"
        )
        if pr_url:
            report += f"• **GitHub PR**: [{pr_url}]({pr_url})\n"
        else:
            report += "• **GitHub PR**: [Local branch ready for push]\n"

        self.switch.post_to_room(self.name, report)
        return report
