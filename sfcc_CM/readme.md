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




按钮监测：
“再试一次”优先级最高，无论何时遇到了都第一时间点击，无需排除
“OK”“确定”“继续”“关闭”“返回”优先级次高，遇到就直接点击，但是会有一些界面进行排除，如下文

界面监测：
登录流bootstrap：
1. 登录界面（识别模板 login_mark），识别出来之后点1次，等待进入游戏主界面
2. 游戏主界面（识别模板 game_main_mark），识别出来之后点击创造球会模式（识别模板 game_main_mark），等待进入 保存数据一览
3. 保存数据一览（OCR识别左上角），识别出来后点击第3个存档 
排除：该界面中返回按钮不能点击

创造模式流main：
1. 创造模式主界面（识别模板 creative_mode_advance_schedule_button_small），识别出来后有3个行为：切3倍速、特别训练、推进日程
2. 特别训练设置（OCR识别左上角），识别出来后有4个行为：全部重置、推荐、进行特训、返回
排除：该界面中“返回”按钮最后点击
3. 收支·球迷 界面（OCR识别左上角），识别出来后有2个行为：切换3倍速，点击继续
排除：该界面中“继续”按钮最后点击
4. 剧情界面（识别模板 log，在右上角），识别出来后点击skip
识别到小三角log_mark，就一直点击右下角区域

新联赛选择流new_season：
1. 联赛等级选择界面（OCR识别中心），识别出来后有2个行为：点击min，点击“确定”
排除：该界面中“确定”按钮最后点击
2. SP球员加盟界面（OCR识别屏幕最上方），识别出来后有3个行为：切换筛选、选择球员、最后点击加盟

疑似可以修改的界面
1. 俱乐部转会界面（OCR识别左上角），该界面只有“续约”按钮需要点击，是否可以将“续约”作为按钮监测，这样子就无需识别该界面了
2. 最终确认界面（OCR识别上方区域），该界面只有“确定”按钮需要点击，是否可以直接按按钮监测来执行



1. 阶段切换规则
bootstrap -> main:
bootstrap -> new_season:
main -> post_schedule_exception:
main -> new_season:
new_season -> main:

2. 推进日程后的分支
分支A:
识别标志:
动作顺序:
结束条件:

分支B:
识别标志:
动作顺序:
结束条件:

3. 新赛季固定链
club_transfers:
club_transfers_level: 
final_confirm:
sp_join:

4. 比赛/异常链
识别标志:
动作顺序:
结束条件:

5. 剧情链
识别标志:
动作顺序:
结束条件:

6. 禁止误点规则
界面:
不能点:
必须先点:
最后点:

7. 通用按钮优先级
login_retry:
close:
ok/confirm:
continue:
back:
skip:

8. 重启后中途界面规则
落在sp_join:
落在match_reward:
落在剧情log:
落在普通确认框:

9. 最需要提速的场景
1.
2.
3.

10. 补充截图/日志


我先给出main的具体链路，你分析改动方案：
main 固定链 以下都属于main固定链，不要写post_schedule_exception了
creative_mode_main
 识别：creative_mode_advance_schedule_button_small
动作顺序：
先切 3 倍速
再尝试特别训练，如果点击2次后未进入特别训练界面，则跳过
再推进日程，可能会出现1~2次 确认框，点击确认

下一步：
正常情况下 自动推进阶段
部分情况下 会进入剧情阶段
如果是中途重启了游戏，会进入 异常比赛阶段
之后会回到 creative_mode_main

极少数情况会进入 联赛结束阶段
之后会进入 new_season



special_training
       识别：左上 OCR 特别训练设置
        动作顺序：
全部重置，二次确认框中点击 OK
推荐，
进行特训，二次确认框中点击 OK，概率出现第2个二次确认框点击OK
返回, 之后一定来到 creative_mode_main

自动推进阶段：
不需要做任何事情，等待即可，只要画面在变化就一直等待，之后会回到creative_mode_main

剧情阶段：
识别：右上 log
动作：先点 skip，如果剧情还在，继续点推
可能出现 continue/ok，直接点击

异常比赛阶段：
识别：左上 OCR 比赛开始
动作顺序：
点击 查看结果，进入一段动画，然后进入下一页
点击 继续，进入下一页
点击 继续，进入下一页
点击 继续，进入下一页 收支·球迷

收支·球迷match_reward：
识别：左上 OCR 收支·球迷
动作顺序：
切 3 倍速
点击 继续 回到自动推进阶段

联赛结束阶段season_end
识别：左上 OCR 梦幻球队
动作顺序：
持续点击右下角OK，点一次右下 OK 后，如果当前仍在 season_end 链中，就继续点




new_season 固定链

1. club_transfers
最强识别：左上 OCR 俱乐部转会
动作顺序：
1. 点击右下角续约
2. 进入切页/确认过渡态
3. 优先等待二次确认框 ok_chs_button，并点击
4. 点击确认后，再进入 club_transfers_level
5. 如果未检测到 ok_chs_button，但已明确进入 club_transfers_level，也允许继续

下一步：club_transfers_level
切页动画：1秒
顺序约束：无

2. club_transfers_level
最强识别：中部 OCR 选择联赛等级
动作顺序：先点 min 再点 确定，然后等一会儿 出现二次确认框，点击ok_button

下一步：选择赞助商
切页动画：有 2秒
顺序约束：min一定在确定之前点击，除非找不到

3. 选择赞助商
最强识别：顶部 OCR 选择赞助商
动作顺序：无条件直接确定 点击 右下角 确定final_confirm_ok_button、final_confirm_ok_button2
下一步：特殊球员加盟 SP_Join
切页动画：有
顺序约束：无

4. sp_join
最强识别：顶部 OCR 特殊球员加盟
筛选入口：sp_join_filter_entrance
动作顺序：
点击筛选入口，在弹出的二次确认框中点击 OK
选择最多3个球员并排除有所属中标志sp_belong的
如果没有球员合适，向下滑动3次，选择最多3个球员
滑动到底后如果还是没有合适球员，跳过选择球员
点击右下角加盟

选择几名球员：3
哪些不能选：有所属中标志sp_belong
加盟后确认框数量：没有
下一步：最终确认
切页动画：2秒
顺序约束：有


5. final_confirm
最强识别：顶部 OCR 最终确认
动作：点击 右下角 确定final_confirm_ok_button、final_confirm_ok_button2
二次确认框 点击确定ok_chs_button
下一步：  creative_mode_main
切页动画：3秒
顺序约束：无

6. new_season 结束条件
结束条件：只有回到 creative_mode_main 才算 new_season 结束
如果中途又出现普通 OK/continue，仍然属于 new_season 内部链

7. 中途重启接管
落在以上任何一个界面，都属于 new_season 内部链，按照顺序继续往前走



save_selection 后进入 post_save_handoff 状态：

优先判断顺序：
1. new_season 任一步
2. creative_mode_main
3. main 固定链中的中间态（剧情 / continue / 收支·球迷 / 比赛开始）
4. 若以上都未识别，则继续等待

行为：
- 命中 new_season 任一步，直接进入 new_season_flow
- 命中 creative_mode_main，直接进入 main_flow
- 命中 main 固定链中间态，直接进入 main_flow
- 在该状态中，不走通用按钮逻辑抢先处理