# 红警2 / 尤里的复仇：画面重置社区现状调研（2026-11-07）

只读调研，没下载、没运行任何程序。信息来自网页搜索和读页面；"未查到"就是没查到，没猜。
注意：很多 GitHub 页面抓取不到日期和细节（页面只返回摘要），下面凡是"日期不详"的都是这个原因。

## 一句话结论

**总控的初判要修正：红警2 的画面重置不是"没人做"，而是已经有两个人在走我们设想的两条路，而且都很新（2026 年 10～11 月还在更新）。** 立项前先别开工，先去看这两个项目能不能直接拿来用或合作。

| 路线 | 已有项目 | 进度 | 最近更新 |
| --- | --- | --- | --- |
| 包一层显示接口 | cnc-ddraw / TS-DDRAW / DDrawCompat | 成熟，已普及；只能放大和滤镜，不能让画面更清晰 | 持续维护 |
| 挂钩替换绘制（GPU 渲染） | hzqst 的 Phobos GPU Render 分支 | 实验中，有可下载的每日构建 | 2026-11-04 |
| 静态重编译 + 重做显示层 | sp00nznet/redalert2-recomp | v0.1.0 "可玩"，HD 体素 2x/3x 已做 | 2026-11-03 |
| 整个重写 | OpenRA ra2 mod；Chrono Divide | OpenRA 半停滞；Chrono Divide 测试版，只有联机 | 见下 |

## 1. 显示接口包装

- cnc-ddraw：GDI / OpenGL / Direct3D 9 三种后端、自动选择；GLSL 着色器放大、初步支持 libretro 着色器；窗口、独占全屏、无边框；限帧、垂直同步。支持列表里明确有红警2 和尤里的复仇。限制：只管 DirectDraw 软件渲染的游戏，游戏必须设成全屏。[GitHub](https://github.com/CnCNet/cnc-ddraw)
- 普及度：CnCNet 客户端的显示选项里有"自动 / CNC-DDRAW / TS-DDRAW"，FAQ 推荐窗口化用 TS-DDRAW。Steam/EA 版自带的默认是 narzoul 的 DDrawCompat。[CnCNet 论坛 FAQ](https://forums.cncnet.org/topic/6866-frequently-asked-questions)、[cncnz 安装指南](https://cncnz.com/features/technical-support-help-guides/installing-command-conquer-red-alert-2-yuris-revenge/)
- TS-DDRAW：[github.com/cnc-patch/ts-ddraw](https://github.com/cnc-patch/ts-ddraw)，细节未查到。
- 这一层的本质：游戏自己用 CPU 画好一张 8 位色的位图，它们只负责把位图贴到屏幕上。所以它们能放大、能加滤镜，但**不会让单位变清楚**。玩家社区也这么说："提高分辨率不会让画面更高清，只是显示范围变大、东西变小"。[Steam 讨论](https://steamcommunity.com/app/2229850/discussions/0/4299320559088147777)

## 2. 引擎扩展框架

| 项目 | 现状 | 来源 |
| --- | --- | --- |
| Ares | 新版本闭源（0.A 之后源码私有），Phobos 的诞生部分原因就是这个 | [PPM 论坛](https://ppmforums.com/topic-58574/phobos-v01-first-release) |
| Antares | Phobos 团队对 Ares 3.0p1 的开源重写，"不是优先项目"，和 Ares 互斥 | [GitHub](https://github.com/Phobos-developers/Antares) |
| Phobos | LGPL，基于 YRpp + Syringe；README 自述"维护不够积极，找维护者"；约 3300 提交 | [GitHub](https://github.com/Phobos-developers/Phobos)、[文档](https://phobos.readthedocs.io/en/latest/) |
| Vinifera | 泰伯利亚之日的同类框架；release 都算不稳定版；只管 TS | [文档](https://vinifera.readthedocs.io/) |
| YRpp / Syringe | Phobos 的底座（头文件库 + 注入器），单独状态未查到 | — |

Phobos 对绘制做过的事，**全是"修补和加配置项"，没有换渲染器**（文档逐项读过）：
- 体素：跳过缩到零的部分、可改光源方向（`VoxelLightSource`）、可固定体素光照、修炮塔偏移。
- 阴影、光照、色板：一堆位置修正，配置项化的色调；半透明 RLE SHP 换了更精确的混合。
- 界面：侧边栏计数器、工具提示背景、PCX 加载画面在大分辨率下居中；**没有任何"侧边栏随分辨率缩放"**。[界面文档](https://phobos.readthedocs.io/en/latest/User-Interface.html)、[修复与改进](https://phobos.readthedocs.io/en/latest/Fixed-or-Improved-Logics.html)

**GPU 渲染替换确实有人在做（关键发现）**：hzqst/Phobos 的 `feature/gpu-render` 分支，每日构建 gpu-2026.11.03.2 ～ 2026.11.04，Win32，用 SyringeEx 加 `-GPURender` 参数启用，着色器编成 DXIL 和 SPIR-V，窗口层用 SDL3；PR 内容是体素帧缓存、1000 单位的主线程性能剖析、前端菜单（OwnerDraw）搬到 GPU，作者称 D3D12 与 Vulkan 输出和 CPU 路径像素误差很小；官方说明"仍在开发，可能不稳定"。
- 来源（均为搜索结果页，**我直接抓取全部 404，细节只来自搜索摘要，需用户用浏览器确认仓库是否公开**）：[release 11.04](https://github.com/hzqst/Phobos/releases/tag/gpu-2026.11.04)、[PR #6](https://github.com/hzqst/Phobos/pull/6)、[PR #5](https://github.com/hzqst/Phobos/pull/5)、[PR #3](https://github.com/hzqst/Phobos/pull/3)
- 没查到：它是否已合入上游 Phobos、作者在哪个社区讨论、有没有文档、画面上除"对齐 CPU 路径"外有没有增强（高分辨率体素、新光照）。从 PR 标题看，**目前目标是"和原版像素一致且更快"，还不是"更好看"**。
- 上游 Phobos 的 issue / Discord 里有无 GPU 渲染讨论：**未查到**。

## 3. 已有的高清化 / 重制尝试

- **redalert2-recomp**（最值得看）：把 `gamemd.exe` 1.001 / `game.exe` 1.006 的二进制静态翻译成 C，跑的是 Westwood 原代码；加了 D3D11 显示层（720p～4K、宽屏、多种缩放）；**体素单位、它们的阴影、飞机可按游戏自己的体素模型画成 2x / 3x 分辨率**；菜单、skirmish、两个战役起头、LAN 联机、`mods/` 目录可用；MIT 协议，需要用户自己的正版文件，仓库不带游戏数据。路线图仍开放：体素动画和碎片、"更高分辨率的美术路径"（即 SHP 素材仍是原分辨率）、现代输入音频、合作战役、CnCNet 联机。**自己写明"CnCNet 的 Ares / Phobos 改 exe 的 mod 对它是问题，因为翻译出来的 C 跟不上对 exe 的补丁"。**[README](https://github.com/sp00nznet/redalert2-recomp)、[路线图](https://github.com/sp00nznet/redalert2-recomp/blob/main/ROADMAP.md)。作者和可信度：个人项目，96 个提交，v0.1.0；"30 项测试通过"是它自己的说法，我没验证。
- 高清素材包 / AI 放大精灵：**未查到**。搜到的 AI 放大都是过场视频（ClassiCinematics 的 4K 重制、Nexus 上的增强过场）。[PCGamesN](https://www.pcgamesn.com/red-alert-2-remastered)、[Nexus](https://www.nexusmods.com/commandandconquerredalert2/mods/140)
- 个别 mod（Yuri's Revenge Revolution 等）只是自带少量新图，不是高清包。[ModDB](https://www.moddb.com/mods/yuris-revenge-revolution)
- 另有早期小项目 ChronoStorm（Python/Pygame）、RedAlert2-Engine（TypeScript），页面只说"早期"，未细查。
- 官方源码：2025-02 EA 开源了 TD、RA、Generals/Zero Hour、Renegade（GPL），**不含红警2 和泰伯利亚之日**。[Gigazine](https://gigazine.net/gsc_news/en/20250228-ea-open-sources-command-and-conquer)

## 4. 重写路线

| 项目 | 完成度 | 渲染 | 许可证 |
| --- | --- | --- | --- |
| OpenRA ra2 mod | 无发布版；约 63 个开放 issue；最后推送约 2024-06（第三方统计，可能过期）；基于 OpenRA 的 2.5D 能力；必须有原版 `ra2.mix` | OpenRA 引擎自己的 2.5D；体素处理方式未查到 | GPL-3.0 |
| Chrono Divide | 测试版（页面截图 BETA v0.37）；联机和原版地图可玩；战役未确认 | 网页技术，具体库未查到 | 客户端源码是否公开**未查到**（GitHub 上只见 mod SDK 和机器人 API），站点自称非盈利粉丝项目 |

来源：[OpenRA/ra2](https://github.com/OpenRA/ra2)、[wiki](https://github.com/OpenRA/ra2/wiki)、[chronodivide.com](https://chronodivide.com)、[Heise](https://www.heise.de/en/news/Red-Alert-2-in-the-Browser-Fan-Project-Brings-Classic-to-the-Web-11087986.html)、[机器人库](https://github.com/Supalosa/supalosa-chronodivide-bot)。
重写路线的代价：规则和 AI 全要重做，已有的 Ares/Phobos mod 基本不兼容（Chrono Divide 称"很多原版 mod 几乎直接可用"，但没说 Ares 类 mod）。

## 5. 社区自己提到的难点

| 难点 | 社区说法 | 来源 |
| --- | --- | --- |
| 侧边栏写死像素 | 不随分辨率缩放，想变大只能降分辨率；过场视频也不缩放 | [Steam](https://steamcommunity.com/app/2229850/discussions/0/4299320559088147777) |
| 超高分辨率 | 改三个 ini 可到 1080p/1440p，4K 有的人崩溃 | [Gamepressure](https://www.gamepressure.com/newsroom/red-alert-2-resolution-fix-how-to-play-1920-x-1080/z36a9c) |
| 和 Ares/Phobos 兼容 | recomp 直接承认跟不上；GPU 分支是 Phobos 的分支，所以靠 Syringe 注入保持兼容 | recomp 路线图、hzqst 分支 |
| 阴影 | recomp 只提了体素阴影已做 | 路线图 |
| 色板动画、迷雾 | 社区资料里**未查到**专门讨论 | — |
| 素材版权 | recomp 和 OpenRA 都要求用户自带原版文件，仓库不带；不分发游戏数据 | 各项目 README |
| 高分辨率美术 | SHP 精灵（步兵、建筑、地形）依然是原分辨率；recomp 把它列为"未做" | 路线图 |

## 6. 结论与建议

**谁走到哪了**
- 显示接口层：已完成，没必要做。
- 挂钩换渲染器：hzqst 在做，**刚起步，目标偏"对齐 + 提速"**，画面增强还没出现。
- 重编译 + HD 体素：recomp 已做到 2x/3x 体素，**这是目前离"画面重置"最近的东西**，但不兼容 Ares/Phobos，也就是不兼容 Mental Omega 这类主流大 mod。
- 重写：OpenRA 慢，Chrono Divide 只管联机，都没把"更好看"作为主线。

**如果我们做，最值得的切入点（按推荐顺序）**
1. **不开新渲染器，先跟 hzqst 联系，在它的 GPU 路径上做"画面增强层"**：高分辨率体素（recomp 已验证体素本来就能放大）、光照/阴影后处理、侧边栏缩放。这条路兼容 Ares/Phobos，不用重复造渲染器。粗估：先评估 2 周（读代码、跑构建），增强层 2～3 个月单人，**前提是对方愿意合作且仓库公开**。
2. **只做高分辨率精灵素材**：给步兵、建筑、地形做 AI 放大或重绘包，配合上面任一渲染器使用。这块**真的没人做**（未查到任何素材包）；难点是素材量巨大、风格一致性、版权（重绘要避免直接分发 EA 原图的放大版）。粗估：样板 1 个月，全量要数月，大头是美术。
3. 自己写渲染器（挂钩 YRpp 或另起）：**不推荐**，两个项目已经在做，我们加入只会重复。

**要避开重复造轮子的地方**：显示接口包装、体素放大、D3D11 / Vulkan 呈现层、过场视频放大（已有）。

**待用户决定的 2 项**
1. 是否去联系 hzqst（或 recomp 作者）确认合作意向——我不能代发消息。
2. 红警2 画面线是否值得占额度：用户的真目标是自己的 RTS 独立游戏，这条线对它的直接价值有限，更像"练手 + 社区声望"。

**调研的盲区**：没读到 GPU 分支的真实代码和 README；没查 Discord / QQ 群 / 贴吧（国内社区可能有更多，网页搜索覆盖不到）；Chrono Divide 的渲染方式和代码是否公开未查清。
