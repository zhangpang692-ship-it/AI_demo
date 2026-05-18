# JIRA 规范巡检技能（jira-inspection）

## 技能概述

本技能将 JIRA 规范巡检的**完整能力**内嵌为一个独立 Skill，包含：

1. **六阶段固化执行流程**（原 `jira-inspection` 技能）
2. **提单/关单规范全文**（原 `jira-ticket-standard` 技能，V1.0，April 2026）
3. **工具代码**（`code/jira_tools.py`）

适用范围：海外 AI 测试团队（EE1、尼日利亚、肯尼亚、印度、印度尼西亚），项目库 SRDAIV。

---

## 依赖说明

### Python 包依赖

| 包名 | 用途 |
|------|------|
| `httpx` | JIRA REST API 调用（Basic Auth）、多模态图片上传 |
| `langchain-core` | `@tool` 装饰器（`langchain_core.tools.tool`） |
| `python-dotenv` | 从 `.env` 加载环境变量 |
| `deepagents` | Agent 框架（`create_deep_agent`、`FilesystemBackend`、`SkillsMiddleware`） |
| `langchain` | `init_chat_model` 初始化 LLM |

### 环境变量依赖（`.env`）

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `JIRA_URL` |  | JIRA 实例地址，如 `http://jira.transsion.com` |
| `JIRA_USER` |  | JIRA 用户名（Basic Auth） |
| `JIRA_PASS` |  | JIRA 密码（Basic Auth） |
| `IMAGE_PARSER_API_KEY` | （ZT-6） | 多模态视觉模型 API Key（用于 Bug 等级截图识别） |
| `IMAGE_PARSER_API_BASE` | 可选 | 视觉模型 API Base，默认 `https://ark.cn-beijing.volces.com/api/v3` |
| `IMAGE_PARSER_MODEL` | 可选 | 视觉模型名，默认 `doubao-seed-1-6-vision-250815` |
| `FASTAPI_BASE_URL` | 可选 | 内部 FastAPI 地址，默认 `http://127.0.0.1:8080`（用于入库） |
| `INTERNAL_API_SECRET` | 可选 | 内部 API 鉴权密钥（用于 `save_jira_audit_to_database`） |

### 本地文件系统依赖

工具代码自动在 `src/workspace/jira/` 下创建以下目录（无需手动创建）：

| 目录 | 用途 |
|------|------|
| `jira/jira_result/` | Phase 1 保存原始单据 JSON |
| `jira/picture/{issue_key}/` | Phase 3 保存图片附件 |
| `jira/JIRA_check_result/{run_id}/batches/` | Phase 5 各批次质检结果 |
| `jira/JIRA_check_result/{run_id}/exports/` | Phase 6 汇总报告与导出 JSON |

### 工具代码

工具实现位于 `code/jira_tools.py`，提供以下可调用工具函数：

| 工具函数 | 阶段 | 说明 |
|----------|------|------|
| `phase1_fetch_and_save_jira_issues(input_text)` | Phase 1 | 拉取 JIRA 单据并保存到本地 |
| `phase2_load_batch_info()` | Phase 2 | 读取最新单据文件，返回批次规划 |
| `phase3_download_attachments(batch_index)` | Phase 3 | 下载指定批次的图片附件 |
| `phase4_analyze_bug_level(issue_key)` | Phase 4 | 多模态识别 Bug 等级截图 Severity |
| `phase3_fetch_batch_for_inspection(batch_index)` | Phase 5 | 读取批次字段数据用于质检 |
| `phase3_save_batch_quality_result(batch_index, results_json)` | Phase 5 | 保存批次质检结果 |
| `phase4_generate_quality_report()` | Phase 6 | 生成 Markdown 汇总报告 |
| `phase6_export_check_result()` | Phase 6 | 导出前端展示 JSON |
| `post_jira_issue_comment(issue_key, comment_text)` | Phase 5 | 对不合规单据发表 JIRA 评论 |
| `save_jira_audit_to_database(audit_data)` | 可选 |  入库操作，须用户明确批准 |
| `read_local_file(file_path)` | 辅助 | 读取本地文件内容 |

---

## 六阶段固化执行流程

### Phase 1  拉取并保存单据

调用 `phase1_fetch_and_save_jira_issues`，传入用户提供的原始输入（支持 Filter URL / JQL URL / JQL 字符串 / browse 链接 / 裸 key）。

- 工具自动将所有单据完整字段保存到本地 `jira_result/` 目录。
- 告知用户：文件名、总条数（`fetched`）。若返回 `error`，告知用户并终止。

---

### Phase 2  确认待检批次

调用 `phase2_load_batch_info`，读取最新文件，获取批次规划。

- 向用户报告：共 **N** 条单据，分 **M** 批（每批 5 条），即将开始质检。

---

### Phase 3  下载批次附件图片（循环，batch_index 从 0 到 M-1）

**每批质检前**，先调用 `phase3_download_attachments(batch_index=i)`，下载本批所有单据的 PNG/JPG 附件到 `picture/{issue_key}/` 目录。

- 告知用户：下载了多少张图片、哪些单据有附件。
- 若某单据无图片附件，继续执行下一步，不阻断流程。

---

### Phase 4  多模态识别 Bug 等级（逐条，本批每条单据都执行）

**对本批中每条单据**，调用 `phase4_analyze_bug_level(issue_key=key)`，用多模态大模型识别该单据已下载的**全部图片**，提取 Bug 等级计算表中的 Severity 字段（Critical / Blocker / Major），用于后续 ZT-6 检查。

 **关键规则**：
- 返回结果**仅作为当前这条单据质检的辅助信息**，严禁跨单据使用。
- 开始质检**下一条**单据时，**必须清除上一条的图片识别结果**，重新调用获取新结果。
- 若工具返回 `has_bug_level_image: false`，说明图片中无 Bug 等级信息，质检时忽略 ZT-6 此项。

---

### Phase 5  逐条质检 + 发表评论

对本批每条单据，综合使用：
1. `phase3_fetch_batch_for_inspection(batch_index=i)` 中的字段数据
2. `phase4_analyze_bug_level` 返回的 `bug_level_summary`（仅用于当前条）

按 **4.1**（提单检查清单）与 **4.2**（关单检查清单）逐项核对，**零容忍项（ZT-1 ~ ZT-6）优先检查**：

- **ZT-6 专项判断**：将图片识别到的 **Severity 值**（如 `Critical`）与 JIRA **Priority 字段**比对（二者必须一致）；不一致时检查 Comments 是否有备注说明原因。注意：图中 Probability of occurrence（频率）是 ZT-2 的检查范围，ZT-6 只看 Severity vs Priority。

** 强制要求发表评论**：对于**不合规单据**（`compliance_ok == false`），**必须**立即调用 `post_jira_issue_comment(issue_key, comment_text)` 在 JIRA 上发表评论。内容应遵循 **4.3** 格式规范（分条说明缺陷、规范条文、整改方案、整改期限），使用英文。

完成本批所有单据（含评论）后，调用 `phase3_save_batch_quality_result(batch_index=i, results_json=...)` 保存。

`results_json` 格式（每条单据一个对象）：
```json
[
  {
    "key": "PROJ-123",
    "link": "http://jira.transsion.com/browse/PROJ-123",
    "country": "Kenya",
    "reporter": "Robin Namweya Sisungo",
    "priority": "Critical",
    "status": "SUBMITTED",
    "compliance_ok": false,
    "problems": [
      {"field": "Risk/Frequency 三处不一致", "description": "Summary【Must】vs Risk字段must vs 图片识别10/10一致，但Priority为Critical不一致", "ref": "ZT-6/1.8"},
      {"field": "Environment", "description": "缺少 Device ID", "ref": "ZT-5/1.1"}
    ],
    "suggestions": [
      "将 Priority 调整为 Block/Major 使其与 Must 对应，或在 Comment 中说明不一致原因",
      "在 Environment 字段补充 Device ID（通过 adb devices 获取）"
    ],
    "comment_posted": true
  }
]
```

完成后告知用户进度，如「第 1/3 批完成，共 5 条，发现 2 条不合规（含 1 条 ZT-6 Bug等级不一致），已发表 2 条评论」。

---

### Phase 6  汇总报告

所有批次完成后：
1. 调用 `phase4_generate_quality_report` 生成 Markdown 汇总报告
2. 调用 `phase6_export_check_result` 导出前端展示 JSON

向用户展示汇总统计：总条数、合规条数、不合规条数、ZT 违规分布。

---

## 0 零容忍缺陷清单（Zero-Tolerance Violations）

> **以下六类问题属于「零容忍」级别，发现任意一条即判定为严重不合规，必须立即反馈并要求整改。**

| # | 缺陷类型 | 判定依据 | 条款 |
|---|----------|---------|------|
| ZT-1 | **Summary 缺少关键标签** | 标题中缺少以下任意一项：环境信息（`【TestEnvironment】` 或 `【Test Environment】`）、版本信息（`【MainVersion】`/`【DetailedVersion】` 或等价版本号标签如 `【V5.4.2】`）、国家信息（`【Country】`）、频率信息（`【Frequency】`）。合法国家标签：`【Indonesia】`、`【India】`、`【Nigeria】`、`【Kenya】`、**`【EE1】`（代表俄罗斯，是合法国家标签，不得误判）** | 1.2 |
| ZT-2 | **Risk 三处不一致** | `【Frequency】` 标题标签、Risk 字段值、Description 正文频率描述三者必须完全一致 | 1.4 |
| ZT-3 | **Component/s 不在允许范围** | AI-VA 专项单据 Component/s 只允许：`AI-VA专项-通用`、`AI-VA专项-ASR`、`AI-VA专项-TTS`、`AI-VA专项-NLU`、`AI-VA专项-UX` | 1.7 |
| ZT-4 | **Description 缺少关键内容** | 缺少以下任意一项：Steps to Reproduce、Expected Result、Actual Result、LogAddress/Log Link、VideoLink | 1.5 |
| ZT-5 | **Environment 字段缺少设备标识** | Environment 字段必须包含手机 Device ID（通过 `adb devices` 获取） | 1.1 |
| ZT-6 | **Bug 等级截图 Severity 与 Priority 字段不一致且无备注说明** | 截图中的 Severity 字段须与 JIRA Priority 字段完全一致；若不一致且 Comment 中无说明，则视为异常 | 1.8 |

---

## 一、提单规范（Ticket Submission Standards）

### 1.1 必填字段一览

| 字段名 | 填写规则 | 备注 |
|--------|---------|------|
| **Project** | 智慧助手 (SRDAIV) | 复制粘贴至输入框 |
| **IssueType** | Bug | 固定选 Bug |
| **Summary（标题）** | 按标题格式模板填写，含全部标签 | 见 1.2 |
| **Priority（优先级）** | Blocker / Block(A) / Critical(B) / Major(C) | 见 1.3 |
| **Environment** | 必须包含测试环境和必要平台信息 |  **零容忍 ZT-5** |
| **Risk（频率）** | Must / Often / Occasional / Once / SingleMachine，须与标题 `【Frequency】` 及 Description 正文**三处完全一致** |  **零容忍 ZT-2** |
| **IssueSource** | 内测(TestCase) 或 内测(FreeTest) | 二选一 |
| **IssueCategory** | Functions / Experience / Translation / UI | 四选一 |
| **IssueNature** | New issues | 固定填 New issues |
| **Component/s** | AI-VA 专项只允许五个值之一 |  **零容忍 ZT-3** |
| **Reporter** | 提单人自己 | |
| **Assignee** | 按项目分配，**不纳入合规性检查范围** |  |
| **Affects Version/s** | 详细 APK 版本号 | |
| **Description（描述）** | 含前提条件、复现步骤、实际结果、预期结果（英文书写） | 见 1.5 |
| **Attachment（附件）** | 截图 + 视频 + 日志 + Bug 等级规范截图 | 见 1.6 |
| **TCID** | `/` | 固定填 `/` |

---

### 1.2 标题格式规范

**标准格式**：
```
【Environment】【Project】【MainVersion】【DetailedVersion】【Country】【FunctionName】【Frequency】 + Bug 描述
```

**示例（Good Case）**：
```
【TestEnvironment】【Ella】【v4.7.1】【Ella4.7.1.009】【Indonesia】【RealTimeCall】【Must】Ella didn't give a response on RealTimeCall
```

> **版本标签说明**：`【MainVersion】` 和 `【DetailedVersion】` 是标准名称，但实际提单中**允许直接使用版本号**，例如 `【V5.4.2】`。只要标题中存在版本号格式的标签，即视为版本信息已填写，**不触发 ZT-1**。

**标签说明**：

| 标签 | 填写规则 |
|------|---------|
| `【Environment】` | 必须在标题**开头**，只允许 `【TestEnvironment】` 或 `【Test Environment】`、`【ProductionEnvironment】` 或 `【Production Environment】` |
| `【Project】` | 项目名称（如 `【Ella】`、`【Folax】`） |
| `【MainVersion】` / `【DetailedVersion】` | 版本信息；**等价写法**：直接使用版本号标签，如 `【V5.4.2】`、`【v4.7.1】` |
| `【Country】` | 合法值：`【Indonesia】`、`【India】`、`【Nigeria】`、`【Kenya】`、`【EE1】` |
| `【FunctionName】` | 涉及功能名称 |
| `【Frequency】` | Must / Often / Occasional / Once / SingleMachine（必填） |

**常见标题违规（Bad Case）**：
- 环境格式描述错误（如缩写）
- 标题中完全没有版本号信息（无 `【MainVersion】`/`【DetailedVersion】` 也无 `【VX.X.X】` 格式标签）
- 缺失国家、频率标签
- 标签顺序错乱
- Bug 描述不清晰（如仅写 "Ella doesn't work"）

**特定场景需额外增加中英文标签**：

| Bug 类型 | 需加 CN 标签 |
|---------|------------|
| 翻译类（所有国家） | `【翻译】` |
| 健康饮食（所有国家） | `【健康饮食】` |
| 购物助手（所有国家） | `【购物助手】` |
| 回归测试（所有国家） | `【RT】` |
| EE1 上市问题 | `【EE1上市问题】` |
| TTS 算法测试（EE1/INDO） | `【TTS算法测试】` |
| IP 直连测试（NG/EE1） | `【IP直连测试】` |

---

### 1.3 优先级（Priority）规范

| 等级 | 定义 |
|------|------|
| **Blocker** | 最高严重度，阻塞测试/发版流程 |
| **Block（A）** | Crash、ANR 宕机，或影响后续流程 |
| **Critical（B）** | 功能/服务无法使用，严重影响线上用户 |
| **Major（C）** | 功能未按需求实现 |

**规则**：Priority 填写上述任意一项均合规；**不要求与标题 `【Frequency】` 标签强制对应**。

---

### 1.4 Risk（频率）规范

| 级别 | 说明 |
|------|------|
| **Must** | 必现（5/5、10/10、15/15、20/20） |
| **Often** | 频繁复现 |
| **Occasional** | 偶发 |
| **Once** | 仅复现一次 |
| **SingleMachine** | 单机出现 |

** 零容忍规则（ZT-2）：Risk 必须在以下三处完全一致：**

| # | 位置 | 示例（Must） |
|---|------|------------|
| 1 | Summary 标题的 `【Frequency】` 标签 | `【Must】` |
| 2 | Risk 字段值 | `must` |
| 3 | Description 正文中的频率描述 | `Test Count: 5/5` 或文字说明 `Must` |

**频率标签与 Test Count 对应关系**：
- **Must**：必现，通常 `5/5`、`10/10`、`15/15`、`20/20`
- **Often**：频繁出现，复现次数高但不一定 100%
- **Occasional**：偶发，出现频率较低
- **Once**：仅出现一次
- **SingleMachine**：仅单机出现

**判定方式**：
- 提取 Summary 中 `【...】` 标签内的频率值
- 与 Risk 字段值对比（大小写不敏感）
- 与 Description 中出现的频率表述对比
- 三者若不一致，标记 ZT-2 违规

---

### 1.5 描述（Description）规范

描述**必须用英文书写**，必须包含以下六部分（ 标注为零容忍项）：

```
A) Preconditions
B) Steps to Reproduce   ZT-4
C) Actual Result        ZT-4
D) Expected Result      ZT-4
E) VideoLink            ZT-4
F) LogAddress           ZT-4
```

**判定关键字**（大小写不敏感）：
- Steps to Reproduce / Operation step
- Actual Result / Test Results
- Expected Result / Expected results
- VideoLink / Video Link / Video:
- LogAddress / Log Address / Log Link

**违规示例**：描述仅写 "The function is broken, please fix" → 不合规（缺少 B/C/D/E/F 全部内容）。

---

### 1.6 附件（Attachment）规范

| 附件类型 | 要求 | 注意事项 |
|---------|------|---------|
| 截图 / GIF | 清晰标注问题位置（箭头/圆圈），提供实际 vs 预期对比截图 | 不可模糊，必须能直观看出问题 |
| 视频 / 录屏 | 上传链接，不可 zip，须可在线观看；视频中标注时间节点 | — |
| 日志 | < 10 MB 直传；> 10 MB 可 zip 但须可下载 | 云盘权限须设为"可下载" |
| Bug 等级规范截图 | 必须附上 Bug 严重程度等级计算表截图 | — |

**重要**：附件上传至云盘后，须在**父文件夹**设置"任何人可查看/下载"权限，否则开发团队无法访问——此项为高频违规点。

---

### 1.7 Component/s 规范（ 零容忍 ZT-3）

AI-VA 专项单据的 Component/s 字段**只允许**填写以下五个选项之一：

| 可选值 | 适用场景 |
|--------|---------|
| `AI-VA专项-通用` | 通用 AI 语音助手问题 |
| `AI-VA专项-ASR` | 语音识别相关问题 |
| `AI-VA专项-TTS` | 语音合成相关问题 |
| `AI-VA专项-nlu` | 自然语言理解相关问题 |
| `AI-VA专项-UX` | 用户体验相关问题 |

**判定规则**：
- Component/s 字段为空 → **不合规**
- Component/s 填写的值不在上述五个选项内 → **不合规**
- Component/s 填写了多个值但均在允许列表内 → **合规**

---

### 1.8 Bug 等级截图 Severity 与 Priority 一致性规范（ 零容忍 ZT-6）

| 截图字段 | 含义 | 对应 JIRA 字段 | 负责检查项 |
|---------|------|--------------|---------|
| **Severity** | 严重度（Critical / Blocker / Major） | **Priority 字段** |  **ZT-6** |
| **Probability of occurrence** | 频率 | Risk 字段 + `【Frequency】` 标签 | ZT-2 |

**ZT-6 判定规则**：
1. 使用多模态模型从 Description 附图中提取 **Severity** 字段的值（Critical / Blocker / Major）。
2. 与 JIRA **Priority 字段**进行比对：
   - **一致** → ZT-6 合规。
   - **不一致** → 检查 Comments 中是否有备注说明原因。
     - **有备注** → 合规（记录备注内容）。
     - **无备注** → ⚠️ **ZT-6 不合规**，必须反馈要求补充说明。
3. 若图片中无 Severity 字段（即非 Bug 等级计算表），则跳过 ZT-6 检查，不判定不合规。

---

## 二、关单规范（Ticket Closure & Verification Standards）

### 2.1 RESOLVED  VERIFIED 验证规范

验证评论必须按以下格式填写：
```
APK Version:
Test Steps:
Test Count: ?/?
Test Result: PASSED / NOT PASSED
```

- **PASSED** → 操作 Close（A 类问题须流转给 TL 二次审核后关闭）。
- **NOT PASSED** → 操作 Reopen，在 Comment 说明失败现象、版本、步骤，附 Log/视频。

**A 类/必解问题额外要求**：
- RESOLVED 后须由 TL（Opener）二次审核方可流转 VERIFIED。
- VERIFIED 通过后须经 TL 二次审核方可关闭。

**概率性问题**：必须按验证轮次要求执行，不得减少验证次数。

### 2.2 Reopen 规范

- Reopen 时须在 Comment 区清晰写明原因。
- **禁止**在原 Ticket 上叠加描述新问题新问题须单独提单并 Link 原单。

### 2.3 CLOSED 状态规范

- CLOSED 是流程终态，关闭后**不可 Reopen**。
- 关闭后发现新 Bug  新建单 + Link 原单。

### 2.4 开发 Reject（驳回）时的处理规范

- 开发 Reject 后，单流转至 RESOLVED（non-positive），由 TL 审核。
- 如同意 Reject → 无需操作，等待 TL 关闭。
- 如不同意 → 在 Comment 留反驳意见（日志、截图、参照标准等依据），@TL，由 TL 决定 Reopen 或关闭。
- 双方无法达成一致 → 提交 CCB 决策。
- A 类/必解问题不允许 Reject，须 CCB 决策后降级再操作。
- 操作 Reject 时 Comment 必须备注 Reject 原因；若为重复单须注明主单号；若为新需求须注明需求单号。
- 场测（海外）问题的 Comment **须用英文备注**。
- TL 关闭 Reject 单前，必须完成与 Reporter 的沟通确认。

### 2.5 CannotReproduce（无法复现）处理规范

| 场景 | 处理方式 |
|------|---------|
| Must（必现）问题被标 CannotReproduce | 原则上不允许；要求开发走 Retest 流程后再复现 |
| 概率性问题 | 确认开发复测次数是否满足要求；满足且未复现 → 可接受，TL 关闭 |
| Retest 失败（仍能复现） | 操作 Reopen，附最新复现 Log 和步骤 |
| 已 Closed 的 CannotReproduce 单再次复现 | 新建单 + Link 原单，**禁止 Reopen** |
| A 类/必解问题 | 不允许直接操作无法复现，须 CCB 决策降级后再操作 |

### 2.6 DUPLICATED（置重）处理规范

- **只能置重到同库内、创建时间更早的单；禁止跨库置重。**

---

## 三、全生命周期状态规则速查

| 状态 | 执行人 | 关键规则 |
|------|--------|---------|
| **SUBMITTED** | Reporter | 所有必填字段完整；提交即进入审核队列 |
| **MODIFYING** | Reporter | 收到打回后 **24 小时内**完成修改 |
| **OPEN** | Assignee（devs） | 超过 30 天无状态更新  项目经理升级 |
| **RESOLVED** | Reporter/TL | A 类必解问题须 TL 审核后方可流转 VERIFIED |
| **VERIFIED** | Reporter/组员 | 按格式填写验证评论；A 类必解须 TL 二次审核后关闭 |
| **CLOSED** | Reporter/Owner | 终态，不可 Reopen；新 Bug 须新建单 + Link |
| **DUPLICATED** | Fixer（devs） | 只能置重到同库更早的单；不可跨库 |

---

## 四、Agent 巡检使用指南

### 4.1 提单合规性检查项（逐项核对）

**标题（Summary）**：
- [ ]  **ZT-1** 是否以 `【TestEnvironment】` 或 `【Test Environment】` 开头
- [ ]  **ZT-1** 是否包含全部 7 个标签
- [ ]  **ZT-1** 是否含国家信息（合法国家标签含 `【EE1】`，**不得误判**）
- [ ]  **ZT-1** 是否含版本信息
- [ ]  **ZT-2** Risk 字段值是否与 Summary `【Frequency】` 标签一致
- [ ]  **ZT-2** Risk 字段值是否与 Description 正文频率描述一致
- [ ]  **ZT-3** Component/s 是否在允许的五个值内
- [ ]  **ZT-5** Environment 字段是否包含 Device ID
- [ ]  **ZT-4** Description 是否包含 Steps / Actual / Expected / VideoLink / LogAddress

**附件与 Bug 等级（ZT-6）**：
- [ ]  **ZT-6** 使用多模态模型识别附件图片中的 Severity 字段，与 Priority 字段比对；不一致且无 Comment 备注  ZT-6 不合规
- [ ] 若所有图片均无 Severity 字段，**跳过 ZT-6，不判定不合规**

### 4.2 关单合规性检查项

- [ ] VERIFIED Comment 格式是否正确（APK Version / Test Steps / Test Count / Test Result）
- [ ] 是否在 Fix Version 指定版本上验证
- [ ] A 类问题是否经过 TL 二次审核
- [ ] Reopen 时 Comment 是否清晰说明原因

### 4.3 不合规问题的评论格式

**评论示例**：
```
[JIRA Quality Inspection]

The following items do not comply with the ticket submission standard (V1.0, April 2026):

1. [Title] Missing required tag【DetailedVersion】. All 8 tags are mandatory per 1.2.
2. [Risk] Risk field is blank. It must be filled and consistent with【Frequency】in the title per 1.4.
3. [Attachment] No attachment permission set. Please enable "Anyone can view/download" on the parent folder per 1.6.

Please revise within 24 hours (MODIFYING status) and reassign to the Owner after commit.
```

---

## 约束

- 质检标准**仅引用本技能中的规范（编号/ZT 编号）**，不得编造条文。
- 字段值**只能使用工具返回的内容**，不得假设或捏造。
- Phase 4 的图片识别结果**严禁跨单据使用**，每条单据质检完后立即清除。
- 六个阶段**必须按顺序完整执行**，不得省略。
- `save_jira_audit_to_database` 属于入库动作，**未经用户批准严禁调用**。
- 若 JIRA 凭证未配置，告知用户在 `.env` 中配置 `JIRA_URL` / `JIRA_USER` / `JIRA_PASS`。
- 若多模态模型未配置，告知用户在 `.env` 中配置 `IMAGE_PARSER_API_KEY`。
