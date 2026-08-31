import os
import re
import tempfile
import shutil
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

try:
    import git
except ImportError:
    git = None

@dataclass
class FileChange:
    file_path: str
    change_type: str
    diff: str
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    additions: int = 0
    deletions: int = 0

@dataclass
class DiffInfo:
    source: str
    target: str
    changes: List[FileChange]
    total_additions: int = 0
    total_deletions: int = 0
    commit_message: Optional[str] = None
    author: Optional[str] = None

class GitService:
    def __init__(self, work_dir: Optional[str] = None):
        self.work_dir = work_dir or tempfile.gettempdir()
        self._repos: Dict[str, str] = {}

    def clone_repo(self, repo_url: str, branch: Optional[str] = None) -> str:
        if not git:
            raise RuntimeError("GitPython is not installed")
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        local_path = os.path.join(self.work_dir, f"repo_{repo_name}_{os.urandom(4).hex()}")
        try:
            clone_options = {'depth': 50}
            if branch and branch.upper() != 'HEAD':
                clone_options['branch'] = branch
            repo = git.Repo.clone_from(repo_url, local_path, **clone_options)
            self._repos[repo_url] = local_path
            return local_path
        except Exception as e:
            if os.path.exists(local_path):
                shutil.rmtree(local_path)
            raise RuntimeError(f"Failed to clone repository: {str(e)}")

    def get_pr_diff(self, repo_url: str, pr_number: int, token: Optional[str] = None) -> DiffInfo:
        if 'github.com' in repo_url:
            return self._get_github_pr_diff(repo_url, pr_number, token)
        local_path = self.clone_repo(repo_url)
        repo = git.Repo(local_path)
        try:
            repo.git.fetch('origin', f'pull/{pr_number}/head:pr_{pr_number}')
            repo.git.checkout(f'pr_{pr_number}')
            base = repo.git.merge_base('HEAD', 'origin/main').strip()
            diff_text = repo.git.diff(base, 'HEAD')
            return self._parse_diff(diff_text, source=f"PR #{pr_number}", target=repo_url)
        except Exception as e:
            raise RuntimeError(f"Failed to get PR diff: {str(e)}")
        finally:
            if local_path in self._repos.values():
                shutil.rmtree(local_path, ignore_errors=True)

    def _get_github_pr_diff(self, repo_url: str, pr_number: int, token: Optional[str]) -> DiffInfo:
        import httpx
        parts = repo_url.replace('https://github.com/', '').replace('.git', '').split('/')
        owner, repo = parts[0], parts[1]
        headers = {"Accept": "application/vnd.github.v3.diff"}
        if token:
            headers["Authorization"] = f"token {token}"
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        try:
            pr_resp = httpx.get(url, headers={**headers, "Accept": "application/vnd.github.v3+json"})
            pr_data = pr_resp.json()
            diff_resp = httpx.get(url, headers=headers)
            diff_text = diff_resp.text
            diff_info = self._parse_diff(diff_text, source=f"PR #{pr_number}", target=repo_url)
            diff_info.commit_message = pr_data.get('title', '') + "\n" + pr_data.get('body', '')
            diff_info.author = pr_data.get('user', {}).get('login')
            return diff_info
        except Exception as e:
            raise RuntimeError(f"Failed to fetch GitHub PR diff: {str(e)}")

    def get_commit_diff(self, repo_url: str, commit_sha: str) -> DiffInfo:
        local_path = self.clone_repo(repo_url)
        try:
            repo = git.Repo(local_path)
            commit = repo.commit(commit_sha)
            if commit.parents:
                diff_text = repo.git.diff(commit.parents[0].hexsha, commit.hexsha)
            else:
                diff_text = repo.git.show(commit.hexsha, format='')
            diff_info = self._parse_diff(diff_text, source=commit_sha, target=repo_url)
            diff_info.commit_message = commit.message
            diff_info.author = f"{commit.author.name} <{commit.author.email}>"
            return diff_info
        except Exception as e:
            raise RuntimeError(f"Failed to get commit diff: {str(e)}")
        finally:
            shutil.rmtree(local_path, ignore_errors=True)

    def get_local_diff(self, local_path: str, target_ref: Optional[str] = None) -> DiffInfo:
        if not git:
            raise RuntimeError("GitPython is not installed")
        repo = git.Repo(local_path)
        if target_ref:
            diff_text = repo.git.diff(target_ref)
        else:
            diff_text = repo.git.diff('HEAD')
        return self._parse_diff(diff_text, source="working tree", target=local_path)

    def get_repo_context(self, repo_path: str, file_path: str, max_files: int = 10) -> Dict[str, str]:
        context = {}
        file_dir = os.path.join(repo_path, os.path.dirname(file_path))
        if os.path.exists(file_dir):
            for f in os.listdir(file_dir):
                full_path = os.path.join(file_dir, f)
                if os.path.isfile(full_path) and f != os.path.basename(file_path):
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as file:
                            content = file.read()
                            if len(content) < 50000:
                                context[os.path.join(os.path.dirname(file_path), f)] = content
                    except:
                        pass
        config_files = ['README.md', 'package.json', 'requirements.txt', 'pyproject.toml', 
                       'Dockerfile', '.gitignore', 'tsconfig.json', 'setup.py']
        for config in config_files:
            config_path = os.path.join(repo_path, config)
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                        context[config] = f.read()
                except:
                    pass
        return context

    def read_file_at_commit(self, repo_path: str, file_path: str, ref: str = "HEAD") -> Optional[str]:
        try:
            repo = git.Repo(repo_path)
            blob = repo.git.show(f"{ref}:{file_path}")
            return blob
        except:
            return None

    def _parse_diff(self, diff_text: str, source: str, target: str) -> DiffInfo:
        stripped = diff_text.strip()

        # Handle raw code (not a git diff) - THIS IS THE KEY FIX
        if not stripped.startswith("diff --git") and not stripped.startswith("--- "):
            lines = stripped.splitlines()

            # Detect language from content
            file_path = "submitted_code.py"
            if any(l.strip().startswith(("function ", "const ", "let ", "var ")) for l in lines[:20]):
                file_path = "submitted_code.js"
            elif any(l.strip().startswith(("import ", "from ")) and "def " in stripped for l in lines[:5]):
                file_path = "submitted_code.py"
            elif "<?php" in stripped:
                file_path = "submitted_code.php"
            elif "package main" in stripped or "func " in stripped:
                file_path = "submitted_code.go"
            elif "public class" in stripped or "private class" in stripped:
                file_path = "submitted_code.java"

            # CRITICAL FIX: Prefix every line with + so LLM sees them as additions
            prefixed_lines = []
            for line in lines:
                prefixed_lines.append("+" + line)

            additions = len(lines)

            wrapped_diff = (
                f"diff --git a/{file_path} b/{file_path}\n"
                f"new file mode 100644\n"
                f"index 0000000..1111111\n"
                f"--- /dev/null\n"
                f"+++ b/{file_path}\n"
                f"@@ -0,0 +1,{additions} @@\n"
                + "\n".join(prefixed_lines)
            )

            change = FileChange(
                file_path=file_path,
                change_type="added",
                diff=wrapped_diff,
                additions=additions,
                deletions=0
            )
            return DiffInfo(
                source=source,
                target=target,
                changes=[change],
                total_additions=additions,
                total_deletions=0
            )

        # Standard git diff parsing
        changes = []
        current_file = None
        current_diff_lines = []

        for line in stripped.splitlines():
            if line.startswith("diff --git"):
                if current_file and current_diff_lines:
                    changes.append(self._create_file_change(current_file, current_diff_lines))
                match = re.match(r'diff --git a/(.+) b/(.+)', line)
                current_file = match.group(2) if match else None
                current_diff_lines = [line]
            elif current_file is not None:
                current_diff_lines.append(line)

        if current_file and current_diff_lines:
            changes.append(self._create_file_change(current_file, current_diff_lines))

        total_additions = sum(c.additions for c in changes)
        total_deletions = sum(c.deletions for c in changes)

        return DiffInfo(
            source=source,
            target=target,
            changes=changes,
            total_additions=total_additions,
            total_deletions=total_deletions
        )

    def _create_file_change(self, file_path: str, diff_lines: List[str]) -> FileChange:
        change_type = "modified"
        if any('new file mode' in l for l in diff_lines):
            change_type = "added"
        elif any('deleted file mode' in l for l in diff_lines):
            change_type = "deleted"
        elif any('rename from' in l for l in diff_lines):
            change_type = "renamed"

        additions = sum(1 for l in diff_lines if l.startswith('+') and not l.startswith('+++'))
        deletions = sum(1 for l in diff_lines if l.startswith('-') and not l.startswith('---'))
        diff_text = "\n".join(diff_lines)

        return FileChange(
            file_path=file_path,
            change_type=change_type,
            diff=diff_text,
            additions=additions,
            deletions=deletions
        )

    def cleanup(self):
        for path in self._repos.values():
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)
        self._repos.clear()
