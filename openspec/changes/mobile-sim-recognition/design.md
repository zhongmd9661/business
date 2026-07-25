## Architecture Overview

本方案不再将识别视为简单的文本提取，而是一个**空间重建过程**。通过构建一个全局的语义坐标系 $(\text{Row}_{\text{global}}, \text{Col}_{\text{global}})$，将分散在多张图片中的碎片数据点映射到该坐标系中，最终还原出完整报表。

### Reconstruction Workflow
Image Set $\rightarrow$ Vision LLM Extraction $\rightarrow$ Y-Axis Alignment $\rightarrow$ X-Axis Alignment $\rightarrow$ Virtual Matrix Filling $\rightarrow$ Professional Excel Export

## Detailed Design

### 1. 结构化提取层 (Vision Extraction)
每个图片碎片被转化为一个包含元数据的对象：
- **Headers**: 识别出的表头列表（用于定义 X 轴）。
- **Rows**: 每行数据及其“语义指纹”（例如：`序号 + 日期 + 项目名`，用于 Y 轴对齐）。
- **ImageID**: 指向原图的引用。

### 2. 语义拼接算法 (Semantic Stitching)

#### A. 纵向重建 (Y-Axis / Rows)
1. **指纹匹配**：对比 $\text{Img}_A$ 的底部 $N$ 行与 $\text{Img}_B$ 的顶部 $M$ 行。
2. **链条构建**：当两图在语义上存在连续重叠时，将 $\text{Img}_B$ 挂载在 $\text{Img}_A$ 之后。
3. **全局行索引生成**：剔除重复项，为所有数据分配唯一的全局行号 $r \in [0, \text{TotalRows})$。

#### B. 横向重建 (X-Axis / Columns)
1. **全局列空间定义**：$\text{Col}_{\text{global}} = \bigcup (\text{所有碎片的 Headers})$。
2. **相对偏移计算**：根据每张图包含的具体列名，将其映射到 $\text{Col}_{\text{global}}$ 的索引区间 $[start\_col, end\_col]$。
3. **行同步校验**：利用 Y 轴已生成的全局行号 $r$，确保左右拼接时数据处于同一物理行。

### 3. 虚拟大矩阵 (Virtual Matrix)
- **存储结构**：创建一个 $\text{TotalRows} \times \text{TotalCols}$ 的内存矩阵。
- **冲突处理 (Voting)**：当同一个坐标 $(r, c)$ 在多张图中出现时，采用“多数票”机制或 Vision LLM 二次裁决，确保数据的元整性（Integrity）。

### 4. 专业 Excel 导出 (Professional Export)
- **布局实现**：
    - **冻结窗格**：固定首行（表头）和首列（序号/索引），模拟报表软件的滚动体验。
    - **原图映射**：在单元格中存储指向原图及其坐标的元数据，支持回溯验证。
    - **格式优化**：设置自动换行、单元格边框及标准字体，确保数据的专业呈现。

## Critical Considerations
- **语义漂移**：防止因识别错误导致拼接链条断裂 $\rightarrow$ 引入模糊匹配和容错机制。
- **内存占用**：超大型报表可能导致矩阵过大 $\rightarrow$ 使用稀疏矩阵存储或分块写入 Excel。
- **水印过滤**：在 Vision Prompt 中明确要求模型忽略所有非业务数据的覆盖物（如水印）。
