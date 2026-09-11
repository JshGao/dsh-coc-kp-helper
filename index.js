/**
 * @jshgao/dsh-coc-kp-helper — 这个 bundle 只贡献一个 preset 根目录，不贡献任何运行时插件。
 *
 * 它做的事全在 `agent-presets.patch.yml` 里：往 `agent-presets` 行里加一个 preset 根
 * `presets/`，于是 `presets/coc-kp/` 成为名册里可选的「COC 守秘人备团模式」。
 *
 * 因此本包**不注册任何服务、工具或提示段**，`apply` 是空的。保留入口文件是因为
 * 它作为 profile bundle 被加载，包本身要能被解析。
 *
 * @module @jshgao/dsh-coc-kp-helper
 */

/** Cordis 插件名。 */
export const name = 'coc-kp-helper'

/**
 * 空实现：真正的贡献是包内 `agent-presets.patch.yml` 这一层 patch。
 * @returns {void}
 */
export function apply() {}
