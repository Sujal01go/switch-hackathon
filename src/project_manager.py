"""Project Manager for Multi-Project Access Across PC."""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

ACTIVE_PROJECT_FILE = Path("data/active_project.json")
DEFAULT_PROJECTS_DIR = Path("D:/projects")
IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", ".next", ".cache", ".idea", ".vscode"}


class ProjectManager:
    def __init__(self, default_projects_dir: Path = DEFAULT_PROJECTS_DIR):
        self.default_projects_dir = default_projects_dir
        self.sample_repo_path = Path("sample_repo").resolve()
        self._active_project = self._load_active_project()

    def _load_active_project(self) -> Path:
        """Load previously selected project or default to sample_repo."""
        if ACTIVE_PROJECT_FILE.exists():
            try:
                data = json.loads(ACTIVE_PROJECT_FILE.read_text(encoding="utf-8"))
                saved_path = Path(data.get("path", ""))
                if "pytest" not in str(saved_path).lower() and saved_path.exists() and saved_path.is_dir():
                    return saved_path
            except Exception:
                pass
        return self.sample_repo_path

    def _save_active_project(self, project_path: Path):
        """Persist active project choice to disk."""
        ACTIVE_PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_PROJECT_FILE.write_text(
            json.dumps({"path": str(project_path.resolve()), "name": project_path.name}, indent=2),
            encoding="utf-8"
        )

    @property
    def active_project(self) -> Path:
        return self._active_project

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all discovered project directories on the PC."""
        projects = []

        # 1. Include sample_repo
        projects.append({
            "name": "sample_repo",
            "path": str(self.sample_repo_path),
            "is_active": self._active_project == self.sample_repo_path,
            "has_git": (self.sample_repo_path / ".git").exists(),
            "type": "Python (Sample Buggy Repo)"
        })

        # 2. Scan default projects dir (D:\projects)
        if self.default_projects_dir.exists():
            for p in sorted(self.default_projects_dir.iterdir(), key=lambda x: x.name.lower()):
                if p.is_dir() and not p.name.startswith("."):
                    has_git = (p / ".git").exists()
                    has_py = any(p.glob("*.py"))
                    has_js = (p / "package.json").exists()
                    tech = []
                    if has_py: tech.append("Python")
                    if has_js: tech.append("Node/JS")
                    if not tech: tech.append("General")

                    projects.append({
                        "name": p.name,
                        "path": str(p.resolve()),
                        "is_active": self._active_project.resolve() == p.resolve(),
                        "has_git": has_git,
                        "type": " / ".join(tech)
                    })

        return projects

    def set_active_project(self, identifier: str) -> Tuple[bool, str, Path]:
        """
        Switch active project by name, partial name, or absolute path.
        Returns: (success: bool, message: str, resolved_path: Path)
        """
        clean_id = identifier.strip().strip("'\"")

        # 1. Check if direct absolute or relative directory path
        direct_path = Path(clean_id)
        if direct_path.exists() and direct_path.is_dir():
            resolved = direct_path.resolve()
            self._active_project = resolved
            self._save_active_project(resolved)
            return True, f"Switched to project at `{resolved}`", resolved

        # 2. Match by exact name in D:\projects
        if self.default_projects_dir.exists():
            for p in self.default_projects_dir.iterdir():
                if p.is_dir() and p.name.lower() == clean_id.lower():
                    resolved = p.resolve()
                    self._active_project = resolved
                    self._save_active_project(resolved)
                    return True, f"Switched active project to `{p.name}`", resolved

        # 3. Match sample_repo
        if clean_id.lower() in ["sample_repo", "sample-repo", "sample"]:
            self._active_project = self.sample_repo_path
            self._save_active_project(self.sample_repo_path)
            return True, "Switched active project to `sample_repo`", self.sample_repo_path

        # 4. Partial substring match in D:\projects
        if self.default_projects_dir.exists():
            matches = [
                p for p in self.default_projects_dir.iterdir()
                if p.is_dir() and clean_id.lower() in p.name.lower()
            ]
            if len(matches) == 1:
                p = matches[0]
                resolved = p.resolve()
                self._active_project = resolved
                self._save_active_project(resolved)
                return True, f"Switched active project to `{p.name}`", resolved
            elif len(matches) > 1:
                names = ", ".join([f"`{m.name}`" for m in matches])
                return False, f"Ambiguous project name '{clean_id}'. Multiple matches: {names}", self._active_project

        return False, f"Could not find project directory `{clean_id}` on your PC.", self._active_project

    def extract_target_project_from_text(self, text: str) -> Tuple[Optional[Path], str]:
        """
        Detect if prompt specifies a project, e.g.:
        'In portfolio: change title' -> (Path('D:/projects/portfolio'), 'change title')
        'For ARS-Module fix X' -> (Path('D:/projects/ARS-Module'), 'fix X')
        """
        text_lower = text.lower()
        projects = self.list_projects()
        for p_info in projects:
            p_name = p_info["name"]
            p_path = Path(p_info["path"])

            for prefix in [f"in {p_name.lower()}:", f"in {p_name.lower()} ", f"for {p_name.lower()}:", f"project {p_name.lower()}:"]:
                if text_lower.startswith(prefix):
                    clean_req = text[len(prefix):].strip()
                    return p_path, clean_req

        return None, text

    def get_project_files_tree(self, max_files: int = 40) -> List[str]:
        """Get structured list of source files inside active project."""
        p = self._active_project
        file_tree = []
        count = 0

        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
            rel_dir = Path(root).relative_to(p)
            for f in sorted(files):
                if f.startswith(".") or f.endswith((".pyc", ".lock", ".log", ".tmp")):
                    continue
                rel_path = (rel_dir / f).as_posix()
                if rel_path == ".":
                    rel_path = f
                file_tree.append(rel_path)
                count += 1
                if count >= max_files:
                    file_tree.append(f"... (truncated, {max_files}+ files)")
                    return file_tree

        return file_tree

    def read_project_file(self, rel_path: str, max_lines: int = 150) -> Tuple[bool, str]:
        """Read a file safely within active project."""
        target = (self._active_project / rel_path).resolve()
        p_resolved = self._active_project.resolve()

        if p_resolved not in target.parents and p_resolved != target:
            return False, f"Path security error: `{rel_path}` is outside project directory."

        if not target.exists() or not target.is_file():
            return False, f"File `{rel_path}` does not exist in `{self._active_project.name}`."

        try:
            lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
            truncated = len(lines) > max_lines
            content = "\n".join(lines[:max_lines])
            if truncated:
                content += f"\n\n... (truncated at line {max_lines} of {len(lines)})"
            return True, content
        except Exception as e:
            return False, f"Error reading `{rel_path}`: {e}"

    def undo_changes(self, target_repo: Optional[Path] = None) -> Tuple[bool, str]:
        """Revert uncommitted modifications in repository."""
        repo = target_repo or self._active_project
        if not (repo / ".git").exists():
            return False, f"Project `{repo.name}` is not a git repository; cannot automatically undo."

        try:
            # Checkout modified files
            subprocess.run(["git", "-C", str(repo), "checkout", "--", "."], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "clean", "-fd"], check=True, capture_output=True)
            return True, f"Successfully reverted all working changes in `{repo.name}`."
        except Exception as e:
            return False, f"Failed to revert changes: {e}"
