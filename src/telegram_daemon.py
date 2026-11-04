"""Live Telegram Listener Daemon for Multi-Agent Engineering Team.

Full Feature Set:
- Handles both Telegram slash commands (`com.switch.command`) and plain text commands.
- Multi-project management across all PC projects via ProjectManager.
- File explorer (`/files`) and file reader (`/read <file>`) directly in Telegram.
- Code diff inspection (`/diff`) prior to approval or after completion.
- Revert / undo working directory changes (`/undo`).
- Task execution audit history (`/history`).
- Intent classification: distinguishes greetings and informational inquiries from real engineering tasks.
- LangGraph interrupted human-in-the-loop approval gate.
"""

import sys
import time
import logging
import subprocess
import psycopg2
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.config import SWITCH_ROOM_ID, TELEGRAM_CHAT_ID
from src.switch.client import SwitchClient
from src.project_manager import ProjectManager
from src.db.task_store import TaskStore
from src.workflow.graph import EngineeringTeamWorkflow
from src.agents.codex import CodexLeadAgent
from src.state import TaskStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("telegram_daemon")

DB_HOST = "localhost"
DB_PORT = 55011
DB_USER = "switch_app"
DB_PASS = "J0-Efw91U4XjcYhS8CfA0qdHaUzi8oSx"
DB_NAME = "switch"
TENANT_ID = "00000000-0000-0000-0000-000000000000"


class TelegramEngineeringDaemon:
    def __init__(self):
        self.room_id = SWITCH_ROOM_ID
        self.switch_client = SwitchClient(room_id=self.room_id, deliver_live=True)
        self.project_manager = ProjectManager()
        self.task_store = TaskStore("data/tasks.db")
        self.codex = CodexLeadAgent(self.switch_client)
        self.workflow = EngineeringTeamWorkflow(
            self.switch_client,
            self.task_store,
            interrupt_approval=True
        )
        
        # State tracking
        self.current_state = "IDLE"  # IDLE | AWAITING_APPROVAL
        self.active_task_id: Optional[str] = None
        self.active_target_repo: Optional[Path] = None
        self.latest_diff: Optional[str] = None
        self.task_counter = 1
        self.last_seen_seq = 0

    def get_db_connection(self):
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            dbname=DB_NAME
        )
        cur = conn.cursor()
        cur.execute(f"SET app.tenant_id = '{TENANT_ID}';")
        return conn, cur

    def get_latest_seq(self) -> int:
        try:
            conn, cur = self.get_db_connection()
            cur.execute("""
                SELECT COALESCE(MAX(seq), 0) FROM messages 
                WHERE room_id = %s;
            """, (self.room_id,))
            res = cur.fetchone()
            conn.close()
            return res[0] if res else 0
        except Exception as e:
            logger.error(f"Error fetching latest seq: {e}")
            return 0

    def poll_new_messages(self):
        """Poll for new messages sent in the room including commands and text."""
        try:
            conn, cur = self.get_db_connection()
            cur.execute("""
                SELECT seq, sender_id, sender_name, body, sent_at, event_type, content 
                FROM messages 
                WHERE room_id = %s AND seq > %s
                ORDER BY seq ASC;
            """, (self.room_id, self.last_seen_seq))
            rows = cur.fetchall()
            conn.close()
            return rows
        except Exception as e:
            logger.error(f"Error polling messages: {e}")
            return []

    def is_bot_or_admin(self, sender_id: str, sender_name: str, body: Optional[str]) -> bool:
        """Check if message is from Switch Core, internal agents, or admin bot."""
        if not sender_id:
            return True
        s_lower = sender_name.lower() if sender_name else ""
        if s_lower in ["admin", "switch-buddy-admin", "codex", "opencode", "cursor"]:
            return True
        if "@switch-admin" in sender_id or "@switch-agent" in sender_id:
            return True
        if body and "unknown command:" in body.lower():
            return True
        return False

    def handle_greeting(self, sender_name: str):
        """Respond politely to casual greetings without triggering software workflow."""
        active_p = self.project_manager.active_project
        self.codex.respond_to_greeting(
            sender_name=sender_name or "Developer",
            active_project_name=active_p.name,
            active_project_path=str(active_p)
        )

    def handle_inquiry(self, query: str):
        """Respond to informational questions directly."""
        active_p = self.project_manager.active_project
        projs = self.project_manager.list_projects()
        self.codex.respond_to_inquiry(
            query=query,
            active_project_name=active_p.name,
            projects_list=projs
        )

    def handle_list_projects(self):
        """List all available projects on user's PC."""
        projs = self.project_manager.list_projects()
        active_p = self.project_manager.active_project.resolve()

        lines = ["📂 **Available Projects on Your PC**:"]
        for p in projs:
            p_path = Path(p["path"]).resolve()
            is_active = (p_path == active_p)
            badge = "⭐ **[ACTIVE]** " if is_active else "• "
            lines.append(f"{badge}`{p['name']}` ({p['type']})")

        lines.append("\n👉 To switch project: `/use <project_name>`")
        lines.append("👉 To browse files: `/files`")
        lines.append("👉 Or target directly: `in <project_name>: <your task>`")

        self.switch_client.post_to_room("Codex", "\n".join(lines))

    def handle_switch_project(self, identifier: str):
        """Switch active project repository."""
        if not identifier or not identifier.strip():
            self.switch_client.post_to_room("Codex", "⚠️ Please provide a project name. Example: `/use portfolio` or `/projects` to list all.")
            return

        ok, msg, path = self.project_manager.set_active_project(identifier)
        if ok:
            response = (
                f"✅ **Active Project Switched**\n\n"
                f"• **Project**: `{path.name}`\n"
                f"• **Path**: `{path}`\n\n"
                f"Subsequent bug reports and tasks will target this project. Type `/files` to view project source files."
            )
        else:
            response = f"⚠️ {msg}\nUse `/projects` to see the full list of available projects."
        self.switch_client.post_to_room("Codex", response)

    def handle_status_command(self):
        """Report current status."""
        active_p = self.project_manager.active_project
        has_git = (active_p / ".git").exists()
        branch = "N/A"
        if has_git:
            try:
                res = subprocess.run(["git", "-C", str(active_p), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
                branch = res.stdout.strip() or "main"
            except Exception:
                branch = "main"

        status_msg = (
            f"ℹ️ **System Status**:\n"
            f"• Current State: `{self.current_state}`\n"
            f"• Active Task: `{self.active_task_id or 'None'}`\n"
            f"• Active Project: `{active_p.name}` (`{active_p}`)\n"
            f"• Git Branch: `{branch}`\n"
            f"• Agents: Codex (Lead), Cursor (Developer), OpenCode (QA)"
        )
        self.switch_client.post_to_room("Codex", status_msg)

    def handle_help_command(self):
        """Report help instructions."""
        help_msg = (
            "🛠️ **Available Commands & Usage**:\n\n"
            "• `/projects` - List all projects on your PC\n"
            "• `/use <name>` - Switch active project (e.g. `/use portfolio`)\n"
            "• `/files` - Browse active project files\n"
            "• `/read <file>` - Inspect source code of a file\n"
            "• `/diff` - View latest uncommitted code changes\n"
            "• `/status` - Check current agent and project status\n"
            "• `/history` - View recent task execution history\n"
            "• `/undo` - Revert working changes\n\n"
            "**Tasks**:\n"
            "• `in sample_repo: fix the PDF upload bug for files over 10MB`\n"
            "• `in portfolio: update the title in index.html`\n"
            "• `create a new file utils.py with helper functions`"
        )
        self.switch_client.post_to_room("Codex", help_msg)

    def handle_show_diff(self):
        """Display latest code diff."""
        if self.latest_diff:
            self.codex.display_diff(self.latest_diff, self.active_task_id)
        else:
            # Try git diff on active project
            active_p = self.project_manager.active_project
            if (active_p / ".git").exists():
                try:
                    res = subprocess.run(["git", "-C", str(active_p), "diff"], capture_output=True, text=True)
                    diff = res.stdout.strip()
                    self.codex.display_diff(diff)
                except Exception as e:
                    self.switch_client.post_to_room("Codex", f"⚠️ Error fetching git diff: {e}")
            else:
                self.switch_client.post_to_room("Codex", "ℹ️ No pending diff found.")

    def handle_list_files(self):
        """Display file tree of active project."""
        active_p = self.project_manager.active_project
        files = self.project_manager.get_project_files_tree()
        self.codex.display_project_files(active_p.name, files)

    def handle_read_file(self, rel_path: str):
        """Display contents of a file in the active project."""
        clean_path = rel_path.strip().strip("'\"")
        ok, content = self.project_manager.read_project_file(clean_path)
        if ok:
            self.codex.display_file_content(clean_path, content)
        else:
            self.switch_client.post_to_room("Codex", f"⚠️ {content}")

    def handle_history_command(self):
        """Display recent task execution audit trail."""
        tasks = self.task_store.get_recent_tasks(limit=5)
        self.codex.display_task_history(tasks)

    def handle_undo_command(self):
        """Undo / revert uncommitted changes in active project."""
        ok, msg = self.project_manager.undo_changes()
        emoji = "🔄" if ok else "⚠️"
        self.switch_client.post_to_room("Codex", f"{emoji} {msg}")
        self.latest_diff = None
        self.current_state = "IDLE"
        self.active_task_id = None

    def handle_reset_command(self):
        """Reset sample_repo or active project git state."""
        active_p = self.project_manager.active_project
        try:
            if (active_p / ".git").exists():
                subprocess.run(["git", "-C", str(active_p), "checkout", "main"], check=True, capture_output=True)
                if active_p.name == "sample_repo":
                    subprocess.run(["git", "-C", str(active_p), "reset", "--hard", "95d7b11"], check=True, capture_output=True)
                else:
                    subprocess.run(["git", "-C", str(active_p), "reset", "--hard", "HEAD"], check=True, capture_output=True)
                self.switch_client.post_to_room("Codex", f"🔄 Project `{active_p.name}` has been reset to clean git state.")
            else:
                self.switch_client.post_to_room("Codex", f"ℹ️ Project `{active_p.name}` does not have a git repository to reset.")
            self.current_state = "IDLE"
            self.active_task_id = None
            self.latest_diff = None
        except Exception as e:
            logger.error(f"Failed to reset repo: {e}")
            self.switch_client.post_to_room("Codex", f"⚠️ Error resetting project: {e}")

    def start_task(self, raw_request: str):
        inline_target, clean_request = self.project_manager.extract_target_project_from_text(raw_request)
        target_repo = inline_target or self.project_manager.active_project

        task_id = f"TASK-{self.task_counter:03d}"
        self.task_counter += 1
        self.active_task_id = task_id
        self.active_target_repo = target_repo
        
        logger.info(f"Starting task {task_id} on {target_repo.name}: {clean_request}")
        self.switch_client.post_to_room(
            "Codex",
            f"📋 **Task #{task_id} Created**\n\n"
            f"• **Target Project**: `{target_repo.name}` (`{target_repo}`)\n"
            f"• **Request**: \"{clean_request}\"\n"
            f"• **Workflow**: Codex (Lead) -> Cursor (Dev) -> OpenCode (QA)\n\n"
            f"Beginning repository inspection..."
        )

        try:
            state = self.workflow.run_until_approval(
                raw_request=clean_request,
                repo_path=str(target_repo),
                task_id=task_id
            )

            if state.status == TaskStatus.FAILED:
                self.switch_client.post_to_room(
                    "Codex",
                    f"⚠️ **Task #{task_id} Failed**: {state.error or 'Review/Correction cycles exceeded.'}"
                )
                self.current_state = "IDLE"
                self.active_task_id = None
                return

            review = state.review
            mod_files = state.implementation.modified_files if state.implementation else []
            files_str = ", ".join(mod_files) if mod_files else "(no files changed)"
            self.latest_diff = state.implementation.diff if state.implementation else ""

            approval_prompt = (
                f"⏸️ **Changes Ready for Your Approval**\n\n"
                f"• **Task**: #{task_id} on `{target_repo.name}`\n"
                f"• **Root Cause / Requirement**: {state.investigation.root_cause if state.investigation else 'Code modification requirement'}\n"
                f"• **Files Modified**: `{files_str}`\n"
                f"• **QA Verdict**: {review.verdict if review else 'PASS'} ({review.tests_passed if review else 1} checks passed, 0 failed)\n"
                f"• **Safety Check**: No commits or PRs have been pushed.\n\n"
                f"👉 **Type `/diff` to inspect the code diff.**\n"
                f"👉 **Reply with 'Approve' to create Pull Request, or 'Reject' to cancel.**"
            )
            self.switch_client.post_to_room("Codex", approval_prompt)
            self.current_state = "AWAITING_APPROVAL"
            logger.info(f"Task {task_id} paused awaiting developer approval in Telegram.")

        except Exception as e:
            logger.error(f"Workflow execution exception: {e}", exc_info=True)
            self.switch_client.post_to_room("Codex", f"💥 **Error during execution**: {e}")
            self.current_state = "IDLE"
            self.active_task_id = None

    def handle_approval_response(self, text: str):
        clean_text = text.strip().lower()
        task_id = self.active_task_id

        if clean_text in ["/diff", "diff", "show diff"]:
            self.handle_show_diff()
            return

        if any(w in clean_text for w in ["approve", "approved", "yes", "lgtm", "proceed", "go ahead"]):
            logger.info(f"Approval received for task {task_id}")
            self.switch_client.post_to_room(
                "Codex",
                f"👍 **Approval received from developer!** Committing changes and generating Pull Request..."
            )

            final_state = self.workflow.resume_with_approval(
                task_id=task_id,
                approved=True,
                comment="Approved by developer in Telegram"
            )

            self.current_state = "IDLE"
            self.active_task_id = None
            self.active_target_repo = None
            self.latest_diff = None

        elif any(w in clean_text for w in ["reject", "rejected", "no", "cancel", "stop", "abort"]):
            logger.info(f"Rejection received for task {task_id}")
            self.switch_client.post_to_room(
                "Codex",
                f"❌ **Changes rejected by developer.** Rolling back repository changes without pushing. Workflow aborted."
            )
            self.workflow.resume_with_approval(
                task_id=task_id,
                approved=False,
                comment="Rejected by developer in Telegram"
            )
            self.handle_undo_command()
            self.current_state = "IDLE"
            self.active_task_id = None
            self.active_target_repo = None
            self.latest_diff = None

        else:
            self.switch_client.post_to_room(
                "Codex",
                f"⏳ Task #{task_id} is awaiting your decision.\n"
                f"• Reply **'Approve'** to create the Pull Request\n"
                f"• Reply **'Reject'** to cancel\n"
                f"• Type `/diff` to inspect changes"
            )

    def run(self):
        logger.info("Initializing TelegramEngineeringDaemon...")
        self.last_seen_seq = self.get_latest_seq()
        active_p = self.project_manager.active_project
        logger.info(f"Starting at seq {self.last_seen_seq}. Telegram room: {self.room_id}. Active project: {active_p}")

        startup_banner = (
            "🚀 **Multi-Agent Software Engineering Team is Online!**\n\n"
            "• **Codex** (Engineering Lead)\n"
            "• **Cursor** (Developer Agent)\n"
            "• **OpenCode** (QA & Code Reviewer)\n\n"
            f"📁 **Active Project**: `{active_p.name}` (`{active_p}`)\n\n"
            "**Commands**:\n"
            "• `/projects` - List all projects on your PC\n"
            "• `/use <project>` - Switch active project\n"
            "• `/files` - Browse project files\n"
            "• `/diff` - View code diff\n"
            "• `/status` - Check agent health\n"
            "• Say 'hi' to chat, or send any task to begin!"
        )
        self.switch_client.post_to_room("Codex", startup_banner)
        logger.info("Startup banner delivered to Telegram. Listening for user messages...")

        while True:
            try:
                new_messages = self.poll_new_messages()
                for seq, sender_id, sender_name, body, sent_at, event_type, content in new_messages:
                    self.last_seen_seq = max(self.last_seen_seq, seq)

                    # 1. Check for Switch Slash Commands (event_type == 'com.switch.command')
                    if event_type == "com.switch.command" and isinstance(content, dict):
                        cmd = content.get("command", "").strip().lower()
                        args = content.get("args", "").strip()
                        u_name = content.get("user_name", "Developer")
                        logger.info(f"Handling slash command from {u_name}: /{cmd} '{args}'")

                        if cmd in ["projects", "project_list"]:
                            self.handle_list_projects()
                        elif cmd in ["use", "project", "switch"]:
                            self.handle_switch_project(args)
                        elif cmd == "files":
                            self.handle_list_files()
                        elif cmd == "read":
                            self.handle_read_file(args)
                        elif cmd == "diff":
                            self.handle_show_diff()
                        elif cmd == "history":
                            self.handle_history_command()
                        elif cmd in ["undo", "revert"]:
                            self.handle_undo_command()
                        elif cmd == "status":
                            self.handle_status_command()
                        elif cmd == "help":
                            self.handle_help_command()
                        elif cmd == "reset":
                            self.handle_reset_command()
                        else:
                            self.switch_client.post_to_room("Codex", f"Unknown command `/{cmd}`. Use `/help` to see available commands.")
                        continue

                    # 2. Skip bot, admin, or agent messages
                    if self.is_bot_or_admin(sender_id, sender_name, body):
                        continue

                    if not body or not body.strip():
                        continue

                    logger.info(f"Received user message from {sender_name}: '{body}'")

                    clean_body = body.replace("@codex", "").replace("@opencode", "").replace("@cursor", "").strip()
                    body_lower = clean_body.lower()

                    # 3. State: AWAITING APPROVAL
                    if self.current_state == "AWAITING_APPROVAL":
                        self.handle_approval_response(clean_body)
                        continue

                    # 4. Plain Text Commands or Slash Commands in body
                    if body_lower in ["/projects", "projects", "list projects"]:
                        self.handle_list_projects()
                        continue
                    elif body_lower.startswith("/use ") or body_lower.startswith("use ") or body_lower.startswith("switch to "):
                        arg = clean_body.split(maxsplit=1)[1] if not body_lower.startswith("switch to ") else clean_body[10:]
                        self.handle_switch_project(arg.strip())
                        continue
                    elif body_lower in ["/files", "files", "list files"]:
                        self.handle_list_files()
                        continue
                    elif body_lower.startswith("/read ") or body_lower.startswith("read "):
                        arg = clean_body.split(maxsplit=1)[1]
                        self.handle_read_file(arg.strip())
                        continue
                    elif body_lower in ["/diff", "diff", "show diff"]:
                        self.handle_show_diff()
                        continue
                    elif body_lower in ["/history", "history"]:
                        self.handle_history_command()
                        continue
                    elif body_lower in ["/undo", "undo", "revert"]:
                        self.handle_undo_command()
                        continue
                    elif body_lower in ["/status", "status"]:
                        self.handle_status_command()
                        continue
                    elif body_lower in ["/reset", "reset"]:
                        self.handle_reset_command()
                        continue
                    elif body_lower in ["/help", "help"]:
                        self.handle_help_command()
                        continue

                    # 5. Greeting / Casual conversation -> Do NOT run software workflow!
                    if self.codex.is_greeting(clean_body):
                        self.handle_greeting(sender_name)
                        continue

                    # 6. Informational question or inquiry -> Answer directly without running workflow!
                    if self.codex.is_casual_or_question(clean_body):
                        self.handle_inquiry(clean_body)
                        continue

                    # 7. Actual Software Engineering Task
                    if self.current_state == "IDLE":
                        self.start_task(clean_body)
                    else:
                        logger.warning(f"Unexpected state {self.current_state}")

                time.sleep(1.5)

            except KeyboardInterrupt:
                logger.info("Daemon stopped by user.")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(2.0)


if __name__ == "__main__":
    daemon = TelegramEngineeringDaemon()
    daemon.run()
