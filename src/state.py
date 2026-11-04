"""Typed state schemas for the Multi-Agent Engineering Team workflow."""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TaskType(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"

class TaskStatus(str, Enum):
    SUBMITTED = "submitted"
    ANALYZED = "analyzed"
    INVESTIGATING = "investigating"
    IMPLEMENTING = "implementing"
    IN_REVIEW = "in_review"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"

class InvestigationReport(BaseModel):
    root_cause: str
    affected_files: List[str] = Field(default_factory=list)
    proposed_solution: str
    implementation_plan: List[str] = Field(default_factory=list)

class ImplementationReport(BaseModel):
    modified_files: List[str] = Field(default_factory=list)
    diff: str = ""
    summary: str = ""
    local_tests_passed: bool = False

class ReviewReport(BaseModel):
    verdict: str  # "PASS" or "FAIL"
    tests_executed: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    edge_cases: List[str] = Field(default_factory=list)
    critique: str = ""
    iteration: int = 1

class ApprovalReport(BaseModel):
    approved: bool
    responder: str = "human"
    comment: str = ""
    timestamp: str = ""

class TeamWorkflowState(BaseModel):
    """The central state passed across LangGraph nodes and persisted in SQLite."""
    task_id: str
    raw_request: str
    task_type: TaskType = TaskType.BUG
    status: TaskStatus = TaskStatus.SUBMITTED
    repo_path: str
    investigation: Optional[InvestigationReport] = None
    implementation: Optional[ImplementationReport] = None
    review: Optional[ReviewReport] = None
    approval: Optional[ApprovalReport] = None
    iteration_count: int = 1
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    simulate_initial_flaw: bool = False
    git_branch: Optional[str] = None
    pr_url: Optional[str] = None
    final_report: Optional[str] = None
    error: Optional[str] = None

