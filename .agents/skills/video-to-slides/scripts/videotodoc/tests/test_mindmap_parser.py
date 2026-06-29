from videotodoc.mindmap import _parse_mermaid_tree

SAMPLE_MMD = """mindmap
  root((Git + GitHub))
    基础概念
      Git
        开源免费
      GitHub
    环境准备
      安装工具
"""

def test_parse_mermaid_tree_structure():
    root = _parse_mermaid_tree(SAMPLE_MMD)
    assert root is not None
    assert root.text == "Git + GitHub"
    assert root.level == 0
    assert [c.text for c in root.children] == ["基础概念", "环境准备"]
    assert [c.text for c in root.children[0].children] == ["Git", "GitHub"]
    assert [c.text for c in root.children[0].children[0].children] == ["开源免费"]
