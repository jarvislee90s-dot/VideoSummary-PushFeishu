#!/bin/bash
# 安装 video-to-notes skill 到 ~/.codex/skills/

set -e

SKILL_NAME="video-to-notes"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$HOME/.codex/skills/$SKILL_NAME"

echo "📦 安装 $SKILL_NAME skill..."
echo "  源目录: $SOURCE_DIR"
echo "  目标目录: $TARGET_DIR"

# 创建目标目录
mkdir -p "$TARGET_DIR/scripts"

# 复制文件
cp "$SOURCE_DIR/SKILL.md" "$TARGET_DIR/"
cp "$SOURCE_DIR/scripts/process.py" "$TARGET_DIR/scripts/"

# 设置权限
chmod +x "$TARGET_DIR/scripts/process.py"

echo "✅ 安装完成！"
echo ""
echo "使用方式："
echo "  在 Codex 中发送视频链接，Agent 将自动使用此 skill"
echo ""
echo "测试命令："
echo "  python3 ~/.codex/skills/video-to-notes/scripts/process.py doctor"
