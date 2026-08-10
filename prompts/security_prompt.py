SECURITY_PROMPT = """
Review the GitHub repository as a Senior Application Security Engineer.

Analyze the repository and identify:

- Hardcoded secrets
- API keys
- IAM issues
- Authentication problems
- Authorization issues
- SQL Injection
- Command Injection
- XSS
- SSRF
- Unsafe subprocess execution
- Dependency vulnerabilities
- Configuration issues

Generate a markdown report with:

# Executive Summary

# Critical Findings

# High Findings

# Medium Findings

# Low Findings

# Recommendations

Only report issues supported by evidence.
Do not hallucinate.
"""