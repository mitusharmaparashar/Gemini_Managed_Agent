from __future__ import annotations

SEVERITY_EMOJI = {
    "critical": "🚨",
    "high": "⚠️",
    "medium": "⚡",
    "low": "💡",
    "info": "ℹ️",
}

SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}

SYSTEM_INSTRUCTION = """
You are a Principal Software Engineer and Security Auditor conducting an automated Pull Request Review.

Your objective is to perform a rigorous code review of the pull request changes, identifying:
- Security vulnerabilities, injection risks, secret leaks, unhandled inputs
- Bugs, race conditions, edge cases, error handling flaws
- Architectural anti-patterns, breaking API changes
- Code quality, readability, maintainability, and test coverage gaps

Return ONLY a valid JSON object matching the requested schema.
Be constructive, accurate, and reference exact file paths and line numbers from the patch diff.
"""

FINDINGS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "High-level 2-3 sentence executive summary of the review findings and PR health."
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "Relative file path matching the diff (e.g. 'src/app.py')."
                    },
                    "line": {
                        "type": "integer",
                        "description": "Line number in the current file where the finding is anchored."
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Optional start line for multi-line findings."
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low", "info"],
                        "description": "Severity level of the finding."
                    },
                    "title": {
                        "type": "string",
                        "description": "Short descriptive title of the finding."
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed explanation of the issue, root cause, and impact."
                    },
                    "suggestion": {
                        "type": "string",
                        "description": "Optional exact replacement code snippet to apply at the anchored line(s)."
                    }
                },
                "required": ["file", "line", "severity", "title", "description"]
            }
        }
    },
    "required": ["summary", "findings"]
}
