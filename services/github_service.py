import os
import re
import requests
from config import GITHUB_TOKEN


class GitHubService:

    def __init__(self, token: str = None):
        self.token = token or os.getenv("GITHUB_TOKEN") or GITHUB_TOKEN
        self.headers = {
            "Accept": "application/vnd.github+json",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def parse_pr_url(self, url: str):
        """Extract owner, repo, and PR number from a GitHub PR URL."""
        url = url.strip()
        pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.search(pattern, url)
        if not match:
            raise ValueError("Invalid GitHub PR URL. Format must be: https://github.com/owner/repo/pull/123")
        owner, repo, pr = match.groups()
        return owner, repo, int(pr)

    def parse_repo_url(self, url: str):
        """Extract owner and repo from a GitHub Repository URL."""
        url = url.strip()
        if url.endswith(".git"):
            url = url[:-4]
        if "/tree/" in url:
            url = url.split("/tree/")[0]
        pattern = r"github\.com/([^/]+)/([^/]+)"
        match = re.search(pattern, url)
        if not match:
            raise ValueError("Invalid GitHub Repository URL. Format must be: https://github.com/owner/repo")
        return match.group(1), match.group(2)

    def get_pr(self, url: str):
        """Fetch PR details."""
        owner, repo, pr = self.parse_pr_url(url)
        api = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr}"
        response = requests.get(api, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_changed_files(self, url: str):
        """Fetch list of changed files in PR."""
        owner, repo, pr = self.parse_pr_url(url)
        api = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr}/files"
        response = requests.get(api, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_pr_diff(self, url: str):
        """Fetch unified patch diff for the PR."""
        owner, repo, pr = self.parse_pr_url(url)
        api = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr}"
        diff_headers = dict(self.headers)
        diff_headers["Accept"] = "application/vnd.github.v3.diff"
        response = requests.get(api, headers=diff_headers)
        response.raise_for_status()
        return response.text

    def post_pr_comment(self, url: str, body: str):
        """Post a general issue/PR comment on GitHub."""
        if not self.token:
            raise ValueError("GITHUB_TOKEN is required to post comments on GitHub.")
        owner, repo, pr = self.parse_pr_url(url)
        api = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr}/comments"
        response = requests.post(api, headers=self.headers, json={"body": body})
        response.raise_for_status()
        return response.json()

    def post_pr_review(self, url: str, body: str, event: str = "COMMENT", inline_comments: list = None):
        """
        Submit an official PR review with optional line-level inline comments.
        Handles GitHub restrictions (e.g. self-PR approval rules, diff line boundaries)
        with automated fallback.
        """
        if not self.token:
            raise ValueError("GITHUB_TOKEN is required to submit reviews on GitHub.")
        owner, repo, pr = self.parse_pr_url(url)
        api = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr}/reviews"

        payload = {
            "body": body,
            "event": event.upper(),
        }

        if inline_comments:
            formatted_comments = []
            for item in inline_comments:
                if item.get("path") and item.get("line") and item.get("body"):
                    formatted_comments.append({
                        "path": str(item["path"]),
                        "line": int(item["line"]),
                        "side": "RIGHT",
                        "body": str(item["body"]),
                    })
            if formatted_comments:
                payload["comments"] = formatted_comments

        response = requests.post(api, headers=self.headers, json=payload)
        if response.ok:
            return response.json()

        # Extract detailed GitHub API error explanation
        error_details = response.text
        try:
            err_json = response.json()
            if "errors" in err_json and isinstance(err_json["errors"], list):
                error_details = "; ".join([str(e) for e in err_json["errors"]])
            elif "message" in err_json:
                error_details = err_json["message"]
        except Exception:
            pass

        # Smart Fallback for 422 errors (Self-PR approval restrictions or inline diff line mismatches)
        if response.status_code == 422:
            # 1. If self-review approval is rejected, downgrade event to 'COMMENT'
            fallback_event = "COMMENT" if ("own" in error_details.lower() or "author" in error_details.lower()) else event.upper()

            # 2. Re-try without inline comments array (append inline feedback to body markdown)
            fallback_body = body
            if inline_comments:
                fallback_body += "\n\n---\n### 💬 Line-Level Feedback\n"
                for item in inline_comments:
                    fallback_body += f"- **`{item.get('path')}`** (Line #{item.get('line')}): {item.get('body')}\n"

            fallback_payload = {
                "body": fallback_body,
                "event": fallback_event,
            }

            fallback_res = requests.post(api, headers=self.headers, json=fallback_payload)
            if fallback_res.ok:
                return fallback_res.json()

        raise ValueError(f"GitHub API Error ({response.status_code}): {error_details}")