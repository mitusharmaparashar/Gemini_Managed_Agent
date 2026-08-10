import os
import streamlit as st

from agents.supervisor_agent import SupervisorAgent
from agents.repository_chat_agent import RepositoryChatAgent
from agents.pr_review_agent import PRReviewAgent
from services.github_service import GitHubService
from config import GEMINI_API_KEY, GITHUB_TOKEN, MODEL

# Page Configuration
st.set_page_config(
    page_title="Managed Agent Studio - Enterprise Product",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .verdict-approve {
        background-color: #065f46;
        color: #34d399;
        padding: 0.4rem 0.8rem;
        border-radius: 0.4rem;
        font-weight: bold;
        display: inline-block;
    }
    .verdict-request-changes {
        background-color: #991b1b;
        color: #fca5a5;
        padding: 0.4rem 0.8rem;
        border-radius: 0.4rem;
        font-weight: bold;
        display: inline-block;
    }
    .verdict-comment {
        background-color: #854d0e;
        color: #fde047;
        padding: 0.4rem 0.8rem;
        border-radius: 0.4rem;
        font-weight: bold;
        display: inline-block;
    }
    .inline-comment-card {
        background-color: #1e293b;
        border-left: 4px solid #6366f1;
        padding: 0.8rem;
        margin-bottom: 0.8rem;
        border-radius: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chat_interaction_id" not in st.session_state:
    st.session_state.chat_interaction_id = None
if "active_repo" not in st.session_state:
    st.session_state.active_repo = ""
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "pr_review_result" not in st.session_state:
    st.session_state.pr_review_result = None

# Sidebar Credentials Management
with st.sidebar:
    st.markdown("### ⚙️ Studio Settings")
    st.caption("Manage AI model & API connection credentials.")

    custom_gemini_key = st.text_input(
        "Gemini API Key",
        value=GEMINI_API_KEY or "",
        type="password",
        help="Google GenAI API Key for Managed Agents.",
    )

    custom_github_token = st.text_input(
        "GitHub Personal Access Token",
        value=GITHUB_TOKEN or "",
        type="password",
        help="Required for posting line-level PR review comments to GitHub.",
    )

    selected_model = st.selectbox(
        "Managed Agent Model",
        options=["antigravity-preview-05-2026", "gemini-2.0-flash", "gemini-1.5-pro"],
        index=0,
    )

    st.divider()

    st.markdown("#### 📡 System Status")
    if custom_gemini_key:
        st.success("Gemini API: Connected", icon=":material/check_circle:")
    else:
        st.error("Gemini API: Missing Key", icon=":material/warning:")

    if custom_github_token:
        st.success("GitHub API: Authenticated", icon=":material/check_circle:")
    else:
        st.info("GitHub API: Read-Only Mode", icon=":material/info:")

    st.divider()
    if st.button("🗑️ Reset Session State", width="stretch"):
        st.session_state.chat_history = []
        st.session_state.chat_interaction_id = None
        st.session_state.analysis_results = None
        st.session_state.pr_review_result = None
        st.rerun()

# Header
st.markdown('<div class="main-title">🤖 Managed Agent Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Autonomous Enterprise Product for Deep Audits, PR Reviews & Automated GitHub Actions CI/CD</div>', unsafe_allow_html=True)

# Studio Tabs
tab_orchestrator, tab_chat, tab_pr, tab_cicd, tab_hub = st.tabs([
    "🚀 Super Agent Orchestrator",
    "💬 Interactive Repo Q&A",
    "🔀 GitHub PR Code Review",
    "⚡ Automated CI/CD Setup",
    "📊 Studio Hub & Reports",
])

# -----------------------------------------------------------------------------
# TAB 1: SUPER AGENT ORCHESTRATOR
# -----------------------------------------------------------------------------
with tab_orchestrator:
    st.markdown("### 🎯 Multi-Agent Deep Repository Analysis")
    st.caption("Orchestrate parallel AI agents to audit structure, architecture, security vulnerabilities, and documentation.")

    col_repo, col_opts = st.columns([3, 1])

    with col_repo:
        repo_url = st.text_input(
            "Repository URL",
            placeholder="https://github.com/owner/repository",
            value=st.session_state.active_repo,
            key="orchestrator_repo_input",
        )

    with col_opts:
        execution_mode = st.radio(
            "Execution Mode",
            options=["Parallel (Fast)", "Sequential"],
            index=0,
            horizontal=True,
        )

    st.markdown("#### Select Specialized Agents to Deploy")

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            sel_repo = st.checkbox("📁 Repository Breakdown", value=True)
        with c2:
            sel_arch = st.checkbox("🏗️ Architecture Analysis", value=True)
        with c3:
            sel_sec = st.checkbox("🛡️ Security & Vulnerability Audit", value=True)
        with c4:
            sel_doc = st.checkbox("📚 Technical Documentation", value=True)

    selected_agent_names = []
    if sel_repo:
        selected_agent_names.append("Repository")
    if sel_arch:
        selected_agent_names.append("Architecture")
    if sel_sec:
        selected_agent_names.append("Security")
    if sel_doc:
        selected_agent_names.append("Documentation")

    if st.button("🚀 Run Super Agent Analysis", type="primary", width="stretch"):
        if not repo_url.strip():
            st.warning("Please specify a valid GitHub repository URL.")
            st.stop()

        if not selected_agent_names:
            st.warning("Please select at least one agent to run.")
            st.stop()

        st.session_state.active_repo = repo_url.strip()
        supervisor = SupervisorAgent(api_key=custom_gemini_key, model=selected_model)

        with st.spinner(f"Running {len(selected_agent_names)} Managed Agents ({execution_mode})..."):
            is_parallel = "Parallel" in execution_mode
            results = supervisor.run(
                selected_agents=selected_agent_names,
                repo=repo_url.strip(),
                parallel=is_parallel,
            )
            st.session_state.analysis_results = results

        st.success(f"Analysis Complete! Executed {len(results)} agent tasks.")

    if st.session_state.analysis_results:
        results = st.session_state.analysis_results
        st.divider()

        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric("Total Agents Executed", len(results))
        with k2:
            total_time = sum(r.get("duration", 0) for r in results.values())
            st.metric("Total Duration", f"{round(total_time, 2)}s")
        with k3:
            st.metric("Target Repository", st.session_state.active_repo.split("/")[-1] if "/" in st.session_state.active_repo else "N/A")

        st.markdown("### 📋 Agent Reports")
        agent_tabs = st.tabs([f"{name}" for name in results.keys()])

        for idx, (agent_name, data) in enumerate(results.items()):
            with agent_tabs[idx]:
                st.caption(f"⚡ Execution Time: {data.get('duration', 0)} seconds")
                if data.get("environment_id"):
                    st.caption(f"Environment ID: `{data.get('environment_id')}` | Interaction ID: `{data.get('interaction_id')}`")

                st.markdown(data["output"])

                st.download_button(
                    label=f"📥 Download {agent_name} Report (.md)",
                    data=data["output"],
                    file_name=f"{agent_name.lower()}_report.md",
                    mime="text/markdown",
                    key=f"dl_{agent_name}",
                )

# -----------------------------------------------------------------------------
# TAB 2: INTERACTIVE REPO Q&A / CHAT
# -----------------------------------------------------------------------------
with tab_chat:
    st.markdown("### 💬 Interactive Codebase Q&A with Memory")
    st.caption("Ask questions about any repository. Multi-turn conversation retains full context via Managed Agent interactions.")

    repo_chat_input = st.text_input(
        "Target Repository URL for Chat",
        value=st.session_state.active_repo,
        placeholder="https://github.com/owner/repository",
        key="chat_repo_input",
    )

    if repo_chat_input.strip() != st.session_state.active_repo:
        if st.button("Update Target Repository for Chat"):
            st.session_state.active_repo = repo_chat_input.strip()
            st.session_state.chat_history = []
            st.session_state.chat_interaction_id = None
            st.success("Updated active repository!")

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_query = st.chat_input("Ask any question about the codebase...")
    if user_query:
        if not repo_chat_input.strip():
            st.warning("Please enter a repository URL to start chatting.")
            st.stop()

        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        chat_agent = RepositoryChatAgent(api_key=custom_gemini_key, model=selected_model)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing repository & reasoning..."):
                try:
                    interaction = chat_agent.chat(
                        user_question=user_query,
                        repo=repo_chat_input.strip(),
                        previous_interaction_id=st.session_state.chat_interaction_id,
                    )
                    response_text = getattr(interaction, "output_text", str(interaction))
                    st.session_state.chat_interaction_id = getattr(interaction, "id", None)
                    st.markdown(response_text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response_text})
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})

# -----------------------------------------------------------------------------
# TAB 3: GITHUB PR CODE REVIEW
# -----------------------------------------------------------------------------
with tab_pr:
    st.markdown("### 🔀 Autonomous GitHub PR Code Review & Approval Platform")
    st.caption("Includes the 5 Standout Features: Changed-files filter, Line-level inline comments, AI Code Fixes (diffs), Multi-Agent Consensus Scorecard, and Auto-publishing to GitHub.")

    pr_url = st.text_input(
        "Pull Request URL",
        placeholder="https://github.com/owner/repository/pull/123",
        key="pr_url_input",
    )

    if st.button("🚀 Audit PR with 5 Standout Features", type="primary", width="stretch"):
        if not pr_url.strip():
            st.warning("Please enter a valid GitHub PR URL.")
            st.stop()

        gh_service = GitHubService(token=custom_github_token)

        with st.spinner("Fetching changed files, patches, and PR diff from GitHub..."):
            try:
                pr_data = gh_service.get_pr(pr_url.strip())
                changed_files = gh_service.get_changed_files(pr_url.strip())
                diff_text = gh_service.get_pr_diff(pr_url.strip())
            except Exception as e:
                st.error(f"Failed to fetch PR details from GitHub: {e}")
                st.stop()

        owner, repo_name = pr_data["base"]["repo"]["owner"]["login"], pr_data["base"]["repo"]["name"]
        repo_full_url = f"https://github.com/{owner}/{repo_name}"

        pr_review_agent = PRReviewAgent(api_key=custom_gemini_key, model=selected_model)

        with st.spinner("Multi-Agent Engine running Security, Architecture & Code Quality PR analysis..."):
            try:
                parsed_res = pr_review_agent.review_pr(
                    pr_url=pr_url.strip(),
                    pr_title=pr_data.get("title", ""),
                    pr_body=pr_data.get("body", ""),
                    changed_files=changed_files,
                    diff_text=diff_text,
                    repo_url=repo_full_url,
                )

                st.session_state.pr_review_result = {
                    "pr_data": pr_data,
                    "changed_files": changed_files,
                    "diff_text": diff_text,
                    "review_markdown": parsed_res["output_text"],
                    "inline_comments": parsed_res["inline_comments"],
                    "code_fixes": parsed_res["code_fixes"],
                    "verdict": parsed_res["verdict"],
                    "scores": parsed_res["scores"],
                    "pr_url": pr_url.strip(),
                }
            except Exception as e:
                st.error(f"PR Review Agent Error: {e}")
                st.stop()

        st.success("Standout PR Analysis Complete!")

    if st.session_state.pr_review_result:
        res = st.session_state.pr_review_result
        pr_data = res["pr_data"]
        changed_files = res["changed_files"]
        scores = res["scores"]
        verdict = res["verdict"]

        st.divider()

        st.markdown("### 📊 1. Multi-Agent Consensus Scorecard & Verdict")

        c_v1, c_v2, c_v3, c_v4 = st.columns(4)
        with c_v1:
            st.metric("🛡️ Security Score", f"{scores.get('security', 8)} / 10")
        with c_v2:
            st.metric("🏗️ Architecture Score", f"{scores.get('architecture', 8)} / 10")
        with c_v3:
            st.metric("🔍 Code Quality Score", f"{scores.get('quality', 8)} / 10")
        with c_v4:
            st.write("**Consensus Verdict**")
            if verdict == "APPROVE":
                st.markdown('<div class="verdict-approve">✅ APPROVE (Passed)</div>', unsafe_allow_html=True)
            elif verdict == "REQUEST_CHANGES":
                st.markdown('<div class="verdict-request-changes">❌ REQUEST CHANGES</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="verdict-comment">💬 COMMENT (Suggestions)</div>', unsafe_allow_html=True)

        st.write("")

        with st.expander(f"📁 2. Inspect Changed Files ({len(changed_files)} files)", expanded=False):
            for file_item in changed_files:
                f_name = file_item.get("filename", "unknown")
                adds = file_item.get("additions", 0)
                dels = file_item.get("deletions", 0)
                st.markdown(f"- `{f_name}` : :green[+{adds}] / :red[-{dels}]")

        st.markdown(f"### 💬 3. Line-Level Inline Comments ({len(res['inline_comments'])} comments detected)")

        if res["inline_comments"]:
            for item in res["inline_comments"]:
                st.markdown(f"""
                <div class="inline-comment-card">
                    <strong>📄 File:</strong> <code>{item.get('path')}</code> &nbsp;|&nbsp; <strong>📍 Line:</strong> <code>#{item.get('line')}</code>
                    <p style="margin-top:0.4rem; margin-bottom:0;">{item.get('body')}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No line-specific bugs detected. Overall feedback is included in the general review.")

        st.markdown(f"### 🛠️ 4. AI-Generated Code Fixes ({len(res['code_fixes'])} diff patches)")

        if res["code_fixes"]:
            for idx, fix_diff in enumerate(res["code_fixes"]):
                st.markdown(f"#### Fix Patch #{idx+1}")
                st.code(fix_diff, language="diff")
                st.download_button(
                    label=f"📥 Download Fix Patch #{idx+1} (.patch)",
                    data=fix_diff,
                    file_name=f"fix_patch_{idx+1}.patch",
                    mime="text/x-diff",
                    key=f"dl_fix_{idx}",
                )
        else:
            st.info("No code diff patches generated.")

        st.markdown("### 📋 Full Review Markdown Report")
        st.markdown(res["review_markdown"])

        st.divider()

        st.markdown("### 🚀 5. Auto-Publish Review & Inline Comments to GitHub")

        col_act, col_btn = st.columns([1, 2])
        with col_act:
            final_action = st.selectbox(
                "GitHub Decision Action",
                options=[verdict, "APPROVE", "REQUEST_CHANGES", "COMMENT"],
                index=0,
                help="Recommended verdict is pre-selected based on Multi-Agent Consensus.",
            )

        with col_btn:
            st.write("")
            st.write("")
            if st.button("🚀 Auto-Post Consensus Review + Inline Comments to GitHub", type="primary", width="stretch"):
                if not custom_github_token:
                    st.error("GitHub Personal Access Token is required in the sidebar to publish reviews.")
                else:
                    gh_service = GitHubService(token=custom_github_token)
                    with st.spinner(f"Publishing {final_action} review with {len(res['inline_comments'])} inline line comments to GitHub..."):
                        try:
                            gh_service.post_pr_review(
                                url=res["pr_url"],
                                body=res["review_markdown"],
                                event=final_action,
                                inline_comments=res["inline_comments"],
                            )
                            st.balloons()
                            st.success(f"Successfully published {final_action} review and inline comments to GitHub!")
                        except Exception as e:
                            st.error(f"GitHub API Error: {e}")

# -----------------------------------------------------------------------------
# TAB 4: AUTOMATED CI/CD SETUP & GITHUB ACTION GENERATOR
# -----------------------------------------------------------------------------
with tab_cicd:
    st.markdown("### ⚡ Automated GitHub Actions CI/CD Product Setup")
    st.caption("Automatically trigger Managed Agent PR reviews whenever new Pull Requests are opened or new commits are pushed (`synchronize`)!")

    with st.container(border=True):
        st.markdown("#### ⚙️ Configure Workflow Generator")
        col_w1, col_w2 = st.columns(2)

        with col_w1:
            wf_skill = st.selectbox(
                "Review Skill for CI/CD",
                options=["pr_review", "security", "architecture", "documentation"],
                index=0,
            )
            wf_persist = st.checkbox("Persist Memory Across Commits (PERSIST=1)", value=True)

        with col_w2:
            wf_model = st.text_input("Base Agent Model", value="antigravity-preview-05-2026")
            wf_triggers = st.multiselect(
                "Pull Request Trigger Events",
                options=["opened", "synchronize", "reopened"],
                default=["opened", "synchronize", "reopened"],
            )

    workflow_content = f"""name: Autonomous Managed Agent Code Review

on:
  pull_request:
    types: [{", ".join(wf_triggers)}]
  workflow_dispatch:
    inputs:
      pr_number:
        description: "Pull Request number to review manually"
        required: false

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      issues: write

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install google-genai requests

      - name: Run Autonomous Managed Agent PR Review
        env:
          GEMINI_API_KEY: ${{{{ secrets.GEMINI_API_KEY }}}}
          GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
          GITHUB_REPOSITORY: ${{{{ github.repository }}}}
          PR_NUMBER: ${{{{ github.event.pull_request.number || inputs.pr_number }}}}
          REVIEW_SKILL: "{wf_skill}"
          BASE_AGENT: "{wf_model}"
          PERSIST: "{'1' if wf_persist else '0'}"
        run: |
          python review_pr_action.py
"""

    st.markdown("#### 📄 Generated Workflow (`.github/workflows/managed_agent_review.yml`)")
    st.code(workflow_content, language="yaml")

    col_dl, col_info = st.columns([1, 2])
    with col_dl:
        st.download_button(
            label="📥 Download Workflow File (.yml)",
            data=workflow_content,
            file_name="managed_agent_review.yml",
            mime="text/yaml",
            type="primary",
        )

    with col_info:
        st.info("Place this file at `.github/workflows/managed_agent_review.yml` and add `GEMINI_API_KEY` in your GitHub Repository Secrets!")

# -----------------------------------------------------------------------------
# TAB 5: STUDIO HUB & REPORTS
# -----------------------------------------------------------------------------
with tab_hub:
    st.markdown("### 📊 Studio Hub & System Status")
    st.caption("Overview of registered agents, capabilities, and system configuration.")

    with st.container(border=True):
        st.markdown("#### Registered Managed Agents")
        ag_col1, ag_col2 = st.columns(2)

        with ag_col1:
            st.markdown("""
            - 📁 **Repository Agent**: Full repository structure, file tree, technology stack summary.
            - 🏗️ **Architecture Agent**: High/Low-level architectural overview & Mermaid diagrams.
            - 🛡️ **Security Agent**: OWASP top 10, secret detection, code vulnerability scanner.
            """)
        with ag_col2:
            st.markdown("""
            - 📚 **Documentation Agent**: Full developer documentation, setup guides, component breakdown.
            - 🔍 **PR Review Agent**: Unified diff reviewer, safety audit & GitHub approval automation.
            - 💬 **Repository Chat Agent**: Stateful multi-turn conversational AI with workspace memory.
            - ⚡ **Autonomous CI/CD Script**: GitHub Actions runner with commit memory persistence.
            """)

    st.markdown("#### Active Configuration")
    st.json({
        "gemini_model": selected_model,
        "api_key_configured": bool(custom_gemini_key),
        "github_token_configured": bool(custom_github_token),
        "active_repository": st.session_state.active_repo or "None",
        "chat_interaction_session_id": st.session_state.chat_interaction_id or "None",
    })