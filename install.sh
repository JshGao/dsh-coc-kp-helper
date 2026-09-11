#!/usr/bin/env bash
# 生成把本仓库的 preset 注册进 DSH 的补丁片段。
#
# 为什么需要这一步：agent preset 的「根目录」必须由 DSH 的配置声明，而 bundle 的
# patch 层里既不能用 include、也不能用 import.meta（见 cordis.patch.yml 的说明）。
# 用户自己的补丁层（$DSH_HOME/profiles/<profile>/cordis.patch.yml 或
# $DSH_HOME/cordis.patch.yml）是 **DSH 热重载**的，写进去立即生效、不需要重启。
#
# 用法：
#   ./install.sh                 # 打印补丁片段
#   ./install.sh --write         # 直接写进 $DSH_HOME/cordis.patch.yml（会先备份）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRESETS="$ROOT/presets"
DSH_HOME_DIR="${DSH_HOME:-$HOME/.dsh}"

[ -f "$PRESETS/coc-kp/agent.cordis.yml" ] || { echo "找不到 $PRESETS/coc-kp/agent.cordis.yml" >&2; exit 1; }

snippet() {
  cat <<YAML
# 由 dsh-coc-kp-helper/install.sh 生成：注册 COC 守秘人备团 preset 的根目录
- id: agent-presets
  config:
    default: standard
    roots:
      - path: $PRESETS
    includeShippedRoot: true
    includeUserRoot: true
YAML
}

if [ "${1:-}" = "--write" ]; then
  target="$DSH_HOME_DIR/cordis.patch.yml"
  mkdir -p "$DSH_HOME_DIR"
  if [ -f "$target" ]; then
    cp "$target" "$target.bak.$(date +%s)"
    echo "已备份到 $target.bak.*" >&2
  fi
  if grep -q 'id: agent-presets' "$target" 2>/dev/null; then
    echo "注意：$target 里已有 agent-presets 行，请手动合并（不要重复声明）。" >&2
    echo "以下是应当写入的内容：" >&2
    snippet
    exit 0
  fi
  snippet >> "$target"
  echo "已写入 $target —— DSH 补丁层是热重载的，保存后立即生效，不需要重启。" >&2
else
  echo "# 把下面这段加进 $DSH_HOME_DIR/cordis.patch.yml（该文件热重载，加完即生效）："
  echo "#"
  snippet
fi
