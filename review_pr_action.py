"""
Autonomous GitHub Pull Request Reviewer using Gemini Managed Agents.
Designed to run inside GitHub Actions CI/CD workflows on pull_request events.
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import sys
from typing import Any

import requests
from google import genai

from schema import (
    FINDINGS_SCHEMA,
    SEVERITY_EMOJI,
    SEVERITY_ORDER,
    SYSTEM_INSTRUCTION,
)

BASE_AGENT = os.environ.get("BASE_AGENT", "antigravity-preview-05-2026")
SKILLS_DIR = pathlib.Path(__file__).parent / "skills"
SHIM_SOURCE = pathlib.Path(__file__).parent / "bin" / "gh-shim.sh"
REPO_MOUNT = "/workspace/repo"
GH_WRAPPER = "/workspace/bin/gh"
STATE_MARKER_RE = re.compile(r"<!-- github-pr-reviewer:state (\{.*?\}) -->")


# --------------------------------------------------------------------------- #
# GitHub API Client Helper
# --------------------------------------------------------------------------- #
class GitHubClient:

    def __init__(self, api_url: str, repo: str, token: str):
        self.api_url = api_url.rstrip("/")
        self.repo = repo
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
        }

    def get_pr(self, pr_number: int) -> dict[str, Any]:
        url = f"{self.api_url}/repos/{self.repo}/pulls/{pr_number}"
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.json()

    def get_pr_files(self, pr_number: int) -> list[dict[str, Any]]:
        url = f"{self.api_url}/repos/{self.repo}/pulls/{pr_number}/files?per_page=100"
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.json()

    def get_pr_diff(self, pr_number: int) -> str:
        url = f"{self.api_url}/repos/{self.repo}/pulls/{pr_number}"
        diff_headers = dict(self.headers)
        diff_headers["Accept"] = "application/vnd.github.v3.diff"
        r = requests.get(url, headers=diff_headers)
        r.raise_for_status()
        return r.text

    def list_issue_comments(self, pr_number: int) -> list[dict[str, Any]]:
        url = f"{self.api_url}/repos/{self.repo}/issues/{pr_number}/comments?per_page=100"
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.json()

    def post_issue_comment(self, pr_number: int, body: str) -> dict[str, Any]:
        url = f"{self.api_url}/repos/{self.repo}/issues/{pr_number}/comments"
        r = requests.post(url, headers=self.headers, json={"body": body})
        r.raise_for_status()
        return r.json()

    def post_review_comment(
        self,
        pr_number: int,
        commit_id: str,
        path: str,
        line: int,
        body: str,
        start_line: int | None = None,
    ) -> bool:
        url = f"{self.api_url}/repos/{self.repo}/pulls/{pr_number}/comments"
        payload = {
            "body": body,
            "commit_id": commit_id,
            "path": path,
            "line": line,
            "side": "RIGHT",
        }
        if start_line and start_line != line:
            payload["start_line"] = start_line
            payload["start_side"] = "RIGHT"

        r = requests.post(url, headers=self.headers, json=payload)
        return r.ok


def build_basic_auth_header(token: str) -> str:
    user_pass = f"x-access-token:{token}"
    b64 = base64.b64encode(user_pass.encode()).decode()
    return f"Basic {b64}"


# --------------------------------------------------------------------------- #
# Skill loading
# --------------------------------------------------------------------------- #
def load_skill(name: str) -> tuple[str, str]:
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.is_file():
        available = sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md"))
        print(f"⚠️  Skill '{name}' not found at {path}, falling back to repository skill.")
        path = SKILLS_DIR / "repository" / "SKILL.md"
        if not path.is_file():
            return name, "Perform a thorough code review."

    text = path.read_text(encoding="utf-8")
    m = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
    return (m.group(1).strip() if m else name), text


# --------------------------------------------------------------------------- #
# State memory markers across commits
# --------------------------------------------------------------------------- #
def build_state_marker(state: dict[str, Any]) -> str:
    return f"<!-- github-pr-reviewer:state {json.dumps(state)} -->"


def find_state(gh: GitHubClient, pr_number: int, skill_name: str) -> dict[str, Any] | None:
    try:
        comments = gh.list_issue_comments(pr_number)
    except Exception as exc:
        print(f"⚠️ Could not list PR comments for state recovery: {exc}", file=sys.stderr)
        return None

    for c in reversed(comments):
        m = STATE_MARKER_RE.search(c.get("body") or "")
        if not m:
            continue
        try:
            state = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if state.get("skill") == skill_name and state.get("interaction_id"):
            return state
    return None


# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #
def _parse_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1)
    else:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            raw = raw[start : end + 1]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        repaired = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", raw)
        try:
            data = json.loads(repaired)
        except json.JSONDecodeError:
            data = {"summary": raw[:500], "findings": []}

    data.setdefault("summary", "")
    data.setdefault("findings", [])
    return data


def build_environment(
    clone_url: str,
    skill_name: str,
    skill_text: str,
    gh_token: str,
    private: bool,
    enable_gh: bool,
) -> dict[str, Any]:
    github_entry: dict[str, Any] = {"domain": "github.com"}
    if private or enable_gh:
        github_entry["transform"] = [{"Authorization": build_basic_auth_header(gh_token)}]

    allowlist: list[dict[str, Any]] = [github_entry]
    sources: list[dict[str, Any]] = [
        {"type": "repository", "source": clone_url, "target": REPO_MOUNT},
        {
            "type": "inline",
            "target": f".agents/skills/{skill_name}/SKILL.md",
            "content": skill_text,
        },
    ]

    if enable_gh and SHIM_SOURCE.is_file():
        allowlist.append({
            "domain": "api.github.com",
            "transform": [{"Authorization": f"Bearer {gh_token}"}],
        })
        allowlist.append({"domain": "*.githubusercontent.com"})
        sources.append({
            "type": "inline",
            "target": "bin/gh",
            "content": SHIM_SOURCE.read_text(encoding="utf-8"),
        })

    return {
        "type": "remote",
        "sources": sources,
        "network": {"allowlist": allowlist},
    }


def build_prompt(
    repo: str,
    pr_number: int,
    pr_title: str,
    base_branch: str,
    head_branch: str,
    head_sha: str,
    diff_text: str,
    enable_gh: bool,
    follow_up: bool,
) -> str:
    parts = [
        f"You are reviewing GitHub pull request #{pr_number} of {repo} "
        f"(\"{pr_title}\"), targeting branch '{base_branch}' from '{head_branch}'.\n"
    ]
    if follow_up:
        parts.append(
            f"You reviewed an earlier version of this pull request; your previous "
            f"findings are in conversation history. New commits were pushed (head: {head_sha[:7]}). "
            f"Focus on what changed since last review: state which previous findings are fixed and raise new findings.\n"
        )

    parts.append(
        f"The repository is mounted at {REPO_MOUNT}. Unified patch diff:\n\n"
        f"```diff\n{diff_text[:35000]}\n```\n\n"
        f"Apply the review skill. For every finding whose fix fits at the anchored line(s), "
        f"include the `suggestion` field with exact replacement code for one-click suggestions.\n"
        f"Return ONLY the JSON object matching schema:\n\n"
        f"{json.dumps(FINDINGS_SCHEMA)}"
    )
    return "\n".join(parts)


def _run_streaming(client: genai.Client, **kwargs: Any) -> tuple[str, Any]:
    chunks: list[str] = []
    final: Any = None

    # Handle model vs agent name routing
    agent_val = kwargs.get("agent", BASE_AGENT)
    if "gemini" in agent_val.lower() and "preview" not in agent_val.lower():
        kwargs["model"] = agent_val
        kwargs.pop("agent", None)

    try:
        for event in client.interactions.create(stream=True, **kwargs):
            delta = getattr(event, "delta", None)
            text = getattr(delta, "text", None) if delta is not None else None
            if text:
                chunks.append(text)
            interaction = getattr(event, "interaction", None)
            if interaction is not None:
                final = interaction
    except Exception as exc:
        # Fallback to non-streaming if stream is unsupported
        interaction = client.interactions.create(stream=False, **kwargs)
        text = getattr(interaction, "output_text", str(interaction))
        return text, interaction

    return "".join(chunks), final


def run_review(
    client: genai.Client,
    environment: dict[str, Any],
    prompt: str,
    skill_text: str,
    prior_state: dict[str, Any] | None,
    private: bool,
) -> tuple[dict[str, Any], str | None, str | None, str]:
    system_instruction = f"{SYSTEM_INSTRUCTION}\n\n# Review skill\n\n{skill_text}"

    attempts: list[tuple[str, dict[str, Any] | str, str | None]] = []
    if prior_state:
        attempts.append(
            ("resumed sandbox + conversation", environment, prior_state.get("interaction_id"))
        )
    attempts.append(("cold start", environment, None))

    last_exc: Exception | None = None
    for mode, env, prev_id in attempts:
        try:
            kwargs: dict[str, Any] = {
                "agent": BASE_AGENT,
                "system_instruction": system_instruction,
                "input": prompt,
                "environment": env if isinstance(env, dict) else environment,
            }
            if prev_id:
                kwargs["previous_interaction_id"] = prev_id

            text, interaction = _run_streaming(client, **kwargs)
            result = _parse_json(text)
            return (
                result,
                getattr(interaction, "environment_id", None),
                getattr(interaction, "id", None),
                mode,
            )
        except Exception as exc:
            last_exc = exc
            print(f"⚠️ Attempt '{mode}' failed: {exc}", file=sys.stderr)
            continue

    if last_exc:
        raise last_exc
    raise RuntimeError("Review execution failed across all modes.")


def render_finding_comment(f: dict[str, Any], emoji: str) -> str:
    parts = [
        f"### {emoji} {f.get('title', 'Finding')}\n",
        f"**Severity:** `{f.get('severity', 'info').upper()}`\n\n",
        f"{f.get('description', '')}\n",
    ]
    if f.get("suggestion"):
        parts.append(f"\n```suggestion\n{f['suggestion']}\n```\n")
    return "".join(parts)


def post_results(
    gh: GitHubClient,
    pr_number: int,
    head_sha: str,
    skill_title: str,
    result: dict[str, Any],
    state_marker: str = "",
) -> None:
    findings = sorted(
        result.get("findings", []),
        key=lambda f: SEVERITY_ORDER.get(f.get("severity", "info"), 9),
    )

    counts: dict[str, int] = {}
    for f in findings:
        sev = f.get("severity", "info")
        counts[sev] = counts.get(sev, 0) + 1

    counts_line = (
        " · ".join(
            f"{SEVERITY_EMOJI.get(s, '')} {n} {s}"
            for s, n in sorted(counts.items(), key=lambda kv: SEVERITY_ORDER.get(kv[0], 9))
        )
        or "no findings"
    )

    gh.post_issue_comment(
        pr_number,
        f"## 🔍 Managed Agent Automated Review — {skill_title}\n\n"
        f"{result.get('summary', '(no summary)')}\n\n"
        f"**Findings Breakdown:** {counts_line}\n\n"
        f"<sub>🤖 Reviewed by Google Gemini Managed Agent · Advisory audit</sub>\n"
        f"{state_marker}",
    )

    overflow: list[str] = []
    for f in findings:
        body = render_finding_comment(f, SEVERITY_EMOJI.get(f.get("severity", "info"), ""))
        anchored = False
        try:
            start_line = f.get("start_line")
            anchored = gh.post_review_comment(
                pr_number,
                head_sha,
                f["file"],
                int(f["line"]),
                body,
                start_line=int(start_line) if start_line else None,
            )
        except Exception as exc:
            print(f"⚠️ Inline comment failed for {f.get('file')}:{f.get('line')}: {exc}", file=sys.stderr)

        if not anchored:
            overflow.append(f"`{f.get('file')}:{f.get('line')}`\n\n{body}")

    if overflow:
        gh.post_issue_comment(
            pr_number,
            "### Additional Findings (Unanchored to Diff Lines)\n\n" + "\n\n---\n\n".join(overflow),
        )

    print(f"✅ Successfully posted review summary and {len(findings)} finding(s) to PR #{pr_number}.")


def resolve_pr_number() -> int:
    if os.environ.get("PR_NUMBER"):
        return int(os.environ["PR_NUMBER"])
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and pathlib.Path(event_path).is_file():
        event = json.loads(pathlib.Path(event_path).read_text(encoding="utf-8"))
        number = (event.get("pull_request") or {}).get("number") or (event.get("issue") or {}).get("number")
        if number:
            return int(number)
    raise SystemExit("❌ Cannot determine PR number: Set PR_NUMBER or run inside pull_request event.")


def main() -> int:
    try:
        repo = os.environ["GITHUB_REPOSITORY"]
        gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not gh_token:
            raise KeyError("GITHUB_TOKEN")
        os.environ.get("GEMINI_API_KEY")
    except KeyError as exc:
        print(f"❌ Missing required env variable: {exc}", file=sys.stderr)
        return 1

    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    skill_name = os.environ.get("REVIEW_SKILL", "security")
    dry_run = os.environ.get("DRY_RUN", "0") == "1"
    persist = os.environ.get("PERSIST", "1") == "1"
    enable_gh = os.environ.get("AGENT_GH", "1") == "1"

    pr_number = resolve_pr_number()
    skill_title, skill_text = load_skill(skill_name)
    gh = GitHubClient(api_url, repo, gh_token)

    print(f"Fetching PR #{pr_number} of {repo}...")
    pr = gh.get_pr(pr_number)
    diff_text = gh.get_pr_diff(pr_number)
    private = False

    prior_state = None
    if persist and not dry_run:
        prior_state = find_state(gh, pr_number, skill_name)
        if prior_state:
            print(f"Found previous review state (head {prior_state.get('head_sha', '?')[:7]}) — running follow-up mode.")

    environment = build_environment(
        clone_url=f"{server_url}/{repo}.git",
        skill_name=skill_name,
        skill_text=skill_text,
        gh_token=gh_token,
        private=private,
        enable_gh=enable_gh,
    )

    prompt = build_prompt(
        repo=repo,
        pr_number=pr_number,
        pr_title=pr.get("title", ""),
        base_branch=pr["base"]["ref"],
        head_branch=pr["head"]["ref"],
        head_sha=pr["head"]["sha"],
        diff_text=diff_text,
        enable_gh=enable_gh,
        follow_up=bool(prior_state),
    )

    client = genai.Client()
    result, env_id, int_id, mode = run_review(client, environment, prompt, skill_text, prior_state, private)

    if dry_run:
        print(json.dumps(result, indent=2))
        return 0

    state_marker = ""
    if persist and int_id:
        state_marker = build_state_marker({
            "v": 1,
            "skill": skill_name,
            "interaction_id": int_id,
            "environment_id": env_id,
            "head_sha": pr["head"]["sha"],
        })

    post_results(gh, pr_number, pr["head"]["sha"], skill_title, result, state_marker)
    return 0


if __name__ == "__main__":
    sys.exit(main())
