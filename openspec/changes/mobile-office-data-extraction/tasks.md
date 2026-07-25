## Implementation Tasks

### Phase 1: Windows Capture Engine
- [ ] **Task 1.1**: 开发 `src/window_capture/engine.py`，实现通过标题 “移动办公” 定位并截取窗口图像。
- [ ] **Task 1.2**: 实现自动切换标签页的交互逻辑，确保能遍历所有业务维度。
- [ ] **Task 1.3**: 实现纵向采集机制：模拟鼠标滚轮滚动 $\rightarrow$ 覆盖截图 $\rightarrow$ 边界检测（无滚动条模式）。
- [ ] **Task 1.4**: 实现横向采集机制：模拟左键拖拽滑动 $\rightarrow$ 覆盖截图 $\rightarrow$ 边界检测（无滚动条模式）。

### Phase 2: Vision Dashboard Extractor
- [ ] **Task 2.1**: 设计并优化针对 “掌上经分” UI 的 Vision Prompt，确保能精确提取 KPI 卡片和数据表格。
- [ ] **Task 2.2**: 实现 `src/document_parsing_pipeline/dashboard_extractor.py`，将截图转换为结构化 JSON。
- [ ] **Task 2.3**: 构建针对指标环比/同比等特殊格式的后处理解析逻辑。

### Phase 3: Data Aggregation & Export
- [ ] **Task 3.1**: 开发数据聚合模块，将多页采集结果整合为统一的业务数据集。
- [ ] **Task 3.2**: 实现 `src/output_visualization/office_exporter.py`，支持导出高保真 Excel 报表。

### Phase 4: End-to-End Integration & Validation
- [ ] **Task 4.1**: 修改/创建 `scripts/win_capture.py`，串联【捕获 $\rightarrow$ 提取 $\rightarrow$ 导出】全流程。
- [ ] **Task 4.2**: 使用实际 “移动办公” 程序进行端到端采集测试，验证数据的完整性和准确性。
- [ ] **Task 4.3**: 针对不同分辨率和缩放比例进行鲁棒性测试。
