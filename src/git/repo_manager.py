"""Git repository manager for repository inspection, diff generation, and safe commits."""

import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

class GitRepoManager:
    """Manages Git operations strictly confined to a specified repository directory."""

    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {self.repo_path}")

    def _run_git(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run a git command strictly within repo_path."""
        return subprocess.run(
            ["git", "-C", str(self.repo_path)] + args,
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )

    def is_git_repo(self) -> bool:
        """Check if repo_path is inside a git working tree."""
        proc = self._run_git(["rev-parse", "--is-inside-work-tree"])
        return proc.returncode == 0 and proc.stdout.strip() == "true"

    def init_repo(self, default_branch: str = "main") -> bool:
        """Initialize git repository if not already initialized, setting baseline commit."""
        if self.is_git_repo():
            return True

        init_proc = self._run_git(["init", "-b", default_branch])
        if init_proc.returncode != 0:
            # Fallback for older git without -b flag
            self._run_git(["init"])
            self._run_git(["checkout", "-b", default_branch])

        # Configure local git identity if not configured
        self._run_git(["config", "user.name", "Switch Multi-Agent Team"])
        self._run_git(["config", "user.email", "agents@switch.local"])

        # Stage and commit baseline files
        self._run_git(["add", "."])
        self._run_git(["commit", "-m", "chore: initial baseline commit"])
        return True

    def get_status(self) -> Dict[str, Any]:
        """Inspect repository status for modified, untracked, or staged files."""
        proc = self._run_git(["status", "--porcelain"])
        if proc.returncode != 0:
            return {"is_clean": False, "files": [], "error": proc.stderr.strip()}

        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        modified = []
        untracked = []
        for line in lines:
            status_code = line[:2]
            filename = line[3:].strip()
            if status_code.startswith("??"):
                untracked.append(filename)
            else:
                modified.append(filename)

        return {
            "is_clean": len(lines) == 0,
            "modified": modified,
            "untracked": untracked,
            "total_changes": len(lines)
        }

    def get_diff(self, cached: bool = False) -> str:
        """Generate unified git diff."""
        args = ["diff"]
        if cached:
            args.append("--cached")
        proc = self._run_git(args)
        return proc.stdout

    def create_and_checkout_branch(self, branch_name: str) -> bool:
        """Create and checkout an isolated feature branch."""
        # Sanitize branch name
        safe_branch = "".join(c if c.isalnum() or c in ("-", "_", "/") else "-" for c in branch_name)
        proc = self._run_git(["checkout", "-b", safe_branch])
        if proc.returncode != 0:
            # If branch already exists, simply checkout
            proc = self._run_git(["checkout", safe_branch])
        return proc.returncode == 0

    def commit_changes(self, message: str, files: Optional[List[str]] = None) -> Optional[str]:
        """Stage modified files and commit with provided message.
        
        CRITICAL SAFETY: Only executes after explicit human approval in workflow.
        """
        # Ensure identity is configured
        self._run_git(["config", "user.name", "Cursor AI (Switch)"])
        self._run_git(["config", "user.email", "cursor@switch.agent"])

        if files:
            for f in files:
                self._run_git(["add", f])
        else:
            self._run_git(["add", "-u"])

        proc = self._run_git(["commit", "-m", message])
        if proc.returncode != 0:
            return None

        # Return latest commit hash
        hash_proc = self._run_git(["rev-parse", "HEAD"])
        return hash_proc.stdout.strip() if hash_proc.returncode == 0 else "unknown"

    def get_current_branch(self) -> str:
        """Get currently active branch name."""
        proc = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        return proc.stdout.strip() if proc.returncode == 0 else "unknown"

    def get_recent_commits(self, limit: int = 5) -> List[Dict[str, str]]:
        """Get list of recent commits with hash, author, and message."""
        proc = self._run_git(["log", f"-n{limit}", "--pretty=format:%h|%an|%s"])
        if proc.returncode != 0:
            return []
        commits = []
        for line in proc.stdout.splitlines():
            if "|" in line:
                parts = line.split("|", 2)
                if len(parts) == 3:
                    commits.append({"sha": parts[0], "author": parts[1], "subject": parts[2]})
        return commits

    def inspect_repository(self) -> Dict[str, Any]:
        """Perform comprehensive repository inspection: branch, status, recent commits, and file tree."""
        is_git = self.is_git_repo()
        status = self.get_status() if is_git else {"is_clean": True, "modified": [], "untracked": []}
        branch = self.get_current_branch() if is_git else "non-git"
        commits = self.get_recent_commits(3) if is_git else []
        python_files = sorted([f.name for f in self.repo_path.glob("*.py")])

        return {
            "repo_path": str(self.repo_path),
            "is_git": is_git,
            "branch": branch,
            "status": status,
            "recent_commits": commits,
            "python_files": python_files
        }

