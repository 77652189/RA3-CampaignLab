# 0002 AI 画概念图，手写几何建模

**背景**：同一辆轻型坦克做了两版。AI 版用 HunyuanDiT 画概念图、Hunyuan3D-2 从图生成网格，再体素重建、平滑、减面（`experimental/units/ai_lighttank.py`、`ai_lighttank_blend.py`）；参数化版在 Blender 里手写几何（`cnv_lighttank.py`）。游戏内并排对比（CampNew24）。

**决策**：用户定下的流程是"AI 画概念图，我搭模型"：概念图用 AI，模型照着概念图手写几何（`cnv_lighttank2.py`）。

**后果**：AI 生成网格的流程和环境保留（`envs\ra3gen_env`），只用于出概念图和参考形状。

**否掉的方案**：直接用 AI 网格当成品——轮廓对，但表面凹坑裂缝多，平滑后像泥塑，概念图里的灯带、装甲缝、小部件都没了，不符合红警3的硬朗机械风格。
