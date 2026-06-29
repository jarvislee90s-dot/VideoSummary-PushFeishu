from pathlib import Path

from videotodoc.mindmap import render_mindmap_and_refresh_docs


def _make_big_mmd(chapters: int, leaves_per_chapter: int) -> str:
    lines = ["mindmap", "  root((R))"]
    for i in range(chapters):
        lines.append(f"    Ch{i}")
        for j in range(leaves_per_chapter):
            lines.append(f"      leaf{i}_{j}")
    return "\n".join(lines) + "\n"


def test_render_splits_when_too_many_nodes(tmp_path: Path):
    mmd = tmp_path / "mindmap.mmd"
    mmd.write_text(_make_big_mmd(30, 3), encoding="utf-8")
    image_paths, _ = render_mindmap_and_refresh_docs(tmp_path)
    assert len(image_paths) >= 2
    for path in image_paths:
        assert path.exists()


def test_render_single_image_for_small_tree(tmp_path: Path):
    mmd = tmp_path / "mindmap.mmd"
    mmd.write_text("""mindmap
  root((R))
    A
      a1
    B
      b1
""", encoding="utf-8")
    image_paths, _ = render_mindmap_and_refresh_docs(tmp_path)
    assert len(image_paths) == 1
    assert image_paths[0].exists()
