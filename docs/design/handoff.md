# 策划线交接

清空上下文以后从这里接着做。规则和现状以各自的权威文件为准，这里只写"现在做到哪、下一步做什么、容易踩的坑"。

## 这条线管什么

2026-10-30 起按 [ADR 0010](../adr/0010-question-first.md)：关卡先出题（课程表 → 题卡 → 灰盒 → 配剧情和地图 → 实装），取代 0008/0009 的分层顺序。策划线管课程表和题卡；灰盒、打法脚本归关卡线；`docs/plan.md` 和 ADR 归总控。

- 出题手册 [question-handbook.md](question-handbook.md)：题卡模板（含强弱同源、每轮的取舍、漏洞表三栏）、自查清单 19 条、堵平推和拆源的六种结构、机制推论表、题型库。
- 课程表 [curriculum.md](curriculum.md)：9 个考点（K1～K9）、27 关的用途、一句话巧解、难度。
- 候选题卡 [cards/](cards/)：A4、S1、J7 各 3 张，末尾是评委意见和推荐顺序。
- 旧的第 1 层材料仍在，ADR 0010 第 4 条"配剧情和地图"时再用：[flow/README.md](flow/README.md)、[flowcheck.py](flow/flowcheck.py)、[flowview.py](flow/flowview.py)、[flow/style.md](flow/style.md)、[maps/README.md](maps/README.md)、[principles.md](principles.md)（P1～P35）。

## 现状（2026-10-30）

- **ADR 0010 第一周的策划线部分做完了**：手册、课程表初稿、9 张候选卡，评委（Sonnet 子 Agent，只读 ADR 和卡）挑过一轮漏洞。总控转来的用户想法（打前提不打结果、强弱同源、可推理的暗示、拿掉 / 漏洞 / 最优解三个自检、演示 → 小考 → 正题）已并进手册和三张推荐卡。
- **推荐**：A4 甲（三条街两个工兵）、S1 甲（拉上岸）、J7 甲（留着干扰车），都改成了"评委后第二版"。其余 6 张只记了评委意见，没改。
- **等用户**：每关挑一张卡；课程表审一次；定"三条线能不能任意顺序打"。
- **等关卡线**：打法脚本和检查器校准（ADR 0010 第 3 条），三张推荐卡的"怎么检验"栏是给它的断言。卡里标"待验证 / 待查"的机制要先上测试台：冰面承重、敌方干扰车对飞机、小地图按物体闪点、信息框、干扰光环的地面圈、重机甲砸冰墙。

## 下一步

1. 用户挑卡后：把选中的卡细化成灰盒需求（最简单的地图、原版单位，地图要求写进卡的漏洞表，例如 A4 街口宽 ≤ 200、三个接点分散；S1 的三层冰带；J7 的三条谷远近），交关卡线。
2. 用户审课程表后：其余 24 关逐关照手册出 3 张候选，先过第 16、17 条（强弱同源、每轮最优做法会变），再交评委。
3. 评委的做法可复用：独立 Sonnet 子 Agent，只给 ADR 0010 和卡片路径，让它扮"想偷懒的老玩家"按【平推】【拆源】【捷径】【巧解】【数值】挑。

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
