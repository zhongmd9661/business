"""语义拼接引擎 - 将识别出的图片碎片还原为全局坐标系大表"""
from __future__ import annotations

import pathlib
from typing import List, Dict, Any, Set, Optional
from .llm_vision_engine import VisionFragment

class SplicingEngine:
    """实现纵向和横向的语义对齐重建算法"""

    def reconstruct(self, fragments: List[VisionFragment]) -> List[List[Any]]:
        """将碎片集还原为二维数据矩阵 [Rows][Cols]"""
        if not fragments:
            return []

        # 1. 构建全局列空间 (X-Axis)
        all_headers = set()
        for f in fragments:
            all_headers.update(f.headers)

        # 简单处理：按第一个碎片或最全碎片的顺序排列列名
        global_cols = sorted(list(all_headers))
        col_map = {name: i for i, name in enumerate(global_cols)}

        # 2. 构建纵向链条 (Y-Axis / Row Alignment)
        # 我们需要根据 fingerprints 将碎片有序排列
        ordered_fragments = self._align_vertical(fragments)

        # 3. 填充虚拟大矩阵
        virtual_matrix: List[Dict[str, Any]] = []

        for frag in ordered_fragments:
            for row_data in frag.rows:
                # 检查该行是否已存在于 matrix 中 (利用指纹去重)
                fingerprint = self._calculate_row_fingerprint(row_data)
                existing_idx = self._find_row_index(virtual_matrix, fingerprint)

                if existing_idx is not None:
                    # 存在冲突/重复，执行多票机制更新（这里简化为保留最新值）
                    self._merge_row(virtual_matrix, existing_idx, row_data)
                else:
                    # 新行，添加到矩阵
                    virtual_matrix.append(row_data)

        # 4. 转换为最终的二维列表 [Row][ColValue]
        final_table = []
        for row in virtual_matrix:
            row_values = [row.get(col, "") for col in global_cols]
            final_table.append(row_values)

        return final_table

    def _calculate_row_fingerprint(self, row: Dict[str, Any]) -> str:
        """生成行的唯一语义标识 (例如：序号 + 日期)"""
        # 尝试提取关键识别字段作为指纹
        keys = ["序号", "日期", "项目", "id"]
        parts = [str(row.get(k, "")) for k in keys if k in row]
        return "|".join(parts)

    def _find_row_index(self, matrix: List[Dict], fingerprint: str) -> Optional[int]:
        for i, row in enumerate(matrix):
            if self._calculate_row_fingerprint(row) == fingerprint:
                return i
        return None

    def _merge_row(self, matrix: List[Dict], idx: int, new_data: Dict):
        """将新识别的数据合并到现有行中 (填充缺失列)"""
        for k, v in new_data.items():
            if not matrix[idx].get(k):
                matrix[idx][k] = v

    def _align_vertical(self, fragments: List[VisionFragment]) -> List[VisionFragment]:
        """通过指纹重叠度对碎片进行纵向排序"""
        # 这是一个简化的链式对齐逻辑
        if not fragments: return []

        unvisited = set(fragments)
        ordered = []

        # 假设第一张图是起点 (实际应根据 image_id 或时间戳排序)
        current = fragments[0]
        ordered.append(current)
        unvisited.remove(current)

        while unvisited:
            # 寻找与 current 底部重叠度最高的碎片作为下一个
            best_next = None
            max_overlap = 0

            curr_bottom = current.fingerprints[-3:] if len(current.fingerprints) >= 3 else current.fingerprints

            for candidate in unvisited:
                cand_top = candidate.fingerprints[:3] if len(candidate.fingerprints) >= 3 else candidate.fingerprints
                overlap = len(set(curr_bottom) & set(cand_top))
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_next = candidate

            if best_next and max_overlap >= 1: # 至少有一行重叠
                ordered.append(best_next)
                unvisited.remove(best_next)
                current = best_next
            else:
                # 无法继续拼接，尝试跳到下一个未访问的碎片
                break

        # 处理孤立碎片的简单合并
        if unvisited:
            ordered.extend(list(unvisited))

        return ordered
