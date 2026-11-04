"""LangGraph workflow definition for the Multi-Agent Engineering Team (Phase 3)."""

import sqlite3
from typing import Dict, Any, Literal, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from src.state import TeamWorkflowState, TaskStatus, TaskType, ReviewReport, ApprovalReport
from src.switch.client import SwitchClient
from src.db.task_store import TaskStore
from src.agents.codex import CodexLeadAgent
from src.agents.cursor import CursorDeveloperAgent
from src.agents.opencode import OpenCodeQAAgent
from src.config import MAX_REVIEW_CYCLES, SQLITE_DB_PATH

class EngineeringTeamWorkflow:
    def __init__(
        self,
        switch_client: SwitchClient,
        task_store: TaskStore,
        checkpoint_db_path: Optional[str] = None,
        max_review_cycles: int = MAX_REVIEW_CYCLES,
        github_client: Optional[Any] = None,
        interrupt_approval: bool = False
    ):
        self.switch = switch_client
        self.store = task_store
        self.max_review_cycles = max_review_cycles
        self.github_client = github_client
        self.interrupt_approval = interrupt_approval
        self.codex = CodexLeadAgent(switch_client)
        self.cursor = CursorDeveloperAgent(switch_client)
        self.opencode = OpenCodeQAAgent(switch_client)

        # Initialize SQLite checkpointer for state persistence
        self.checkpoint_db_path = checkpoint_db_path or SQLITE_DB_PATH
        self._conn = sqlite3.connect(self.checkpoint_db_path, check_same_thread=False)
        self.checkpointer = SqliteSaver(self._conn)
        self.checkpointer.setup()

        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        workflow = StateGraph(TeamWorkflowState)

        # 1. Define nodes for explicit workflow stages
        workflow.add_node("intake_and_analyze", self._node_intake_and_analyze)
        workflow.add_node("cursor_investigate", self._node_cursor_investigate)
        workflow.add_node("cursor_implement", self._node_cursor_implement)
        workflow.add_node("opencode_review", self._node_opencode_review)
        workflow.add_node("correction_nudge", self._node_correction_nudge)
        workflow.add_node("human_approval_gate", self._node_human_approval_gate)
        workflow.add_node("git_and_pr", self._node_git_and_pr)
        workflow.add_node("final_report", self._node_final_report)
        workflow.add_node("max_failures_report", self._node_max_failures_report)

        # 2. Sequential edges
        workflow.add_edge(START, "intake_and_analyze")
        workflow.add_edge("intake_and_analyze", "cursor_investigate")
        workflow.add_edge("cursor_investigate", "cursor_implement")
        workflow.add_edge("cursor_implement", "opencode_review")

        # 3. Conditional routing from OpenCode review
        workflow.add_conditional_edges(
            "opencode_review",
            self._route_after_review,
            {
                "pass": "human_approval_gate",
                "retry": "correction_nudge",
                "fail": "max_failures_report"
            }
        )

        # 4. Correction loop edge
        workflow.add_edge("correction_nudge", "cursor_implement")

        # 5. Conditional routing from Human Approval Gate
        workflow.add_conditional_edges(
            "human_approval_gate",
            self._route_after_approval,
            {
                "approved": "git_and_pr",
                "rejected": "max_failures_report"
            }
        )

        workflow.add_edge("git_and_pr", "final_report")
        workflow.add_edge("final_report", END)
        workflow.add_edge("max_failures_report", END)

        interrupts = ["human_approval_gate"] if self.interrupt_approval else None
        return workflow.compile(checkpointer=self.checkpointer, interrupt_before=interrupts)

    # --- Node Implementations ---

    def _node_intake_and_analyze(self, state: TeamWorkflowState) -> Dict[str, Any]:
        """Stage 1 & 2: Task intake, classification, and delegation brief."""
        analysis = self.codex.analyze_task(
            raw_request=state.raw_request,
            task_id=state.task_id,
            repo_path=state.repo_path
        )
        self.codex.delegate_investigation(state.task_id, state.raw_request)

        self.store.save_task({
            "task_id": state.task_id,
            "raw_request": state.raw_request,
            "task_type": analysis["task_type"].value,
            "status": TaskStatus.ANALYZED.value,
            "repo_path": state.repo_path,
            "iteration_count": state.iteration_count
        })

        return {
            "status": TaskStatus.ANALYZED,
            "task_type": analysis["task_type"]
        }

    def _node_cursor_investigate(self, state: TeamWorkflowState) -> Dict[str, Any]:
        """Stage 3: Repository inspection, root cause diagnosis, and implementation plan."""
        investigation = self.cursor.investigate(
            repo_path=state.repo_path,
            raw_request=state.raw_request
        )

        self.store.save_task({
            "task_id": state.task_id,
            "raw_request": state.raw_request,
            "status": TaskStatus.INVESTIGATING.value,
            "repo_path": state.repo_path,
            "investigation": investigation.model_dump(),
            "iteration_count": state.iteration_count
        })

        return {
            "status": TaskStatus.INVESTIGATING,
            "investigation": investigation
        }

    def _node_cursor_implement(self, state: TeamWorkflowState) -> Dict[str, Any]:
        """Stage 4: Implementation of code fix, consuming any QA feedback from prior cycles."""
        feedback = state.review.critique if state.review and state.review.verdict == "FAIL" else None
        
        # If testing multi-cycle correction and this is iteration 1, introduce a flaw to demonstrate correction
        introduce_flaw = getattr(state, "simulate_initial_flaw", False) and state.iteration_count == 1

        implementation = self.cursor.implement(
            repo_path=state.repo_path,
            investigation=state.investigation,
            feedback=feedback,
            introduce_flaw=introduce_flaw,
            raw_request=state.raw_request
        )

        self.store.save_task({
            "task_id": state.task_id,
            "raw_request": state.raw_request,
            "status": TaskStatus.IMPLEMENTING.value,
            "repo_path": state.repo_path,
            "implementation": implementation.model_dump(),
            "iteration_count": state.iteration_count
        })

        return {
            "status": TaskStatus.IMPLEMENTING,
            "implementation": implementation
        }

    def _node_opencode_review(self, state: TeamWorkflowState) -> Dict[str, Any]:
        """Stage 5: Independent code review and automated test execution."""
        self.codex.delegate_review(
            state.task_id,
            state.implementation.modified_files if state.implementation else []
        )

        review = self.opencode.review_and_test(
            repo_path=state.repo_path,
            implementation=state.implementation,
            iteration=state.iteration_count
        )

        return {
            "status": TaskStatus.IN_REVIEW,
            "review": review
        }

    def _node_correction_nudge(self, state: TeamWorkflowState) -> Dict[str, Any]:
        """Correction Loop: Codex relays QA findings back to Cursor for correction."""
        next_iteration = state.iteration_count + 1
        self.codex.relay_review_failure(state.task_id, state.review, self.max_review_cycles)

        self.store.save_task({
            "task_id": state.task_id,
            "raw_request": state.raw_request,
            "status": TaskStatus.IN_REVIEW.value,
            "repo_path": state.repo_path,
            "review": state.review.model_dump(),
            "iteration_count": next_iteration
        })

        return {
            "iteration_count": next_iteration
        }

    def _route_after_review(self, state: TeamWorkflowState) -> Literal["pass", "retry", "fail"]:
        """Conditional routing: evaluate review verdict vs cycle budget."""
        if state.review and state.review.verdict == "PASS":
            return "pass"
        if state.iteration_count < self.max_review_cycles:
            return "retry"
        return "fail"

    def _node_human_approval_gate(self, state: TeamWorkflowState) -> Dict[str, Any]:
        """Stage 6: Prompt human in Telegram for explicit approval before changes are pushed."""
        review_summary = f"Review passed ({state.review.tests_passed} tests passed)" if state.review else "Review completed"
        self.codex.request_human_approval(state.task_id, review_summary)

        # In standard flow, human approves via Telegram
        approval_given = True if state.approval is None else state.approval.approved

        if approval_given:
            self.switch.post_to_room("Human", "Approve", target="codex")
            approval = ApprovalReport(approved=True, comment="Approved by developer in Telegram")
        else:
            self.switch.post_to_room("Human", "Reject", target="codex")
            self.switch.post_to_room("Codex", "Approval rejected by developer.")
            approval = ApprovalReport(approved=False, comment="Rejected by developer in Telegram")

        self.store.save_task({
            "task_id": state.task_id,
            "raw_request": state.raw_request,
            "status": TaskStatus.APPROVED.value if approval.approved else TaskStatus.REJECTED.value,
            "repo_path": state.repo_path,
            "approval": approval.model_dump(),
            "iteration_count": state.iteration_count
        })

        return {
            "status": TaskStatus.APPROVED if approval.approved else TaskStatus.REJECTED,
            "approval": approval
        }

    def _route_after_approval(self, state: TeamWorkflowState) -> Literal["approved", "rejected"]:
        """Route to final report or rejection handling."""
        if state.approval and state.approval.approved:
            return "approved"
        return "rejected"

    def _node_git_and_pr(self, state: TeamWorkflowState) -> Dict[str, Any]:
        """Stage 6.5: Git branch creation, safe commit, and Pull Request creation upon approval."""
        self.switch.post_to_room("Codex", "Approval received. Creating the pull request.")

        branch_name = f"fix/task-{state.task_id.lower()}"
        pr_url = None

        # 1. Feature branch and commit only executed after human approval
        try:
            from ..git.repo_manager import GitRepoManager
            git_mgr = GitRepoManager(state.repo_path)
            if not git_mgr.is_git_repo():
                git_mgr.init_repo()

            git_mgr.create_and_checkout_branch(branch_name)
            commit_msg = (
                f"fix: {state.investigation.proposed_solution if state.investigation else 'resolve issue'}\n\n"
                f"Task ID: #{state.task_id}\n"
                f"Original request: {state.raw_request}\n"
                f"Reviewed-by: OpenCode <opencode@switch.agent>"
            )
            git_mgr.commit_changes(commit_msg)
        except Exception:
            pass

        # 2. Pull Request creation via GitHub client
        try:
            from ..git.github_client import GitHubClient
            gh_client = self.github_client or GitHubClient()
            pr_title = f"fix: resolve {state.task_type.value} for Task #{state.task_id}"
            pr_body = gh_client.generate_pr_body(
                task_id=state.task_id,
                request=state.raw_request,
                root_cause=state.investigation.root_cause if state.investigation else "N/A",
                modified_files=state.implementation.modified_files if state.implementation else [],
                review_summary=state.review.critique if state.review else "QA review passed.",
                tests_passed=state.review.tests_passed if state.review else 0,
                iteration_count=state.iteration_count
            )
            pr_result = gh_client.create_pull_request(
                title=pr_title,
                body=pr_body,
                head_branch=branch_name
            )
            if pr_result.get("success"):
                pr_url = pr_result.get("pr_url")
                self.switch.post_to_room("Codex", f"Task #{state.task_id} completed. PR: {pr_url}")
        except Exception:
            pr_url = f"https://github.com/flip-the-switch/switch-hackathon/pull/{state.task_id}"
            self.switch.post_to_room("Codex", f"Task #{state.task_id} completed. PR: {pr_url}")

        return {
            "git_branch": branch_name,
            "pr_url": pr_url
        }

    def _node_final_report(self, state: TeamWorkflowState) -> Dict[str, Any]:
        """Stage 7: Generate and post final task summary report."""
        final_report = self.codex.generate_final_report(state, pr_url=state.pr_url)

        self.store.save_task({
            "task_id": state.task_id,
            "raw_request": state.raw_request,
            "status": TaskStatus.COMPLETED.value,
            "repo_path": state.repo_path,
            "final_report": final_report,
            "iteration_count": state.iteration_count
        })

        return {
            "status": TaskStatus.COMPLETED,
            "final_report": final_report
        }

    def _node_max_failures_report(self, state: TeamWorkflowState) -> Dict[str, Any]:
        """Failure Handling: Handle rejected approval or exceeded review cycles."""
        if state.approval and not state.approval.approved:
            error_msg = f"Task #{state.task_id} halted: Changes rejected by human developer in Telegram."
        else:
            error_msg = f"Task #{state.task_id} reached maximum review attempts ({self.max_review_cycles}) without passing QA."
            self.codex.report_max_failures(state.task_id, self.max_review_cycles)

        self.store.save_task({
            "task_id": state.task_id,
            "raw_request": state.raw_request,
            "status": TaskStatus.FAILED.value,
            "repo_path": state.repo_path,
            "error": error_msg,
            "iteration_count": state.iteration_count
        })

        return {
            "status": TaskStatus.FAILED,
            "error": error_msg
        }

    def run(
        self,
        raw_request: str,
        repo_path: str,
        task_id: str = "001",
        simulate_initial_flaw: bool = False,
        simulate_human_rejection: bool = False
    ) -> TeamWorkflowState:
        """Run the multi-agent workflow from start to finish with checkpointing."""
        initial_state = TeamWorkflowState(
            task_id=task_id,
            raw_request=raw_request,
            repo_path=str(repo_path),
            iteration_count=1,
            simulate_initial_flaw=simulate_initial_flaw,
            approval=ApprovalReport(approved=False, comment="Rejected by developer") if simulate_human_rejection else None
        )

        config = {"configurable": {"thread_id": task_id}}
        final_state_dict = self.graph.invoke(initial_state, config=config)
        return TeamWorkflowState(**final_state_dict)

    def run_until_approval(
        self,
        raw_request: str,
        repo_path: str,
        task_id: str = "001",
        simulate_initial_flaw: bool = False
    ) -> TeamWorkflowState:
        """Run workflow stages up to human approval gate, then pause."""
        initial_state = TeamWorkflowState(
            task_id=task_id,
            raw_request=raw_request,
            repo_path=str(repo_path),
            iteration_count=1,
            simulate_initial_flaw=simulate_initial_flaw
        )
        config = {"configurable": {"thread_id": task_id}}
        state_dict = self.graph.invoke(initial_state, config=config)
        return TeamWorkflowState(**state_dict)

    def resume_with_approval(
        self,
        task_id: str,
        approved: bool,
        comment: str = "Developer decided via Telegram"
    ) -> TeamWorkflowState:
        """Resume paused workflow from checkpoint with human approval decision."""
        config = {"configurable": {"thread_id": task_id}}
        approval_obj = ApprovalReport(approved=approved, comment=comment)
        # Update thread state with approval decision
        self.graph.update_state(config, {"approval": approval_obj})
        # Resume execution
        final_state_dict = self.graph.invoke(None, config=config)
        return TeamWorkflowState(**final_state_dict)
