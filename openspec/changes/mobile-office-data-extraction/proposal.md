## Why

需要从 Win11 的“移动办公”窗口程序中自动化采集结构化数据。该程序界面包含复杂的指标卡片和数据报表，手动记录效率低且易出错。为了实现高保真、自动化的数据采集，需要构建一套从【窗口捕获 $\rightarrow$ 视觉识别 $\rightarrow$ 结构化输出】的完整管线。

## What Changes

- **引入 Windows 窗口自动化采集模块 (Window Capture Module)**：
    - 实现通过窗口标题（“移动办公”）精准定位并截取目标窗口。
    - 支持处理窗口内的标签页切换和滚动区域，确保数据的全量覆盖。
- **构建基于 Vision LLM 的仪表盘解析管线**：
    - 针对“掌上经分”等特定 UI 布局（指标卡片 + 数据表格），设计专门的视觉提取 Prompt。
    - 利用 VLM 的语义理解能力，直接从截图中提取 key-value 指标和结构化表格数据，过滤 UI 装饰元素。
- **实现结构化数据导出系统**：
    - 将采集到的多维度指标映射到标准化的数据模型中。
    - 支持将结果导出为 Excel 或 JSON 格式，便于后续分析。

## Capabilities

### New Capabilities

- `win-window-capture`: 基于标题的精准窗口截图及自动化翻页/滚动采集。
- `dashboard-structured-extraction`: 针对业务仪表盘 UI 的高保真结构化数据提取。
- `office-data-exporter`: 将窗口采集结果转换为标准化报表的导出能力。

### Modified Capabilities

- `scripts/win_capture.py`: (若已存在) 升级为支持多页采集和 VLM 集成的完整管线。

## Impact

- **新增**: `src/window_capture/engine.py` (窗口定位与截图核心逻辑)
- **新增**: `src/document_parsing_pipeline/dashboard_extractor.py` (仪表盘专用视觉提取器)
- **修改**: `scripts/win_capture.py` (集成上述功能，提供端到端采集脚本)
