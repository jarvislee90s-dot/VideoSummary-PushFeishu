from videotodoc.mindmap_layout import LayoutConfig, compute_layout
from videotodoc.mindmap import _parse_mermaid_tree
from videotodoc.mindmap_verify import verify_layout

def _make_big_mmd(chapters: int, leaves_per_chapter: int) -> str:
    lines = ["mindmap", "  root((R))"]
    for i in range(chapters):
        lines.append(f"    Ch{i}")
        for j in range(leaves_per_chapter):
            lines.append(f"      leaf{i}_{j}")
    return "\n".join(lines) + "\n"


def test_verify_flags_excessive_height():
    mmd = _make_big_mmd(30, 3)
    root = _parse_mermaid_tree(mmd)
    cfg = LayoutConfig(max_col_height=200, chapter_h=30, leaf_h=20, leaf_gap=8, chapter_gap=20)
    layout = compute_layout(root, cfg)
    issues = verify_layout(layout, cfg)
    assert any("高度" in issue for issue in issues)


def test_verify_flags_too_many_nodes():
    mmd = _make_big_mmd(30, 3)
    root = _parse_mermaid_tree(mmd)
    cfg = LayoutConfig()
    layout = compute_layout(root, cfg)
    issues = verify_layout(layout, cfg)
    assert any("节点数" in issue for issue in issues)


def test_verify_passes_for_small_tree():
    small = """mindmap
  root((R))
    A
      a1
    B
      b1
"""
    root = _parse_mermaid_tree(small)
    cfg = LayoutConfig()
    layout = compute_layout(root, cfg)
    issues = verify_layout(layout, cfg)
    assert issues == []
