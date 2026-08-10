import json
import re
from agents.base_agent import BaseAgent
from prompts.pr_review_prompt import PR_REVIEW_PROMPT


class PRReviewAgent(BaseAgent):

    def __init__(self, api_key: str = None, model: str = None):
        super().__init__(skill_folder="pr_review", api_key=api_key, model=model)

    def review_pr(self, pr_url: str, pr_title: str, pr_body: str, changed_files: list, diff_text: str, repo_url: str = None):
        files_summary = "\n".join([
            f"- `{f.get('filename')}` (+{f.get('additions', 0)} / -{f.get('deletions', 0)})"
            for f in changed_files[:25]
        ])
        if len(changed_files) > 25:
            files_summary += f"\n... and {len(changed_files) - 25} more files"

        # Truncate diff_text if extremely large
        truncated_diff = diff_text[:35000] if diff_text else "No diff available."

        prompt = f"""
{PR_REVIEW_PROMPT}

Pull Request URL: {pr_url}
Title: {pr_title}
Description:
{pr_body or 'No description provided.'}

Changed Files Summary:
{files_summary}

Unified Patch Diff:
```diff
{truncated_diff}
```
"""
        extra_sources = [
            {
                "type": "inline",
                "target": "pr_diff.patch",
                "content": truncated_diff,
            }
        ]

        interaction = self.create_interaction(
            prompt=prompt,
            repository=repo_url,
            extra_sources=extra_sources,
        )

        output_text = getattr(interaction, "output_text", str(interaction))

        parsed_data = self.parse_review_results(output_text)
        parsed_data["output_text"] = output_text
        parsed_data["interaction_id"] = getattr(interaction, "id", "")
        return parsed_data

    def parse_review_results(self, output_text: str) -> dict:
        inline_comments = []
        code_fixes = []
        verdict = "COMMENT"
        scores = {"security": 8, "architecture": 8, "quality": 8}

        # 1. Parse JSON inline comments block
        json_match = re.search(r"```json\s*(\[\s*\{.*?\}\s*\])\s*```", output_text, re.DOTALL)
        if json_match:
            try:
                comments_data = json.loads(json_match.group(1))
                if isinstance(comments_data, list):
                    for item in comments_data:
                        if isinstance(item, dict) and "path" in item and "line" in item:
                            inline_comments.append({
                                "path": item["path"],
                                "line": int(item["line"]),
                                "body": item.get("body", item.get("comment", "")),
                            })
            except Exception:
                pass

        # 2. Parse code fix diff blocks
        diff_matches = re.findall(r"```diff\s*(.*?)\s*```", output_text, re.DOTALL)
        for diff_str in diff_matches:
            if "---" in diff_str or "+++" in diff_str or "-" in diff_str or "+" in diff_str:
                code_fixes.append(diff_str.strip())

        # 3. Parse Risk Scores & Verdict
        sec_match = re.search(r"Security Score.*?:?\s*(\d+)", output_text, re.IGNORECASE)
        arch_match = re.search(r"Architecture Score.*?:?\s*(\d+)", output_text, re.IGNORECASE)
        qual_match = re.search(r"Code Quality Score.*?:?\s*(\d+)", output_text, re.IGNORECASE)

        if sec_match:
            scores["security"] = min(10, max(0, int(sec_match.group(1))))
        if arch_match:
            scores["architecture"] = min(10, max(0, int(arch_match.group(1))))
        if qual_match:
            scores["quality"] = min(10, max(0, int(qual_match.group(1))))

        if "REQUEST_CHANGES" in output_text.upper() or scores["security"] < 7:
            verdict = "REQUEST_CHANGES"
        elif "APPROVE" in output_text.upper() and scores["security"] >= 8 and scores["quality"] >= 7:
            verdict = "APPROVE"
        else:
            verdict = "COMMENT"

        return {
            "inline_comments": inline_comments,
            "code_fixes": code_fixes,
            "verdict": verdict,
            "scores": scores,
        }
