# -*- coding: utf-8 -*-
"""
JIRA 规范巡检 Agent。

流程逻辑由 Skills 驱动：
  - jira-inspection   : 六阶段固化执行流程
  - jira-ticket-standard : 提单/关单规范（ZT 零容忍条款）
"""

from __future__ import annotations

from pathlib import Path

from deepagents import create_deep_agent as create_agent
from deepagents.backends import FilesystemBackend
from deepagents.middleware import SkillsMiddleware
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from app.agents.jira.jira_tools import (
    phase1_fetch_and_save_jira_issues,
    phase2_load_batch_info,
    phase3_download_attachments,
    phase4_analyze_bug_level,
    phase3_fetch_batch_for_inspection,
    phase3_save_batch_quality_result,
    phase4_generate_quality_report,
    phase6_export_check_result,
    post_jira_issue_comment,
    save_jira_audit_to_database,
    read_local_file,
)

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)

llm = init_chat_model("deepseek:deepseek-chat")

# ── Skill 中间件（从 workspace 文件系统加载） ─────────────────────────────────
_WORKSPACE_DIR = (_PROJECT_ROOT / "backend" / "workspace").resolve()
_file_backend = FilesystemBackend(root_dir=_WORKSPACE_DIR, virtual_mode=True)

_skills_middleware = SkillsMiddleware(
    backend=_file_backend,
    sources=[
        "jira/skills/jira_inspection/",  # jira-ticket-standard（提单规范）
    ],
)

# ── System Prompt（精简版，流程细节由 Skill 承载） ────────────────────────────
SYSTEM_PROMPT = """
# 角色

你是 JIRA 规范巡检助手。收到用户的巡检请求后，**立即激活 `jira-inspection` Skill**，严格按照其中定义的六阶段固化流程执行。

规范条文来自 `jira-ticket-standard` Skill，质检时直接引用其中的 §编号 / ZT 编号，不得编造。

# 工具说明

| 工具 | 用途 |
|------|------|
| `phase1_fetch_and_save_jira_issues` | Phase 1：拉取并保存单据 |
| `phase2_load_batch_info` | Phase 2：确认批次规划 |
| `phase3_download_attachments` | Phase 3：下载图片附件 |
| `phase4_analyze_bug_level` | Phase 4：多模态识别 Bug 等级 |
| `phase3_fetch_batch_for_inspection` | Phase 5：读取批次字段数据 |
| `phase3_save_batch_quality_result` | Phase 5：保存质检结果 |
| `phase4_generate_quality_report` | Phase 6：生成 Markdown 汇总报告 |
| `phase6_export_check_result` | Phase 6：导出前端展示 JSON |
| `post_jira_issue_comment` | Phase 5：对不合规单据发表评论 |
| `read_local_file` | 读取本地文件内容 |
| `save_jira_audit_to_database` | ⚠️ 入库操作，须用户明确批准后才可调用 |

# 约束

- 严格按 `jira-inspection` Skill 的六阶段顺序执行，不得跳过或合并阶段。
- 若 JIRA 凭证未配置，提示用户在 `.env` 中配置 `JIRA_URL` / `JIRA_USER` / `JIRA_PASS`。
- 若多模态模型未配置，提示用户在 `.env` 中配置 `IMAGE_PARSER_API_KEY`。
"""

agent = create_agent(
    model=llm,
    tools=[
        # ── 六阶段核心工具 ──
        phase1_fetch_and_save_jira_issues,
        phase2_load_batch_info,
        phase3_download_attachments,
        phase4_analyze_bug_level,
        phase3_fetch_batch_for_inspection,
        phase3_save_batch_quality_result,
        phase4_generate_quality_report,
        phase6_export_check_result,
        # ── 辅助工具 ──
        post_jira_issue_comment,
        save_jira_audit_to_database,
        read_local_file,
    ],
    backend=_file_backend,
    middleware=[_skills_middleware],
    system_prompt=SYSTEM_PROMPT,
)
