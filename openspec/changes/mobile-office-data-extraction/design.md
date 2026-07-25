## Architecture Overview

本方案将采集过程定义为**语义映射过程**。通过精准的物理窗口捕获，结合 Vision LLM 对业务 UI 组件（如指标卡片、数据表格）的识别，将像素信息转化为结构化的业务指标。

### Data Collection Workflow
Window Selection $\rightarrow$ Multi-page Capture $\rightarrow$ Component Segmentation $\rightarrow$ Vision LLM Extraction $\rightarrow$ Structured Aggregation $\rightarrow$ Export

## Detailed Design

### 1. 窗口捕获层 (Window Capture Layer)
- **定位机制**：利用 `pywin32` 或 `pygetwindow` 通过标题 “移动办公” 获取窗口句柄。
- **采集策略**：
    - **静态页提取**：对当前可见区域进行高分辨率截图。
    - **动态交互 (标签页)**：模拟点击标签页（如“计费收入”、“移动市场”）并依次触发截图。
    - **无滚动条采集方案**: 由于程序界面不提供物理滚动条，无法通过坐标判断位置，必须采用【覆盖截取 $\rightarrow$ 语义拼接】策略：
        - **纵向 (Y轴)**: 通过模拟鼠标滚轮事件 (Mouse Wheel) 向下滚动。每步滚动距离需保证截图之间存在 $\sim 30\% \text{-} 50\%$ 的内容重叠，以便后续通过 VLM 提取的行语义指纹进行对齐拼接。
        - **横向 (X轴)**: 通过模拟【鼠标左键按下 $\rightarrow$ 水平拖拽 $\rightarrow$ 释放】的操作实现左右滑动。同样需保证每张截图之间有足够的重叠区域用于列语义对齐。
        - **终止判定**: 当连续两张截图的视觉内容（或 VLM 提取出的关键指标）完全一致时，判定为触达边界。

### 2. 视觉解析层 (Vision Parsing Layer)
- **组件识别**：引导 Vision LLM 识别界面中的三种核心组件。由于传统 OCR 在面对截图水印时会出现严重的误识或截断，本方案通过 VLM 的语义理解能力，在 Prompt 中明确要求其排除所有背景水印干扰，直接提取底层业务数据。
- **识别目标**:
    - **KPI Card**: 提取指标名称、当前值、环比/同比变化率（如截图中显示的 $\text{-1.08}\%$）。
    - **Data Table**: 提取表头及行数据，保持列的对应关系。
    - **Navigation State**: 识别当前处于哪个标签页，用于给数据打标。
- **Prompt 策略**：采用“结构化定义 $\rightarrow$ 视觉定位 $\rightarrow$ 精确提取”的 Prompt 模式，要求模型以 JSON 格式输出。

### 3. 数据聚合层 (Aggregation Layer)
- **语义对齐**：将不同标签页采集到的指标统一到同一个业务实体下。
- **冲突处理**：若同一指标在多次截图中出现且值不一致，采用时间戳最新的数据或由 VLM 二次确认。

### 4. 导出层 (Export Layer)
- **格式化输出**：将 JSON 数据转换为 Excel 表格，其中一个 Sheet 保存全局 KPI，其他 Sheet 按标签页保存详细明细表。

## Critical Considerations
- **窗口遮挡**：确保采集前窗口处于前台且未被其他程序遮挡 $\rightarrow$ 实现自动 `SetForegroundWindow` 逻辑。
- **分辨率适配**：不同显示器缩放比例影响识别率 $\rightarrow$ 强制指定截图的分辨率或在 Prompt 中告知缩放比例。
- **UI 变动**：针对 UI 版本更新导致的组件位置变化 $\rightarrow$ 使用语义定位而非绝对坐标定位。
