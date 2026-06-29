import tempfile
from pathlib import Path

from videotodoc.document import ensure_mindmap_link


def test_ensure_mindmap_link_accepts_multiple_images():
    with tempfile.TemporaryDirectory() as tmp:
        md = Path(tmp) / "test.md"
        md.write_text("# Title\n\n## 图文讲义\n", encoding="utf-8")
        img1 = Path(tmp) / "mindmap_01.png"
        img2 = Path(tmp) / "mindmap_02.png"
        img1.write_text("", encoding="utf-8")
        img2.write_text("", encoding="utf-8")
        ensure_mindmap_link(md, [img1, img2])
        text = md.read_text(encoding="utf-8")
        assert "![思维导图](mindmap_01.png)" in text
        assert "![思维导图](mindmap_02.png)" in text


def test_ensure_mindmap_link_replaces_existing_single_image():
    with tempfile.TemporaryDirectory() as tmp:
        md = Path(tmp) / "test.md"
        md.write_text("# Title\n\n## 思维导图\n\n![思维导图](old.png)\n", encoding="utf-8")
        img = Path(tmp) / "new.png"
        img.write_text("", encoding="utf-8")
        ensure_mindmap_link(md, img)
        text = md.read_text(encoding="utf-8")
        assert "![思维导图](new.png)" in text
        assert "old.png" not in text


def test_ensure_mindmap_link_replaces_existing_multiple_images():
    with tempfile.TemporaryDirectory() as tmp:
        md = Path(tmp) / "test.md"
        md.write_text("# Title\n\n## 思维导图\n\n![思维导图](old_01.png)\n\n![思维导图](old_02.png)\n", encoding="utf-8")
        img1 = Path(tmp) / "new_01.png"
        img2 = Path(tmp) / "new_02.png"
        img1.write_text("", encoding="utf-8")
        img2.write_text("", encoding="utf-8")
        ensure_mindmap_link(md, [img1, img2])
        text = md.read_text(encoding="utf-8")
        assert "![思维导图](new_01.png)" in text
        assert "![思维导图](new_02.png)" in text
        assert "old_01.png" not in text
        assert "old_02.png" not in text
