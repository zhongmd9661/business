## Why

在处理仿真手机截取的报表图片时，传统的 OCR 识别（如 MinerU）存在三个核心痛点：
1. **水印干扰**：截图中的水印会严重破坏文字连续性。
2. **空间碎片化**：一个完整的报表被切割为大量纵向滚动和横向滚动的碎图，简单的单图识别无法还原数据的全局结构。
3. **缺乏对照性**：识别结果与原图脱节，难以验证准确率。

为了获得“元整”的数据，必须将识别流程升级为“重建流程”。通过 Vision LLM 的语义理解能力，在不依赖像素拼接的前提下，利用数据本身的语义重复区进行逻辑拼合，还原出一张完整的、可滚动的超大报表。

## What Changes

- **引入视觉重建管线 (Reconstruction Pipeline)**：
    - **提取层**：使用 Vision LLM 识别每张碎片图的【表头】、【行数据】及【语义指纹】。
    - **拼接层 (Semantic Stitching)**：实现纵向 (Y轴) 和横向 (X轴) 的语义对齐算法，将碎图还原为全局坐标系。
    - **聚合层 (Virtual Matrix)**：构建一个动态的虚拟大矩阵，处理重叠区域的数据冲突（通过多票机制确保元整性）。
- **实现专业报表导出系统**：
    - 开发 `ExcelReporter`，将重建后的虚拟大表导出为具备“报表软件”特性的 Excel 文件。
    - 实现冻结窗格 (Freeze Panes) 以支持海量数据的上下左右滚动浏览。
    - 建立【数据 $\rightarrow$ 原图】的反向索引映射。

## Capabilities

### New Capabilities

- `semantic-stitching`: 基于行/列语义指纹的自动化拼接，无需像素对齐即可还原超大表。
- `vision-reconstruction`: 直接从仿真截图集重建结构化报表，具备极强的水印过滤能力。
- `report-fidelity-export`: 导出高保真 Excel 报表，支持原图对照与流畅滚动。

### Modified Capabilities

- `batch_parse.py`: 集成上述重建管线，支持从图片集直接生成完整 Excel 报表。

## Impact

- **新增**: `src/document_parsing_pipeline/llm_vision_engine.py` (Vision LLM 结构化提取)
- **新增**: `src/document_parsing_pipeline/splicing_engine.py` (语义拼接核心算法)
- **新增**: `src/output_visualization/excel_reporter.py` (专业报表导出)
- **修改**: `scripts/batch_parse.py` (升级为重建管线流程)
