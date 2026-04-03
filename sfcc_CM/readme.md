 SFCC CM Notes

需要制作一个游戏的自动化测试脚本，主流程包含 `bootstrap_flow`、`main_flow`、`new_season_flow`、`recovery_flow`。

当前方向：

1. 每次脚本启动时，重启游戏，避免当前游戏位于未知界面
2. 游戏启动后，立即走 `bootstrap_flow`
3. 在 `bootstrap_flow` 最后一步选择第 3 个存档后进行判定
   先判定是否是 `main_flow`，如果不是，继续判定是不是 `new_season_flow`
   如果命中了就快速在单 flow 中推进，如果一个都未命中，则进入异常流程
4. 异常流程执行 `recovery_flow`

---

## 页面归属清单（按当前代码已知内容预填）

说明：

- `当前归属`：当前代码里大致落到哪个 flow
- `建议归属`：按目前设计更推荐落到哪个 flow
- `状态`：
  - `已明确`：当前代码已经比较明确
  - `归属不干净`：当前能处理，但分散在多个地方
  - `未正式分类`：业务上存在，但没有被正式 step 化

---

### Bootstrap

页面名: `login_screen`
当前 detector: `find_login_screen_in_screenshot()`
当前归属: `bootstrap_flow`
建议归属: `bootstrap_flow`
进入后动作: 点击屏幕中心继续
状态: 已明确

页面名: `game_main`
当前 detector: `find_game_main_screen_in_screenshot()`
当前归属: `bootstrap_flow`
建议归属: `bootstrap_flow`
进入后动作: 点击 `game_main_mark` 进入创造模式
状态: 已明确

页面名: `save_selection`
当前 detector: `find_save_selection_screen_in_screenshot()`
当前归属: `bootstrap_flow`
建议归属: `bootstrap_flow`
进入后动作: 选择第 3 个存档
状态: 已明确

---

### Main

页面名: `creative_mode_main`
当前 detector: `find_main_screen_in_screenshot()`
当前归属: `main_flow`
建议归属: `main_flow`
进入后动作: 切 3 倍速、特训、推进日程
状态: 已明确

页面名: `special_training_settings`
当前 detector: `find_special_training_title_in_screenshot()` / `find_special_training_screen_in_screenshot()`
当前归属: `main_flow`
建议归属: `main_flow`
进入后动作: 全部重置 -> 推荐 -> 进行特训
状态: 已明确

页面名: `special_training_result`
当前 detector: `find_special_training_result_screen_in_screenshot()`
当前归属: `main_flow`
建议归属: `main_flow`
进入后动作: 立即返回主界面
状态: 已明确

页面名: `event_dialog`
当前 detector: 右上角 `log/log2`
当前归属: 顶层快线 + `main_flow`
建议归属: `main_flow`
进入后动作: 优先点 `close`，如果有event_choice，选择第1个选项，再点击skip，最后点击鼠标左键，直到离开当前界面

状态: 归属不干净

页面名: `match_reward`
当前 detector: `find_match_reward_screen_in_screenshot()`
当前归属: 顶层 + `main_flow`
建议归属: `main_flow`
进入后动作: 处理奖励页并回到主线
状态: 归属不干净

页面名: `match_sequence`
当前 detector: `MATCH_SEQUENCE_TITLE_TEXT` / `MATCH_SEQUENCE_RESULT_BUTTONS`
当前归属: `main_flow`
建议归属: `main_flow`
进入后动作: 点 result / continue / confirm，然后会来到match_reward
状态: 已明确

页面名: `season_end / league_result`
当前 detector: `联赛结果 / 梦幻球队 / 赛季结果`
当前归属: 顶层 + `main_flow`
建议归属: `main_flow`
进入后动作: 持续点右侧确认，直到 handoff 到主线或新赛季
状态: 归属不干净



页面名: `进入创造模式后的过渡页`
当前 detector: 暂无统一 detector
当前归属: 当前容易变成 `unknown`
建议归属: `main_flow`
进入后动作: 根据后续落到主界面/剧情页/奖励页继续分流
状态: 未正式分类

---

### New Season

页面名: `club_transfers`
当前 detector: `find_club_transfers_screen_in_screenshot()`
当前归属: `new_season_flow`
建议归属: `new_season_flow`
进入后动作: 点击续约，并处理后续 confirm
状态: 已明确

页面名: `club_transfers_level`
当前 detector: `find_club_transfers_level_screen_in_screenshot()`
当前归属: `new_season_flow`
建议归属: `new_season_flow`
进入后动作: 先点 `MIN`，再点确认
状态: 已明确

页面名: `sponsor_selection`
当前 detector: `find_sponsor_selection_screen_in_screenshot()`
当前归属: `new_season_flow`
建议归属: `new_season_flow`
进入后动作: 处理赞助商选择
状态: 已明确

页面名: `sp_join`
当前 detector: `find_sp_join_screen_in_screenshot()`
当前归属: `new_season_flow`
建议归属: `new_season_flow`
进入后动作: 选人、筛选、确认
状态: 已明确

页面名: `final_confirm`
当前 detector: `find_final_confirm_screen_in_screenshot()`
当前归属: `new_season_flow`
建议归属: `new_season_flow`
进入后动作: 点击最终确认，并等待 handoff
状态: 已明确

页面名: `new_season confirm chain`
当前 detector: `ok_button / ok_chs_button / popup confirm`
当前归属: `new_season_flow`
建议归属: `new_season_flow`
进入后动作: 清理确认链并继续到下一步
状态: 已明确，但仍偏动作链，不是正式 step

页面名: `新赛季额外剧情页/确认过渡页`
当前 detector: 暂无统一 detector
当前归属: 部分会被 `priority confirm` 吞掉
建议归属: `new_season_flow`
进入后动作: 作为新赛季正式子页面处理
状态: 未正式分类

---

### Recovery

页面名: `back_only`
当前 detector: stage `back_only`
当前归属: `recovery_flow`
建议归属: `recovery_flow`
进入后动作: 点击返回
状态: 已明确

页面名: `generic_confirm_fallback`
当前 detector: 无明确业务页时的右下角 confirm fallback
当前归属: `recovery_flow`
建议归属: `recovery_flow`
进入后动作: 点一次右下角
状态: 已明确

页面名: `light illegal dialogs`
当前 detector: `ok / continue / final_confirm_ok_xx / back`
当前归属: `recovery_flow`
建议归属: `recovery_flow`
进入后动作: 轻量清障
状态: 已明确

---

### Global / System

页面名: `close_button`
当前 detector: emergency / inline story close interrupt
当前归属: 全局中断
建议归属: 全局中断
进入后动作: 立即点击关闭
状态: 已明确

页面名: `login_retry`
当前 detector: emergency
当前归属: 全局中断
建议归属: 全局中断
进入后动作: 立即点击重试
状态: 已明确

页面名: `connecting`
当前 detector: `handle_connecting_screen()`
当前归属: 独立处理
建议归属: 单独系统页
进入后动作: 等待或处理连接提示
状态: 未正式归类

页面名: `unknown`
当前 detector: 无
当前归属: 顶层 / recovery
建议归属: 只保留为兜底状态
进入后动作: 不应该承载业务逻辑
状态: 已存在，但不应承担业务

---

## 你后面只需要改这些字段

如果上面有不对的地方，直接改：

- 当前归属
- 建议归属
- 进入后动作
- 状态

如果有漏掉的页面，直接继续往对应分组下面补。