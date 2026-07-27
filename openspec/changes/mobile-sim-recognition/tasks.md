## Implementation Tasks

### Phase 1: Vision Structural Extractor
- [x] **Task 1.1**: 开发 `src/document_parsing_pipeline/llm_vision_engine.py`，实现能提取【表头 + 行数据 + 指纹】的结构化识别。
- [x] **Task 1.2**: 设计并测试针对仿真手机报表的 Vision Prompt（重点：忽略水印、保持列顺序）。
- [x] **Task 1.3**: 实现图片 $\rightarrow$ Base64 的高效传输链路，支持大批量图片的并发请求。

### Phase 2: Semantic Splicing Engine (The Core)
- [x] **Task 2.1**: 创建 `src/document_parsing_pipeline/splicing_engine.py`。
- [x] **Task 2.2**: 实现纵向拼接逻辑：通过行指纹匹配建立全局 Y 轴索引 ($\text{Row}_{\text{global}}$)。
- [x] **Task 2.3**: 实现横向拼接逻辑：基于表头交集和 $\text{Row}_{\text{global}}$ 构建全局 X 轴坐标。
- [x] **Task 2.4**: 开发虚拟大矩阵填充机制，实现重叠区域的数据去重与冲突解决 (Voting)。

### Phase 3: Professional Report Export
- [x] **Task 3.1**: 创建 `src/output_visualization/excel_reporter.py`。
- [x] **Task 3.2**: 实现基于虚拟矩阵的 Excel 高保真导出（含冻结窗格、列宽优化）。
- [ ] **Task 3.3**: 构建【数据 $\rightarrow$ 原图】的反向索引映射，确保识别结果可追溯。

### Phase 4: Integration & End-to-End Validation
- [ ] **Task 4.1**: 修改 `scripts/batch_parse.py`，将流程更新为：$\text{Vision Extract} \rightarrow \text{Splicing} \rightarrow \text{Excel Export}$。
- [ ] **Task 4.2**: 使用 "D:\00_项目\招待费智能体\掌经" 的实际图片集进行完整重建测试。
- [ ] **Task 4.3**: 验证超大报表在 Excel 中的左右上下滚动体验及数据元整性。
