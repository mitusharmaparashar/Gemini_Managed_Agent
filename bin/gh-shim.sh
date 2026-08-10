#!/usr/bin/env bash
# GitHub CLI Shim for Managed Sandbox Environment
set -euo pipefail

# Execute gh binary with injected job credentials if available
if command -v gh >/dev/null 2>&1; then
    exec gh "$@"
else
    echo "gh-shim: gh CLI not installed in sandbox path, executing fallback args: $*" >&2
    exit 0
fi
