# JIRA 规范巡检示例（正常 / 异常对照）

> 本文件提供 JIRA 提单/关单规范中各检查项的 **Good Case（合规）** 与 **Bad Case（不合规）** 对照示例，供 Agent 在巡检时参考判定标准。
>
> 适用范围：海外 AI 测试团队（EE1、尼日利亚、肯尼亚、印度、印度尼西亚），项目库 SRDAIV。

---

## 示例 1：Summary 标题格式（ZT-1）

### Good Case — 合规标题

```
【TestEnvironment】【Ella】【v4.7.1】【Ella4.7.1.009】【Indonesia】【RealTimeCall】【Must】Ella didn't give a response on RealTimeCall
```

**判定要点**：
- 以 `【TestEnvironment】` 开头 ✓
- 包含全部 7 个标签：Environment、Project、Version（Main/Detailed）、Country、FunctionName、Frequency ✓
- 国家标签 `【Indonesia】` 在合法列表内 ✓
- 版本信息通过 `【v4.7.1】` 等价满足 ✓

### Bad Case — 不合规标题

| 序号 | 不合规标题 | 违规原因 |
|------|-----------|---------|
| 1 | `【TestEnv】【Ella】【v4.7.1】【Ella4.7.1.009】【Indonesia】【RealTimeCall】【Must】Ella didn't give a response` | 环境标签缩写：`【TestEnv】` 应为 `【TestEnvironment】` 或 `【Test Environment】` |
| 2 | `【TestEnvironment】【Ella】【Indonesia】【RealTimeCall】【Must】Ella didn't give a response` | 缺失版本信息标签（无 MainVersion / DetailedVersion / Vx.x.x） |
| 3 | `【TestEnvironment】【Ella】【v4.7.1】【Ella4.7.1.009】【RealTimeCall】【Must】Ella didn't give a response` | 缺失国家标签 |
| 4 | `【TestEnvironment】【Ella】【v4.7.1】【Ella4.7.1.009】【Indonesia】【RealTimeCall】Ella didn't give a response` | 缺失频率标签 `【Frequency】` |
| 5 | `Ella didn't give a response on RealTimeCall` | 无任何标签，全部 7 个标签缺失 |
| 6 | `【TestEnvironment】【Ella】【v4.7.1】【Ella4.7.1.009】【Russia】【RealTimeCall】【Must】...` | 国家标签 `【Russia】` 不在合法列表内；合法应为 `【EE1】` |

> **特别注意**：`【EE1】` 代表俄罗斯，是合法国家标签，**不得误判为缺少国家信息**。

---

## 示例 2：Risk 频率三处一致（ZT-2）

### Good Case — 三处完全一致

| 位置 | 内容 | 判定 |
|------|------|------|
| Summary `【Frequency】` 标签 | `【Must】` | ✓ |
| Risk 字段值 | `must` | ✓ |
| Description 正文频率描述 | `Test Count: 5/5` | ✓ |

**结论**：三处均表示"必现"，ZT-2 合规。

### Bad Case — 三处不一致

| 位置 | 内容 | 判定 |
|------|------|------|
| Summary `【Frequency】` 标签 | `【Must】` | — |
| Risk 字段值 | `Often` | ✗ 与标题不一致 |
| Description 正文频率描述 | `Test Count: 10/10` | —（数值匹配 Must，但 Risk 字段不符） |

**结论**：Risk 字段 `Often` 与 Summary `【Must】` 不一致，ZT-2 不合规。

### Bad Case 2 — Risk 字段为空

| 位置 | 内容 | 判定 |
|------|------|------|
| Summary `【Frequency】` 标签 | `【Occasional】` | — |
| Risk 字段值 | *(空白/未填写)* | ✗ 缺失 |
| Description 正文频率描述 | `Occasional` | — |

**结论**：Risk 字段为空，无法与标题和描述比对，ZT-2 不合规。

---

## 示例 3：Description 描述完整性（ZT-4）

### Good Case — 完整描述

```
A) Preconditions
   - Device: TECNO LH8n, Android 14
   - Network: Wi-Fi connected
   - Ella version: v4.7.1.009

B) Steps to Reproduce
   1. Launch Ella app
   2. Tap RealTimeCall button
   3. Speak "Call Mom"

C) Actual Result
   - Ella shows "I don't understand" and no call is initiated

D) Expected Result
   - Ella should initiate a WhatsApp call to the contact named "Mom"

E) VideoLink
   - https://xxx.feishu.cn/file/video_001

F) LogAddress
   - https://xxx.feishu.cn/file/log_001
```

**判定要点**：A/B/C/D/E/F 六部分齐全，英文书写 ✓ → ZT-4 合规。

### Bad Case — 描述严重缺失

```
The function is broken, please fix.
```

**判定要点**：仅一句话，缺少 B) Steps to Reproduce、C) Actual Result、D) Expected Result、E) VideoLink、F) LogAddress → **ZT-4 不合规**。

### Bad Case 2 — 部分缺失

```
A) Preconditions
   - Device: TECNO LH8n

B) Steps to Reproduce
   1. Open Ella
   2. Use RealTimeCall

D) Expected Result
   - It should work

E) VideoLink
   - https://xxx.feishu.cn/file/video_002
```

**判定要点**：
- 缺少 C) Actual Result → ZT-4 不合规
- 缺少 F) LogAddress → ZT-4 不合规
- D) Expected Result 使用模糊表达 "It should work"，建议具体化，但不单独触发 ZT-4

---

## 示例 4：Component/s 字段（ZT-3）

### Good Case

| Component/s 值 | 判定 |
|----------------|------|
| `AI-VA专项-ASR` | ✓ 合规 |
| `AI-VA专项-TTS` | ✓ 合规 |
| `AI-VA专项-通用` | ✓ 合规 |
| `AI-VA专项-nlu` | ✓ 合规 |
| `AI-VA专项-UX` | ✓ 合规 |

### Bad Case

| Component/s 值 | 判定 | 原因 |
|----------------|------|------|
| *(空白/未填写)* | ✗ 不合规 | 字段为空 |
| `AI-VA` | ✗ 不合规 | 不在允许的五个选项内 |
| `ASR-TTS` | ✗ 不合规 | 不在允许的五个选项内 |
| `AI-VA专项-NLU` | ✗ 不合规 | 大小写不匹配，允许的是 `AI-VA专项-nlu`（小写 nlu） |

> **注意**：Component/s 填写了多个值但均在允许列表内（如 `AI-VA专项-通用` + `AI-VA专项-UX`）→ **合规**。

---

## 示例 5：Bug 等级截图 Severity vs Priority（ZT-6）

### Good Case — 完全一致

| 项目 | 值 |
|------|-----|
| JIRA Priority 字段 | `Critical` |
| 附件截图中 Severity 字段 | `Critical` |
| Comments 中是否有备注 | 无需备注 |

**结论**：Severity = Priority = `Critical`，ZT-6 合规 ✓

### Good Case 2 — 不一致但有备注

| 项目 | 值 |
|------|-----|
| JIRA Priority 字段 | `Critical` |
| 附件截图中 Severity 字段 | `Major` |
| Comments 中备注 | `Severity is Major in calculation table, but set to Critical due to user impact. Approved by TL.` |

**结论**：Severity ≠ Priority，但 Comment 中有合理解释说明 → **ZT-6 合规** ✓（记录备注内容）。

### Bad Case — 不一致且无备注

| 项目 | 值 |
|------|-----|
| JIRA Priority 字段 | `Blocker` |
| 附件截图中 Severity 字段 | `Major` |
| Comments 中是否有备注 | 无 |

**结论**：Severity (`Major`) ≠ Priority (`Blocker`)，且 Comment 中无说明 → **ZT-6 不合规** ✗

### Bad Case 2 — 无 Bug 等级截图

| 项目 | 值 |
|------|-----|
| JIRA Priority 字段 | `Critical` |
| 附件截图 | 仅有 UI 截图、视频链接，无 Bug 等级计算表 |

**结论**：所有图片均无法识别出 Severity 字段 → **跳过 ZT-6 检查，不判定不合规**。

---

## 示例 6：关单验证评论格式

### Good Case — 合规的 VERIFIED 评论

```
APK Version: Ella v4.7.2.015
Test Steps:
  1. Launch Ella app
  2. Tap RealTimeCall button
  3. Speak "Call Mom"
Test Count: 5/5
Test Result: PASSED
```

**判定要点**：包含 APK Version、Test Steps、Test Count、Test Result 四要素，Test Result 为 PASSED → 可 Close。

### Bad Case — 验证评论格式错误

```
Fixed. Verified OK.
```

**判定要点**：缺少 APK Version、Test Steps、Test Count → 不符合关单验证评论格式要求。

### Bad Case 2 — NOT PASSED 未附证据

```
APK Version: Ella v4.7.2.015
Test Steps:
  1. Launch Ella app
  2. Tap RealTimeCall
Test Count: 2/5
Test Result: NOT PASSED
```

**判定要点**：Test Result 为 NOT PASSED，但评论中未说明失败现象、未附最新 Log/视频 → 应要求补充后再 Reopen。

---

## 示例 7：Environment 字段设备标识（ZT-5）

### Good Case

```
Device ID: 0123456789ABCDEF
Test Environment: Production
Network: 4G
```

**判定要点**：包含 Device ID（`adb devices` 获取）→ ZT-5 合规 ✓

### Bad Case

```
Test Environment: Wi-Fi
Device: TECNO LH8n
```

**判定要点**：虽提到设备型号，但缺少具体的 Device ID（如 `0123456789ABCDEF`）→ **ZT-5 不合规** ✗

---

## 示例 8：不合规评论发表示例

当单据被判定为不合规时，Agent 必须调用 `post_jira_issue_comment` 发表评论，参考格式如下：

```
[JIRA Quality Inspection]

The following items do not comply with the ticket submission standard (V1.0, April 2026):

1. [Title] Missing required tag【DetailedVersion】. All 8 tags are mandatory per §1.2.
2. [Risk] Risk field is blank. It must be filled and consistent with【Frequency】in the title per §1.4.
3. [Attachment] No attachment permission set. Please enable "Anyone can view/download" on the parent folder per §1.6.

Please revise within 24 hours (MODIFYING status) and reassign to the Owner after commit.
```

**要点**：
- 使用英文（场测海外问题）
- 分条列出不符合项及对应规范条文（§编号 / ZT 编号）
- 给出具体整改方案
- 明确整改期限（通常 24 小时）
- 指明下一步行动（reassign to the Owner after commit）
