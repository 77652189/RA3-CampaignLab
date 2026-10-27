# 决策索引

每条 ADR 只被取代、不被改写。

| 编号 | 标题 | 状态 | 摘要 |
|---|---|---|---|
| [0001](0001-sdk-v3-only.md) | 只用 Mod SDK v3.0 | accepted | 1.10 时代的旧 SDK 编出的 GameObject 布局旧，单位激活后随机堆损坏 |
| [0002](0002-ai-concept-hand-built-model.md) | AI 画概念图，手写几何建模 | accepted | AI 直接生成的网格表面软、细节丢，不当成品 |
| [0003](0003-standalone-repo-shared-locks.md) | 内容线独立成仓库，共享资源加锁 | accepted | 摩擦来自共享资源而非任务内容；配音线与内容线分仓，显卡与测试台用共享锁 |
| [0004](0004-no-status-filtered-vision.md) | 不用按状态过滤的索敌视野 | accepted | ObjectVisionRange 不检查状态，"优先打冰冻"改靠射速和快速换目标 |
| [0005](0005-own-pathfinder-music.md) | 自制配乐走原版的 Pathfinder 动态音乐，格式自己逆向 | accepted | 保留战况状态机，曲谱图和音轨自己生成，拼进 static 流；不绕开 Pathfinder，不等红3OL 开源 |
| [0006](0006-bench-slots.md) | 测试台同时开几局 | accepted | 游戏靠一个命名互斥锁只许开一份；测试台每局关掉自己的那个，按槽位加锁；用户的游戏不碰 |
