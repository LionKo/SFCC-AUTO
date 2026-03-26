需要制作一个游戏的自动化测试脚本，有主流程和各种界面情况需要处理，需要你使用python/图像识别/文字识别等技术来实现。
游戏的进程是“FootballClubChampions.exe”

运行环境：
- 平台：Windows 11
- 分辨率：1920x1080
- 窗口模式：窗口化
- 输入方式：鼠标点击


第一阶段的任务是完成“创造模式”的主流程推进
文件夹CM_PNG的图片定义如下：
creative_mode_main_screen 为创造模式主界面，判断标准是creative_mode_advance_schedule_button或creative_mode_advance_schedule_button2存在
creative_mode_advance_schedule_button和creative_mode_advance_schedule_button2 为 推进日常按钮，这有2个状态，都表示同一个按钮
creative_mode_special_training_button和creative_mode_special_training_button2 为 特殊训练按钮，这里有2个状态，都表示同一个按钮
special_training_settings_screen和special_training_settings_screen_empty 为特殊训练设置界面，标准是左上角的图片是special_training_settings_title

推进日程：creative_mode_advance_schedule_button或creative_mode_advance_schedule_button2

全部重置：special_training_reset_all_button 和 special_training_reset_all_button2
推荐：special_training_recommend_button 和 special_training_recommend_button2
进行特训：special_training_execute_button 和 special_training_execute_button2
返回：back_button
特别训练:creative_mode_special_training_button 和 creative_mode_special_training_button2 和 creative_mode_special_training_button3


如果当前处于创造模式主界面中，需要按顺序进行2个行为：
第1步，点击特殊训练按钮，如果点击2次没有反馈，则说明无需操作。否则会进入 特殊训练设置界面在该界面要进行4个行为：
1. 点击“全部重置”按钮，图片为“special_training_reset_all_button” ，会进入二次确认框special_training_reset_all_confirm_dialog，点击绿色的按钮“Ok”ok_button即可
2. 点击“推荐“按钮special_training_recommend_button，
3. 点击”进行特训“按钮，special_training_execute_button，会进入二次确认框special_training_execute_confirm_dialog，点击绿色的按钮“Ok”ok_button即可
大部分情况会额外弹出1个二次确认框，special_training_execute_confirm_next_dialog，同样点击OK即可
4. 最后点击 左上角的三角按钮返回special_training_settings_title

第2步，点击"推进日程"按钮,creative_mode_advance_schedule_button或creative_mode_advance_schedule_button2

之后等待一段时间会回到创造模式主界面


特殊情况处理：
如果找不到上述任何操作区域，则点击一次鼠标，间隔为1s
如果遇到了“查看结果”按钮match_result_button，进行点击
如果遇到了“继续”按钮continue_button，进行点击
比赛奖励界面：match_reward_screen，识别标题为 match_reward_title
在比赛奖励界面中，优先将1倍速改为3倍速


如果一直处于同一个页面超过5分钟，则杀掉游戏进程重新进入游戏


以上是 单个赛季的循环逻辑，接下来要处理新赛季的逻辑。
以实现 新赛季逻辑->单赛季循环->新赛季逻辑->单赛季循环的循环

俱乐部转会页面为 club_transfers_screen，标题为 club_transfers_title
续约：club_transfers_renewal_button 和 club_transfers_renewal_button_2

选择联赛等级 页面为 club_transfers_lv_screen，标题为 选择联赛等级 club_transfers_lv_title
最小难度：club_transfers_min_button



先实现如下逻辑：
1. 界面为 俱乐部转会，点击按钮 续约
2. 中间遇到返回按钮不点击，遇到 确定/oK按钮时进行点击
3. 进入选择联赛等级界面club_transfers_lv_screen后，先点击最小难度：club_transfers_min_button，再点击确定

特殊球员加盟 页面为 sp_join_screen，标题为 特殊球员加盟 sp_join_title
“所属中”标签 sp_belong
加盟按钮 sp_join_button1/sp_join_button2/sp_join_button3/sp_join_button4

接下来实现特殊球员加盟逻辑：
1. 在特殊球员加盟界面 sp_join_screen，需要设计一套方案进行识别并点击球员卡片
2. 在特殊球员加盟界面sp_join_screen时，选择SP球员之前加一步筛选的操作，
点击 筛选按钮sp_join_filter_entrance，会打开二次确认框 sp_join_filter_popup，点击确认按钮即可
3. 选择至多3名SP球员，条件是 没有“所属中” sp_belong标签。如果没有符合条件的就不选择
4. 最后点击“加盟”按钮


新赛季的 最终确认逻辑：
最终确认页面：final_confirm_screen，标题为 final_confirm_title
最终确认按钮：final_confirm_ok_button 或 final_confirm_ok_button2

在最终确认界面点击 确认后，即可进入新赛季，接上单赛季循环逻辑


需要整体理一遍逻辑顺序，这里有问题：
新赛季逻辑：俱乐部转会页面 点击续约->联赛等级界面 选择最小难度 -> 特殊球员加盟 -> 最终确认->单赛季循环逻辑

在推进日程后，会遇到事件，目前只点击左键有点慢，如果看到了 skip按钮skip_button，可以点击


现在进行第3层逻辑，启动游戏找到梦幻模式入口，只有需要重启游戏的时候才调用这部分逻辑，需要单独处理。

登录界面全图：login_screen_full，上面的标志图形为login_mark
游戏主界面：game_main_screen,上面的核心标志为 game_main_mark
创造模式入口：game_main_create_entrance 或 game_main_create_entrance2
存档选择界面：save_selection,标题为 save_selection_title


1. 启动游戏，游戏的地址为"E:\SteamLibrary\steamapps\common\SegaFCC\FootballClubChampions.exe"
2. 如果当前在 登录界面login_screen，点击鼠标左键，等待游戏进入游戏主界面
3. 如果当前在游戏主界面，点击 创造模式入口，进入存档选择界面 
4. 如果当前在存档选择界面，该界面有3个存档，设计一个选择逻辑，选择第3个存档



层级：
1. 登录 模板在login
只有在重启游戏时触发，其他时间无需判断


2. 创造模式 模板在CM_PNG

3. 新赛季 模板在new_season
只有在创造模式结束后进行新赛季时需要

4. 通用 模板在common
弹窗
非法界面



