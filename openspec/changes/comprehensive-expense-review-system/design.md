## Context

业务招待费审核系统需要覆盖从规则制度数字化、OCR 解析、字段提取、批次审核到报告输出的完整链路。原 5 个 change 分别建设了不同模块，现整合为统一设计。

## Goals / Non-Goals

**Goals:**
- 规则制度 docx → Markdown → skill 的完整数字化链路
- OCR 解析支持 PDF/图片/Office/XML，输出 Markdown + JSON + 图片
- 字段提取支持规则（正则）和 LLM 两种模式，通过环境变量切换
- 批次级统一审核，7 类 checker 覆盖完整性/金额/招待/禁止/合规/交叉/校对
- 批次审核报告（txt + md），含字段对比表与分类问题
- Webhook 告警推送高风险发现

**Non-Goals:**
- 不修改 MinerU 引擎核心逻辑
- 不删除规则提取器（保留作为 fallback）
- 不影响现有 Webhook 通知机制

## Decisions

### 1. 规则制度数字化

**链路：** `00规则制度/*.docx` → MinerU 解析 → `00规则制度_md/*.md` → 人工整理 → `skill/<子文件夹名>/SKILL.md`

**批次关联：** 批次文件夹名格式 `<skill名称>_<批次类型>_<摘要>_<日期>_<时间戳>`，前缀自动匹配对应 skill。

### 2. OCR 解析引擎

**MinerU LocalAPIServer：** 统一处理 PDF/图片/Office/XML，输出 Markdown。
- XML（全电发票）走 `xml_to_md` 直接转换
- `return_images=True` 收集解析图片到 `images/` 子目录
- `OutputOrganizer` 扁平化目录，JSON 到 `_json/`，图片到 `images/`

### 3. 字段提取双引擎

| 引擎 | 实现 | 适用场景 |
|------|------|----------|
| `FieldExtractor` | 正则 + 表格解析 | 标准格式文档，速度快 |
| `LlmFieldExtractor` | Anthropic API + 本地模型 | 复杂表格/纯文本/非结构化文档 |

**切换：** `USE_LLM_EXTRACTOR=1` 环境变量。

**LLM 提示词：** 基于 `skill/` 目录规则动态构建，非硬编码。

### 4. 批次审核上下文

```python
@dataclass
class BatchReviewContext:
    documents: list[tuple[str, ExtractedFields]]
    total_amount: float       # 取发票→报账单→审批单（优先级）
    total_guest_count: int    # 取第一个非空值
    total_companion_count: int
    department: str
    reception_type: str
    apply_date: datetime
    reception_date: datetime
```

**聚合规则：** 金额/人数不跨文档累加（同一笔报销），取第一个可靠来源。

### 5. 7 类 Checker

| Checker | 规则数 | 说明 |
|---------|--------|------|
| `DocumentIntegrityChecker` | 7 | 报账单号、费用明细、支付凭证/流水、往来公函、发票查验、分摊表签章 |
| `AmountStandardChecker` | 5 | 外部/内部/工作餐金额标准、酒水价格、纪念品 |
| `ReceptionTypeChecker` | 3 | 招待类型判定、陪同人数标准、人均费用 |
| `ProhibitionChecker` | 6 | 禁止性规定（高档场所、敏感日期、超标准等） |
| `ReimbursementComplianceChecker` | 6 | 报销合规（审批流程、附件齐全、差旅地等） |
| `CrossAuditChecker` | 4 | 跨文档稽核（拆分报销、重复招待、日期冲突等） |
| `ProofreadingChecker` | 6 | 跨文档校对（金额/日期/支付/单位/函件一致性） |

### 6. 报告输出

**格式：** `审核报告.txt`（文本）+ `审核报告.md`（Markdown，含字段对比表）

**结构：**
```
全面业务招待费审核报告 — 批次: <批次名>

【批次信息】
  文档数: N
  部门: xxx
  招待类型: xxx

【总体判定】存在高风险 / 无高风险

--- [类别] ---
  [高/中/低/提示] 问题描述
  依据: xxx
```

### 7. Webhook 告警

仅高风险时 POST 到 `http://localhost:9999/hook`，推送高风险发现列表。

## 系统架构

```
输入 (data/input/<批次>/)
  ↓
FileCollector (ZIP 解压、排序、格式支持)
  ↓
MinerUEngine / xml_to_md (OCR 识别 → Markdown)
  ↓
OutputOrganizer (目录扁平化、JSON/图片分离)
  ↓
┌─ FieldExtractor (正则) ─┐
└─ LlmFieldExtractor (LLM) ─→ ExtractedFields
  ↓
ComprehensiveChecker (7 类 checker)
  ↓
ComprehensiveReporter (审核报告.txt + .md)
  ↓
WebhookNotifier (仅高风险)
```

## Risks / Trade-offs

- [LLM 推理速度慢于正则] → 单次提取约 2-5 秒，批处理场景可接受
- [OCR 识别的日期格式可能不一致] → 用 `dateutil.parser.parse` 容错解析
- [聚合指标可能因 OCR 误差偏大] → 金额/人数聚合时跳过 None 值，取第一个可靠来源
- [LLM 可能产生幻觉] → 提示词明确要求不编造，找不到的字段返回 null