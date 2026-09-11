/**
 * @jshgao/dsh-coc-kp-helper — 把本包内的 agent preset 安装到用户预设根。
 *
 * 为什么不是在 `cordis.patch.yml` 里直接注册 preset 根：实测结论（三条，都踩过）——
 *
 *  1. patch 里不能用 `- include: ./x.yml`：patch 的每一项要么是 insert、要么必须带 id，
 *     不带 id 的非 insert 项会被拒绝（`patch: id is required for non-insert patches`）。
 *  2. patch 表达式里不能用 `import.meta`（`Cannot use 'import.meta' outside a module`）。
 *  3. patch 表达式里的 `baseUrl` 实测是 **profile 目录**，不是包目录；而包名解析走的是
 *     安装位置（harness base），所以**没有任何表达式能定位到包自己的目录**。
 *
 * 因此本插件在加载时做一件简单的事：把包内 `presets/coc-kp/` 复制到
 * `$DSH_HOME/.agent-presets/coc-kp/` —— 那是 DSH 名册本来就扫描的标准用户预设根。
 * 复制是幂等的（版本号相同且目录存在就跳过），并且复制到用户根之后 preset 可以被
 * 正常地本地改写（名册每次调用都会重读那个目录）。
 *
 * ⚠️ 前提：本文件**只有在本包声明了 `dsh.bundle.patch` 时才会被执行**。DSH 的插件树
 * 只由 `dsh.profile.bundles` 里每个包的 bundle 补丁层层叠而成；不声明 `dsh.bundle`
 * 的依赖包只是躺在 `node_modules` 里，DSH 永远不会 import 它，这里的 `apply()` 也就
 * 永远不跑 —— 而且**完全静默**。声明在 `package.json`，补丁层在 `cordis.patch.yml`。
 *
 * @module @jshgao/dsh-coc-kp-helper
 */

import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

/** Cordis 插件名。 */
export const name = 'coc-kp-helper'

/** 本包目录（`import.meta` 在真正的模块里可用，这正是 patch 表达式做不到的一点）。 */
const packageDir = dirname(fileURLToPath(import.meta.url))

/** preset 在包内的位置。 */
const sourceDir = join(packageDir, 'presets', 'coc-kp')

/** preset 在用户预设根里的目标位置。 */
const presetId = 'coc-kp'

/** 同步标记文件：记录已经同步过的包版本，避免每次启动都复制。 */
const markerName = '.synced-version'

/**
 * 解析 DSH home：优先 `$DSH_HOME`，否则 `~/.dsh`。
 * @returns {string} DSH home 的绝对路径。
 */
function dshHome() {
  const fromEnv = process.env.DSH_HOME
  if (fromEnv !== undefined && fromEnv !== '') return fromEnv
  const home = process.env.HOME ?? process.env.USERPROFILE
  if (home === undefined || home === '') throw new Error('coc-kp-helper: 既没有 $DSH_HOME 也没有 $HOME')
  return join(home, '.dsh')
}

/**
 * 递归复制 preset 目录（覆盖写）。只处理普通文件与目录：这里是包内自带内容，不需要跟随符号链接。
 * @param {string} from - 源目录。
 * @param {string} to - 目标目录。
 * @returns {number} 复制的文件数。
 */
function copyTree(from, to) {
  let copied = 0
  mkdirSync(to, { recursive: true })
  for (const entry of readdirSync(from, { withFileTypes: true })) {
    const source = join(from, entry.name)
    const target = join(to, entry.name)
    if (entry.isDirectory()) copied += copyTree(source, target)
    else if (entry.isFile()) {
      copyFileSync(source, target)
      copied += 1
    }
  }
  return copied
}

/**
 * 把包内 preset 同步到用户预设根。
 * @param {object} [logger] - 可选的 Cordis logger；缺省时用 console。
 * @returns {{ skipped: boolean, target: string, version: string, copied: number }} 同步结果。
 */
export function syncPreset(logger) {
  const version = JSON.parse(readFileSync(join(packageDir, 'package.json'), 'utf8')).version
  const target = join(dshHome(), '.agent-presets', presetId)
  const marker = join(target, markerName)

  if (existsSync(join(target, 'agent.cordis.yml')) && existsSync(marker)
      && readFileSync(marker, 'utf8').trim() === version) {
    return { skipped: true, target, version, copied: 0 }
  }

  const copied = copyTree(sourceDir, target)
  writeFileSync(marker, `${version}\n`)
  logger?.info?.(`[coc-kp-helper] 已同步 preset 到 ${target}（${copied} 个文件，版本 ${version}）`)
  return { skipped: false, target, version, copied }
}

/**
 * 插件入口：加载时同步一次。同步失败不阻断宿主启动——注册 preset 是附加能力，
 * 不该让整个 profile 起不来；失败会打到日志里。
 * @param {import('@deepseek-ai/cordis').Context} ctx - 宿主上下文。
 * @returns {void}
 */
export function apply(ctx) {
  try {
    const result = syncPreset(ctx.logger)
    if (!result.skipped) ctx.logger?.info?.('[coc-kp-helper] 重启后可在预设下拉里选择「COC 守秘人备团模式」')
  } catch (error) {
    ctx.logger?.warn?.(`[coc-kp-helper] preset 同步失败：${error instanceof Error ? error.message : String(error)}`)
  }
}
