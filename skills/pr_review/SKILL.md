---
name: pr_review
description: Skill for automated GitHub Pull Request code reviews, security audits, diff analysis, and approval decisions.
---

# Pull Request Code Review Skill

This skill guides the agent in conducting thorough, professional pull request reviews.

## Review Guidelines

1. **Focus Areas**:
   - Accuracy and correctness of implementation
   - Security vulnerabilities and secret leakage
   - Performance regressions
   - Code readability, standard style, and design patterns
   - Test coverage and edge cases

2. **Verdict Definitions**:
   - **APPROVE**: High quality, no security risks, safe to merge.
   - **COMMENT**: Good overall, minor non-blocking feedback.
   - **REQUEST_CHANGES**: Bugs, security issues, missing error handling, or performance blockers found.

3. **Format**:
   - Always output clean Markdown with clear headings and bullet points.
