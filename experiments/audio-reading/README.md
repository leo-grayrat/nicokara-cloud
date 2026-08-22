# 音频辅助日语注音实验

这个目录只用于验证一个问题：**nicokara-cloud 已经运行的 MMS_FA 声学模型，能否从真实歌声中保留足够的发音信息，用来纠正歌词注音。**

当前实验不会修改正式任务流程，也不会自动接受任何读音。

## 为什么做这个实验

现有流程先从歌词文字生成假名，再把这些假名转成罗马字交给 MMS_FA 做强制对齐。MMS_FA 实际上先计算逐帧的字符概率，但正式流程最后只保留时间位置和匹配分数。

这里先把那份声学输出直接拿出来，做最简单的 CTC greedy decode，观察像 `nakigoe`、`mezameta`、`sora` 这样的实际唱法是否还能留下可辨认的骨架。

另外准备一个更保守的实验：即使自由解码很脏，也可以把两个已知候选读音分别强制对齐到**同一份 emission**，比较哪个候选的平均声学分数更高。它验证的是“音频能不能当裁判”，而不是“模型能不能自由听写”。

## 文件

- `ctc_decode.py`：纯 CTC 合并逻辑，不依赖 TorchAudio。
- `mms_probe_utils.py`：MMS token 映射小工具。
- `probe_mms_emission.py`：加载真实音频并输出 MMS_FA 的原始 greedy decode。
- `candidate_score.py`：按对齐帧数加权候选读音分数。
- `compare_mms_candidates.py`：在同一段音频上比较多个罗马字候选。
- `cases.json`：第一批已知正确/错误读音案例。
- `results/README.md`：人工汇总结果。
- `data/`：本地真实音频，已忽略，不提交 Git。

## 环境

复用 nicokara-cloud 后端的 AI 依赖即可。仓库当前将 TorchAudio 固定在 `>=2.7.1,<2.8`。

例如在后端虚拟环境已经安装好的情况下，进入本目录运行：

```bash
python -m pytest -q test_ctc_decode.py test_mms_probe_utils.py test_candidate_score.py
```

## 实验 A：看 raw emission 还能听出什么

建议先截取 3～10 秒、包含目标词且尽量少伴奏干扰的片段，放到：

```text
data/example.wav
```

然后运行：

```bash
python probe_mms_emission.py data/example.wav --output results/example-greedy.json
```

有 CUDA 时 `--device auto` 会自动使用 CUDA；也可以显式指定：

```bash
python probe_mms_emission.py data/example.wav --device cpu
```

输出 JSON 中最值得先看的字段是：

- `decoded`：直接从每帧最高概率字符合并得到的粗糙序列；
- `greedy_frame_ids`：未合并的逐帧最高概率 token id；
- `token_dict`：MMS_FA 的字符表。

## 实验 B：让声音在候选读音之间裁判

候选要先写成 MMS 使用的规范化罗马字，只用小写拉丁字母和必要的 `'`，不要放空格。

例如验证 `泣き声`：

```bash
python compare_mms_candidates.py data/nakigoe.wav \
  --candidate nakigoe \
  --candidate nakikoe \
  --output results/nakigoe-candidates.json
```

验证 `目覚めた`：

```bash
python compare_mms_candidates.py data/mezameta.wav \
  --candidate mezameta \
  --candidate mesameta
```

脚本只运行一次声学模型，然后把候选逐个对齐到同一份 emission。输出中的 `score` 是按对齐帧数加权的平均分，`score_margin` 是第一名与第二名之差。

这里**暂时不设自动采用阈值**。第一轮只观察：实际唱法是否在不同歌曲片段上持续比错误候选得分更高，以及差距是否稳定。

对于 `sora` 和 `uchuu` 这种长度差很多的候选，单个词的平均分可能存在长度偏差。更可靠的后续实验会把相同的前后歌词也放进候选，例如比较整段 `konosorade...` 与 `konouchuude...`，让两边只在疑难部分不同。

## 怎么判断值不值得继续

不要用“能不能完整转写歌词”作为第一轮标准。这个模型本来不是自由听写器。

真正要看的是：

- `泣き声` 的片段里，`nakigoe` 是否比 `nakikoe` 更接近声学输出或取得更高候选分；
- `目覚めた` 是否能稳定区分 `z` 与 `s`；
- 明确唱作 `そら` 的 `宇宙` 是否更支持 `sora` 而不是 `uchuu`。

如果 raw decode 很脏，但候选比较稳定正确，那么正式方向就应当是**“已知歌词约束下的候选读音比较”**，而不是整首听写。

如果两种实验都无法稳定区分这些读音，就停止把 MMS_FA 当作主要读音恢复来源，回到网络同曲读音和现有自动注音路线。
