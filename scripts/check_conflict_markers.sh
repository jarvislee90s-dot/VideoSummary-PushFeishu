#!/usr/bin/env bash
# 防止 git 合并冲突标记残留进入仓库
set -euo pipefail
if rg -n "^(<<<<<<< |=======|>>>>>>> )" .agents/skills/ 2>/dev/null; then
  echo "❌ 发现 git 合并冲突标记残留" >&2
  exit 1
fi
echo "✅ 无冲突标记残留"
