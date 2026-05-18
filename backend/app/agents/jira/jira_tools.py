# -*- coding: utf-8 -*-
"""
JIRA 规范巡检工具：解析链接、拉取单据（REST API，与 E:\\cqJIRA 一致使用 Basic Auth）、写本地 API 库表、发表评论。
四阶段批处理工具：Phase1 拉取→Phase2 确认→Phase3 分批质检→Phase4 汇总报告。
"""

from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from langchain_core.tools import tool

# 显式定位项目根目录的 .env（src/app/agents/jira/jira_tools.py → 上溯 5 级到项目根）
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)

FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
JIRA_URL = os.getenv("JIRA_URL", "http://jira.transsion.com").rstrip("/")
JIRA_USER = os.getenv("JIRA_USER", "")
JIRA_PASS = os.getenv("JIRA_PASS", "")
INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET", "")

# 使用 *all 拉取全量字段（含所有自定义字段），确保 JSON 不遗漏任何信息
# POST /rest/api/2/search 的 fields 参数必须是数组，不能是字符串
JIRA_ISSUE_FIELDS = ["*all"]

# 自定义字段名称缓存（customfield_XXXXX → 人类可读名）
_FIELD_NAME_CACHE: dict[str, str] = {}

_ISSUE_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")
_BROWSE_RE = re.compile(r"/browse/([A-Z][A-Z0-9]+-\d+)", re.IGNORECASE)

# ── 批处理目录（统一落到 src/workspace/jira）──────────────────────────────────
_WORKSPACE_JIRA_DIR = _PROJECT_ROOT / "backend" / "workspace" / "jira"
_JIRA_RESULT_DIR = _WORKSPACE_JIRA_DIR / "jira_result"        # Phase 1 保存原始单据
_PICTURE_DIR = _WORKSPACE_JIRA_DIR / "picture"                # Phase 3 保存附件图片
_CHECK_RESULT_ROOT = _WORKSPACE_JIRA_DIR / "JIRA_check_result"  # 每次任务的结果根目录（run_id 子目录）
# 兼容历史目录（不再作为写入目标）
_QUALITY_RESULT_DIR = _WORKSPACE_JIRA_DIR / "jira_quality_result"
BATCH_SIZE = 5  # 每批质检条数


def _ensure_dirs() -> None:
    _JIRA_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    _PICTURE_DIR.mkdir(parents=True, exist_ok=True)
    _CHECK_RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    _QUALITY_RESULT_DIR.mkdir(parents=True, exist_ok=True)


def _latest_result_file() -> Path | None:
    """返回 jira_result/ 目录中按文件名降序排列的最新 JSON 文件。"""
    if not _JIRA_RESULT_DIR.exists():
        return None
    files = sorted(_JIRA_RESULT_DIR.glob("issues_*.json"), reverse=True)
    return files[0] if files else None


def _run_id_from_issues_file(file_name: str) -> str | None:
    """
    从 issues_YYYYMMDD_HHMMSS.json 解析 run_id=YYYYMMDD_HHMMSS。
    """
    m = re.search(r"issues_(\d{8}_\d{6})\.json$", file_name)
    return m.group(1) if m else None


def _current_run_id() -> str | None:
    latest = _latest_result_file()
    if latest is None:
        return None
    return _run_id_from_issues_file(latest.name)


def _run_dir(run_id: str) -> Path:
    """
    每次任务一个目录：JIRA_check_result/{run_id}/
    - batches/: Phase5 各批次 JSON
    - exports/: Phase6 输出给前端的汇总 JSON
    - meta.json: 记录本次任务的抓取信息与源 issues 文件
    """
    root = _CHECK_RESULT_ROOT / run_id
    (root / "batches").mkdir(parents=True, exist_ok=True)
    (root / "exports").mkdir(parents=True, exist_ok=True)
    return root


def _resolve_filter_to_jql(filter_id: str, auth: tuple[str, str]) -> tuple[str, str | None]:
    """
    将 Filter ID 转为可直接传给 /rest/api/2/search 的 JQL 字符串。

    优先策略：直接用 JQL `filter = {id}` 让 JIRA 搜索引擎内部展开，
    无需访问 /rest/api/2/filter/{id}（该端点要求 filter owner 权限，容易 403）。
    返回 (jql, None) 成功；(jql, warning) 附带提示。
    """
    jql = f"filter = {filter_id.strip()}"
    return jql, None


def _jira_auth() -> tuple[str, str] | None:
    if not JIRA_USER or not JIRA_PASS:
        return None
    return (JIRA_USER, JIRA_PASS)


def _load_field_name_map() -> dict[str, str]:
    """
    从 JIRA /rest/api/2/field 拉取全量字段元数据，构建 customfield_ID → 人类可读名 的映射。
    结果缓存到 _FIELD_NAME_CACHE，进程内只调用一次。
    """
    global _FIELD_NAME_CACHE
    if _FIELD_NAME_CACHE:
        return _FIELD_NAME_CACHE
    auth = _jira_auth()
    if not auth:
        return {}
    try:
        response = httpx.get(f"{JIRA_URL}/rest/api/2/field", auth=auth, timeout=30)
        response.raise_for_status()
        fields = response.json()
        for field in fields:
            _FIELD_NAME_CACHE[field.get("id", "")] = field.get("name", "")
    except Exception:
        pass
    return _FIELD_NAME_CACHE


def _normalize_field_name(field_id: str) -> str:
    return _load_field_name_map().get(field_id, field_id)


def _parse_issue_link_or_key(text: str) -> str | None:
    if match := _ISSUE_KEY_RE.search(text):
        return match.group(1)
    if match := _BROWSE_RE.search(text):
        return match.group(1)
    return None


def _get_jira_headers() -> dict[str, str]:
    return {"Content-Type": "application/json"}


def _post_json(
    url: str,
    payload: Any,
    auth: tuple[str, str] | None = None,
    timeout: int = 60,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        response = httpx.post(url, json=payload, auth=auth, timeout=timeout, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": str(exc), "url": url}


def _get_json(url: str, auth: tuple[str, str] | None = None, timeout: int = 60) -> dict[str, Any]:
    try:
        response = httpx.get(url, auth=auth, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": str(exc), "url": url}


def _safe_json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _safe_json_loads(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return {"error": "invalid json"}


def _save_json(file_path: Path, data: Any) -> Path:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path


def _load_json(file_path: Path) -> Any:
    if not file_path.exists():
        return None
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _format_time(ts: datetime | None = None) -> str:
    return (ts or datetime.now()).strftime("%Y%m%d_%H%M%S")


def _format_issue(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": issue.get("key", ""),
        "link": issue.get("self", ""),
        "summary": issue.get("fields", {}).get("summary", ""),
        "issue_type": issue.get("fields", {}).get("issuetype", {}).get("name", ""),
        "priority": issue.get("fields", {}).get("priority", {}).get("name", ""),
        "status": issue.get("fields", {}).get("status", {}).get("name", ""),
    }


def _normalize_issue(issue: dict[str, Any]) -> dict[str, Any]:
    """
    将 JIRA REST API 原始 issue 对象规范化为可读的扁平结构，
    与 issues_20260509_093450.json 格式保持一致。
    """
    fields = issue.get("fields") or {}
    key = issue.get("key", "")
    field_map = _load_field_name_map()

    # ── 附件 ──────────────────────────────────────────────────────────────────
    attachments = []
    for att in fields.get("attachment") or []:
        attachments.append({
            "filename": att.get("filename", ""),
            "mimeType": att.get("mimeType", ""),
            "size": att.get("size", 0),
            "content": att.get("content", ""),
        })

    # ── 评论 ──────────────────────────────────────────────────────────────────
    comments = []
    for c in (fields.get("comment") or {}).get("comments") or []:
        author_obj = c.get("author") or {}
        display = author_obj.get("displayName") or author_obj.get("name", "")
        comments.append({
            "author": display,
            "created": c.get("created", ""),
            "body": c.get("body", ""),
        })

    # ── 自定义字段 ────────────────────────────────────────────────────────────
    custom_fields: dict[str, Any] = {}
    for fid, fval in fields.items():
        if not fid.startswith("customfield_"):
            continue
        # 跳过空值字段，保持与历史格式一致
        if fval is None:
            continue
        fname = field_map.get(fid, fid)
        custom_fields[fname] = fval

    # ── 辅助提取函数 ──────────────────────────────────────────────────────────
    def _name(obj: Any) -> str | None:
        if isinstance(obj, dict):
            return obj.get("name") or obj.get("displayName") or obj.get("value")
        return None

    def _names(lst: Any) -> list[str]:
        if not isinstance(lst, list):
            return []
        return [_name(x) or str(x) for x in lst if x]

    return {
        "key": key,
        "link": f"{JIRA_URL}/browse/{key}",
        "summary": fields.get("summary", ""),
        "description": fields.get("description") or "",
        "environment": fields.get("environment") or "",
        "status": _name(fields.get("status")) or "",
        "issuetype": _name(fields.get("issuetype")) or "",
        "priority": _name(fields.get("priority")) or "",
        "resolution": _name(fields.get("resolution")),
        "reporter": _name(fields.get("reporter")) or "",
        "assignee": _name(fields.get("assignee")),
        "project": _name(fields.get("project")) or "",
        "labels": fields.get("labels") or [],
        "fixVersions": _names(fields.get("fixVersions")),
        "affectsVersions": _names(fields.get("versions")),
        "components": _names(fields.get("components")),
        "attachments": attachments,
        "comments": comments,
        "created": fields.get("created") or "",
        "updated": fields.get("updated") or "",
        "duedate": fields.get("duedate"),
        "custom_fields": custom_fields,
    }


def parse_jira_links_and_keys(text: str) -> dict[str, Any]:
    """Parse JIRA issue keys or browse URLs from a text string."""
    keys = []
    for token in re.split(r"[\s,;]+", text.strip()):
        if parsed := _parse_issue_link_or_key(token):
            keys.append(parsed)
    return {"keys": keys}


def search_jira_by_jql(jql: str) -> str:
    """Search JIRA with the given JQL and return the API JSON result."""
    auth = _jira_auth()
    if auth is None:
        return _safe_json_dumps({"error": "Missing JIRA credentials"})
    url = f"{JIRA_URL}/rest/api/2/search"
    payload = {"jql": jql, "fields": ["key", "summary", "status", "priority", "assignee", "reporter"], "maxResults": 50}
    return _safe_json_dumps(_post_json(url, payload, auth=auth))


def fetch_jira_issue_json(issue_key: str) -> str:
    """Fetch raw JIRA issue JSON for a given issue key."""
    auth = _jira_auth()
    if auth is None:
        return _safe_json_dumps({"error": "Missing JIRA credentials"})
    url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}" 
    return _safe_json_dumps(_get_json(url, auth=auth))


def phase1_fetch_and_save_jira_issues(input_text: str) -> str:
    """Fetch JIRA issues from input text and save them locally as JSON."""
    _ensure_dirs()
    auth = _jira_auth()
    if auth is None:
        return _safe_json_dumps({"error": "Missing JIRA credentials"})

    # 简化：如果用户直接给出了 JQL URL 或 Filter URL，则提取其中的 JQL
    if "/issues/?jql=" in input_text:
        jql = input_text.split("/issues/?jql=", 1)[-1]
        jql = jql.replace("%20", " ")
    elif "filter=" in input_text:
        jql = input_text
    else:
        jql = input_text

    # 1. 获取单据列表（使用 *all 拉取全量字段，确保不遗漏任何信息）
    search_payload = {"jql": jql, "fields": JIRA_ISSUE_FIELDS, "maxResults": 500}
    data = _post_json(f"{JIRA_URL}/rest/api/2/search", search_payload, auth=auth)
    if data.get("error"):
        return _safe_json_dumps(data)

    raw_issues = data.get("issues", [])
    run_id = _format_time()
    fetch_time = datetime.now().isoformat()

    # 2. 规范化每条 issue，转换为可读的扁平结构
    normalized_issues = [_normalize_issue(issue) for issue in raw_issues]
    keys = [issue["key"] for issue in normalized_issues]

    # 3. 构建与旧版格式一致的顶层结构
    result_data = {
        "fetch_time": fetch_time,
        "query": f"{JIRA_URL}/issues/?{input_text}" if not input_text.startswith("http") else input_text,
        "total": data.get("total", len(raw_issues)),
        "fetched": len(normalized_issues),
        "keys": keys,
        "issues": normalized_issues,
    }
    _save_json(_JIRA_RESULT_DIR / f"issues_{run_id}.json", result_data)
    return _safe_json_dumps({"run_id": run_id, "fetched": len(normalized_issues), "filename": f"issues_{run_id}.json"})


def phase2_load_batch_info() -> str:
    """Load the latest saved JIRA result and compute batch planning info."""
    latest = _latest_result_file()
    if latest is None:
        return _safe_json_dumps({"error": "jira_result/ 目录为空，请先调用 phase1_fetch_and_save_jira_issues 拉取单据"})
    data = _load_json(latest)
    if not isinstance(data, dict):
        return _safe_json_dumps({"error": "无法读取最新单据文件"})

    issues = data.get("issues", [])
    batches = [issues[i : i + BATCH_SIZE] for i in range(0, len(issues), BATCH_SIZE)]
    run_id = _run_id_from_issues_file(latest.name) or _format_time()
    result = {"run_id": run_id, "total": len(issues), "batch_count": len(batches), "batch_size": BATCH_SIZE}
    return _safe_json_dumps(result)


def phase3_download_attachments(batch_index: int) -> str:
    """Download image attachments for the specified batch of JIRA issues."""
    latest = _latest_result_file()
    if latest is None:
        return _safe_json_dumps({"error": "jira_result/ 目录为空，请先执行 Phase 1"})
    data = _load_json(latest)
    if not isinstance(data, dict):
        return _safe_json_dumps({"error": "无法读取最新单据文件"})

    auth = _jira_auth()
    issues = data.get("issues", [])
    batch = issues[batch_index * BATCH_SIZE : (batch_index + 1) * BATCH_SIZE]
    downloaded = []
    for issue in batch:
        key = issue.get("key", "")
        # 兼容规范化后的扁平结构（attachments 直接在 issue 下）和旧版原始结构（fields.attachment）
        attachments = issue.get("attachments") or issue.get("fields", {}).get("attachment", [])
        issue_dir = _PICTURE_DIR / key
        issue_dir.mkdir(parents=True, exist_ok=True)
        for attachment in attachments:
            filename = attachment.get("filename", "")
            content_url = attachment.get("content", "")
            if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            try:
                resp = httpx.get(content_url, auth=auth, timeout=60)
                if resp.status_code == 200:
                    file_path = issue_dir / filename
                    file_path.write_bytes(resp.content)
                    downloaded.append(str(file_path))
            except Exception:
                pass

    return _safe_json_dumps({"batch_index": batch_index, "downloaded": downloaded})


def phase4_analyze_bug_level(issue_key: str) -> str:
    """
    Use multimodal LLM to analyze downloaded images for a JIRA issue.
    Extracts the Severity field (Critical/Blocker/Major) from Bug Level Calculation Table screenshots.
    All images for the issue are sent in a single request so the model can find the table across any image.
    Returns has_bug_level_image=False if no relevant image is found or recognition fails.
    """
    issue_dir = _PICTURE_DIR / issue_key
    if not issue_dir.exists():
        return _safe_json_dumps({"issue_key": issue_key, "has_bug_level_image": False})

    images = list(issue_dir.glob("*.png")) + list(issue_dir.glob("*.jpg")) + list(issue_dir.glob("*.jpeg"))
    if not images:
        return _safe_json_dumps({"issue_key": issue_key, "has_bug_level_image": False})

    # 尝试调用多模态模型识别图片（从 settings 读取，与 image_llm_model 保持一致）
    try:
        from app.core.config import settings as _settings
        image_api_key = _settings.IMAGE_PARSER_API_KEY
        _VISION_API_BASE = _settings.IMAGE_PARSER_API_BASE
        _VISION_MODEL = _settings.IMAGE_PARSER_MODEL
    except Exception:
        image_api_key = os.getenv("IMAGE_PARSER_API_KEY", "")
        _VISION_API_BASE = os.getenv("IMAGE_PARSER_API_BASE", "https://ark.cn-beijing.volces.com/api/v3")
        _VISION_MODEL = os.getenv("IMAGE_PARSER_MODEL", "doubao-seed-1-6-vision-250815")

    if not image_api_key:
        # 无多模态 API Key，跳过 ZT-6 检查
        return _safe_json_dumps({
            "issue_key": issue_key,
            "has_bug_level_image": False,
            "skip_reason": "IMAGE_PARSER_API_KEY not configured, skipping ZT-6 multimodal check",
        })

    import base64

    prompt = (
        "You are analyzing JIRA bug report screenshots. "
        f"There are {len(images)} image(s) attached. "
        "Look through ALL images for a Bug Level Calculation Table (Bug等级计算表). "
        "If found in ANY image, extract ONLY the 'Severity' field value (one of: Critical, Blocker, Major). "
        "Also extract the 'Probability of occurrence' field value if present (one of: Must, Often, Occasional, Once, SingleMachine). "
        "Also report which image index (0-based) contained the table. "
        "Respond in JSON format: "
        '{"has_bug_level_table": true/false, "severity": "Critical|Blocker|Major|null", '
        '"probability": "Must|Often|Occasional|Once|SingleMachine|null", "source_image_index": 0}. '
        "If NONE of the images contain a Bug Level Calculation Table, respond: "
        '{"has_bug_level_table": false, "severity": null, "probability": null, "source_image_index": null}.'
    )

    try:
        # 将所有图片一次性放入同一条消息，让模型扫描全部图片
        content_parts = []
        for image_path in images:
            image_bytes = image_path.read_bytes()
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            suffix = image_path.suffix.lower().lstrip(".")
            mime = "image/jpeg" if suffix in ("jpg", "jpeg") else "image/png"
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64_image}"},
            })
        content_parts.append({"type": "text", "text": prompt})

        payload = {
            "model": _VISION_MODEL,
            "messages": [{"role": "user", "content": content_parts}],
            "max_tokens": 1024,
        }
        headers = {
            "Authorization": f"Bearer {image_api_key}",
            "Content-Type": "application/json",
        }
        resp = httpx.post(
            f"{_VISION_API_BASE}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()

        # 去除可能的 markdown 代码块包裹
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())

        if parsed.get("has_bug_level_table") and parsed.get("severity"):
            src_idx = parsed.get("source_image_index")
            src_name = images[src_idx].name if src_idx is not None and 0 <= src_idx < len(images) else "unknown"
            return _safe_json_dumps({
                "issue_key": issue_key,
                "has_bug_level_image": True,
                "severity": parsed["severity"],
                "probability": parsed.get("probability"),
                "source_image": src_name,
                "bug_level_summary": f"Severity={parsed['severity']}, Probability={parsed.get('probability', 'N/A')}",
            })
    except Exception:
        pass

    # 所有图片均未识别到 Bug 等级计算表
    return _safe_json_dumps({
        "issue_key": issue_key,
        "has_bug_level_image": False,
        "skip_reason": "No Bug Level Calculation Table found in any attachment image",
    })
def phase3_fetch_batch_for_inspection(batch_index: int) -> str:
    """Fetch the issue batch data for manual inspection."""
    latest = _latest_result_file()
    if latest is None:
        return _safe_json_dumps({"error": "jira_result/ 目录为空，请先执行 Phase 1"})
    data = _load_json(latest)
    if not isinstance(data, dict):
        return _safe_json_dumps({"error": "无法读取最新单据文件"})

    issues = data.get("issues", [])
    batch = issues[batch_index * BATCH_SIZE : (batch_index + 1) * BATCH_SIZE]
    return _safe_json_dumps({"batch_index": batch_index, "issues": batch})


def phase3_save_batch_quality_result(batch_index: int, results_json: str) -> str:
    """Save quality inspection results for a specific batch."""
    run_id = _current_run_id()
    if run_id is None:
        return _safe_json_dumps({"error": "无法确定当前 run_id"})
    run_dir = _run_dir(run_id)
    file_path = run_dir / "batches" / f"batch_{batch_index}_{_format_time()}.json"
    return str(_save_json(file_path, _safe_json_loads(results_json)))


def phase4_generate_quality_report() -> str:
    """Generate a markdown quality report from saved batch results."""
    run_id = _current_run_id()
    if run_id is None:
        return _safe_json_dumps({"error": "无法确定当前 run_id"})
    run_dir = _run_dir(run_id)
    batch_files = sorted(run_dir.joinpath("batches").glob("batch_*.json"))
    report_lines = ["# JIRA 质检汇总报告", ""]
    for batch_file in batch_files:
        batch_data = _load_json(batch_file) or {}
        report_lines.append(f"## 批次 {batch_file.stem}")
        for issue in batch_data:
            report_lines.append(f"- {issue.get('key', '')}: compliance_ok={issue.get('compliance_ok', False)}")
    report_path = run_dir / "exports" / "quality_report.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return str(report_path)


def phase6_export_check_result() -> str:
    """Export the aggregated batch check results to a JSON file."""
    run_id = _current_run_id()
    if run_id is None:
        return _safe_json_dumps({"error": "无法确定当前 run_id"})
    run_dir = _run_dir(run_id)
    batch_files = sorted(run_dir.joinpath("batches").glob("batch_*.json"))
    all_results = []
    for batch_file in batch_files:
        batch_data = _load_json(batch_file) or []
        all_results.extend(batch_data)
    export_path = run_dir / "exports" / "check_result.json"
    return str(_save_json(export_path, all_results))


def post_jira_issue_comment(issue_key: str, comment_text: str) -> str:
    """Post a comment to a JIRA issue using the configured JIRA credentials."""
    auth = _jira_auth()
    if auth is None:
        return _safe_json_dumps({"error": "Missing JIRA credentials"})
    issue_key = _parse_issue_link_or_key(issue_key) or issue_key
    url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}/comment"
    payload = {"body": comment_text}
    return _safe_json_dumps(_post_json(url, payload, auth=auth))


def save_jira_audit_to_database(audit_data: str) -> str:
    """Send JIRA audit data to the local FastAPI internal audit endpoint."""
    if not INTERNAL_API_SECRET:
        return _safe_json_dumps({"error": "Missing internal API secret"})
    headers = {"X-Internal-Secret": INTERNAL_API_SECRET}
    return _safe_json_dumps(
        _post_json(
            f"{FASTAPI_BASE_URL}/internal/jira-audits",
            {"secret": INTERNAL_API_SECRET, "data": _safe_json_loads(audit_data)},
            timeout=30,
            headers=headers,
        )
    )


def read_local_file(file_path: str) -> str:
    """Read the content of a local file and return it as a string.
    Supports absolute paths and paths relative to the project root.
    Use this tool to read quality reports, check results, or any other
    locally saved files (e.g. quality_report.md, check_result.json).
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = _PROJECT_ROOT / path
    if not path.exists():
        return _safe_json_dumps({"error": f"File not found: {path}"})
    try:
        text = path.read_text(encoding="utf-8")
        return _safe_json_dumps({"file_path": str(path), "content": text})
    except Exception as exc:
        return _safe_json_dumps({"error": str(exc), "file_path": str(path)})
