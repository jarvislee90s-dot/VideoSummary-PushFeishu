from __future__ import annotations

from .mindmap_layout import LayoutConfig, LayoutNode, MindmapLayout


MAX_IMAGE_HEIGHT = 1600
MAX_IMAGE_WIDTH = 3000
MAX_NODES_PER_IMAGE = 80


def _count_nodes(layout_node: LayoutNode) -> int:
    return 1 + sum(_count_nodes(child) for child in layout_node["children"])


def _collect_truncated_nodes(layout_node: LayoutNode) -> list[str]:
    found: list[str] = []
    text = layout_node["text"]
    if text.endswith("…") or text.endswith("..."):
        found.append(text)
    for child in layout_node["children"]:
        found.extend(_collect_truncated_nodes(child))
    return found


def verify_layout(layout: MindmapLayout, cfg: LayoutConfig | None = None) -> list[str]:
    issues: list[str] = []
    if layout.image_height > MAX_IMAGE_HEIGHT:
        issues.append(f"单图高度 {layout.image_height:.0f}px 超过建议上限 {MAX_IMAGE_HEIGHT}px，建议拆图")
    if layout.image_width > MAX_IMAGE_WIDTH:
        issues.append(f"单图宽度 {layout.image_width:.0f}px 超过建议上限 {MAX_IMAGE_WIDTH}px，建议拆图")
    node_count = _count_nodes(layout.root_node)
    if node_count > MAX_NODES_PER_IMAGE:
        issues.append(f"节点数 {node_count} 超过建议上限 {MAX_NODES_PER_IMAGE}，建议拆图")
    truncated = _collect_truncated_nodes(layout.root_node)
    if truncated:
        issues.append(f"存在 {len(truncated)} 个节点文本被截断，建议放宽节点宽度或拆图")
    return issues
