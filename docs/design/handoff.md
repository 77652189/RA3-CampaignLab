# 策划线交接

清空上下文以后从这里接着做。规则和现状以各自的权威文件为准，这里只写"现在做到哪、下一步做什么、容易踩的坑"。

## 这条线管什么

2026-10-30 起按 [ADR 0010](../adr/0010-question-first.md)：关卡先出题（课程表 → 题卡 → 灰盒 → 配剧情和地图 → 实装），取代 0008/0009 的分层顺序。策划线管课程表和题卡；灰盒、打法脚本归关卡线；`docs/plan.md` 和 ADR 归总控。

- 出题手册 [question-handbook.md](question-handbook.md)：题卡模板（含强弱同源、每轮的取舍、漏洞表三栏）、自查清单 19 条、堵平推和拆源的六种结构、机制推论表、题型库。
- 课程表 [curriculum.md](curriculum.md)：9 个考点（K1～K9）、27 关的用途、一句话巧解、难度。
- 候选题卡 [cards/](cards/)：A4、S1、J7 各 3 张，末尾是评委意见和推荐顺序。
- 旧的第 1 层材料仍在，ADR 0010 第 4 条"配剧情和地图"时再用：[flow/README.md](flow/README.md)、[flowcheck.py](flow/flowcheck.py)、[flowview.py](flow/flowview.py)、[flow/style.md](flow/style.md)、[maps/README.md](maps/README.md)、[principles.md](principles.md)（P1～P35）。

## 现状（2026-10-30，灰盒后）

- **ADR 0010 第一周的策划线部分做完了**：手册、课程表初稿、9 张候选卡，评委（Sonnet 子 Agent）挑过一轮。
- **灰盒按 [ADR 0011](../adr/0011-graybox-by-simulator.md) 改成了模拟器定性分析**，关卡线的结论在 [graybox-cards.md](../story/graybox-cards.md)。三张推荐卡已按它改成**第三版**（每份卡末尾"灰盒后"一节写了改了什么）：
  - A4 甲：支点从"要换配兵""并路就赢"换成"接点相距 ≥ 800 护卫赶不及"+"绕行路长短差让兵错开到"+"号角间隔对冷却（用几道墙）"；
  - J7 甲：谷口一辆 → 每谷连摆三辆，选路变成"中谷拔两辆、远谷拔光就抢走近谷"的算术；
  - S1 甲：冰面承重标"留给实机"，补一组同时成立的宽度和镰刀跳跃的漏洞。
  - 推荐都没换（A4 甲 > 丙 > 乙；S1 甲 > 丙 > 乙；J7 甲 > 乙 > 丙），乙为什么不升见 a4.md 末尾。
- **给用户挑卡的对照页**：[cards/pick.md](cards/pick.md)。
- **课程表其余 24 关**过了第 16、17 条：11 关不合格已改句子、6 关补一句、7 关合格（[curriculum.md](curriculum.md) 第五节）。
- **等用户**：在 pick.md 挑卡；课程表第五节的改法；定"三条线能不能任意顺序打"。
- **等关卡线**：三张第三版卡的"灰盒"一栏是给它复算的（A4 每街 1050 打死车几秒、三组同时到 / 错开 / 分三份；J7 拔几辆后谁最快、反扑到达时刻）。待查的机制：冰面承重、镰刀跳距、能不能只禁技能、干扰对飞机、小地图按物体闪点、信息框、光环地面圈、重机甲砸冰墙。

## 下一步

1. 用户挑卡后：把选中的卡细化成灰盒需求交关卡线（地图要求已写在卡的漏洞表和规则栏：A4 接点间距、绕行路差、街口宽；S1 三层冰的宽度；J7 三谷长短和九辆的摆法）。
2. 关卡线复算三张第三版后：数字不撑就再改卡（A4 甲的退路是去掉"号角间隔不固定"）。
3. 用户审课程表后：其余 24 关逐关照手册出 3 张候选，从第五节改后的方向起步，再交评委。改后的句子里有不少新规则（时停区扩张、冰甲卸压、机关门轮班），出题时先查能不能做。
4. 评委的做法可复用：独立 Sonnet 子 Agent，只给 ADR 0010 和卡片路径，让它扮"想偷懒的老玩家"按【平推】【拆源】【捷径】【巧解】【数值】挑。

## 坑（出题）

- 用户先拆光压力源：任何挂在拆得掉的建筑上的压力都会被拆掉；"拆了 Z 它就弱"是外贴开关，不算题。压力源要拆不到（边界外、打不坏），或者拆它本身让局面变坏。
- 大团兵会站在汇合点、广场口当免费杀戮区：威胁的落点要分散、随时间变。
- 别让暗示直接说答案：台词和目标栏只说规则（"他们只认车，不认路"），不说解法。
- 每张卡写清空军、水陆、远程单位怎么处理，评委每次都会从这里绕。

## 常用命令（输出长的写进 work/logs，只看最后几行）

```
python -X utf8 docs/design/flow/flowcheck.py > work/logs/flowcheck.log 2>&1; tail -n 1 work/logs/flowcheck.log
python -X utf8 docs/design/maps/mapcheck.py a4 | tail -n 1
python -X utf8 docs/design/flow/flowview.py
python -m pytest -q tests/test_docs.py | tail -n 1
python -X utf8 docs/design/flow/flowpolish.py brief a4 <文件夹> [说明]
```

## 坑（工具）

- 钩子不让 heredoc、`python -c`、`sed -i` 里带反斜杠：写成草稿目录里的 .py 再跑。
- 查看器 `flowview.html` 是一整段脚本，一处语法错就整页空白（控制台不一定报）：改完用 node 检查——把 `<script>` 抽出来 `node --check`。全局名字别撞（`SIDE` 已经是角色阵营的颜色，建筑用 `OWNER`）。
- YAML：值不要以引号开头；流式列表里名字带逗号要加引号。
- 地图范围用 `BORDERS['whole']` 的矩形，不是 `island` 那个圆。
- 只提交 `docs/design/` 下自己的文件；`mechanics.md` 有时有关卡线没提交的改动，别带进去。不改 `docs/plan.md`、`docs/story/`。
