import os
from typing import List, Dict, Optional
import httpx
from app.config import settings

class GitHubService:
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.token}" if self.token else ""
        }
        self.base_url = "https://api.github.com"

    def get_repo_info(self, owner: str, repo: str) -> Dict:
        url = f"{self.base_url}/repos/{owner}/{repo}"
        resp = httpx.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def list_prs(self, owner: str, repo: str, state: str = "open") -> List[Dict]:
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        params = {"state": state, "per_page": 30}
        resp = httpx.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_pr(self, owner: str, repo: str, pr_number: int) -> Dict:
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        resp = httpx.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        resp = httpx.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def post_pr_comment(self, owner: str, repo: str, pr_number: int, body: str, 
                       commit_id: Optional[str] = None, path: Optional[str] = None, 
                       line: Optional[int] = None) -> Dict:
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"

        data = {"body": body}

        # If we have specific file/line info, use review comments API
        if path and line:
            review_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
            review_data = {
                "body": body,
                "path": path,
                "line": line,
                "commit_id": commit_id
            }
            resp = httpx.post(review_url, headers=self.headers, json=review_data)
        else:
            resp = httpx.post(url, headers=self.headers, json=data)

        resp.raise_for_status()
        return resp.json()

    def create_review(self, owner: str, repo: str, pr_number: int, 
                     findings: List[Dict], overall_comment: str,
                     event: str = "COMMENT") -> Dict:
        """Create a pull request review with comments."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"

        comments = []
        for finding in findings:
            if finding.get('file_path') and finding.get('line_start'):
                comments.append({
                    "path": finding['file_path'],
                    "line": finding['line_start'],
                    "body": f"**{finding['title']}** ({finding['severity']})\n\n{finding['explanation']}\n\n**Impact:** {finding['impact']}\n\n**Fix:** {finding.get('recommended_fix', 'N/A')}"
                })

        data = {
            "body": overall_comment,
            "event": event,  # APPROVE, REQUEST_CHANGES, COMMENT
            "comments": comments[:50]  # GitHub limit
        }

        resp = httpx.post(url, headers=self.headers, json=data)
        resp.raise_for_status()
        return resp.json()

    def get_commits(self, owner: str, repo: str, sha: Optional[str] = None) -> List[Dict]:
        url = f"{self.base_url}/repos/{owner}/{repo}/commits"
        params = {}
        if sha:
            params["sha"] = sha
        resp = httpx.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()
