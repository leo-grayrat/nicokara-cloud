# Audio-assisted Japanese reading probe design

## Goal

验证 nicokara-cloud 现有 MMS_FA 声学模型是否保留了足够的日语歌唱发音信息，从而让音频参与纠正歌词注音，而不是只用于时间轴对齐。

## Scope

这轮只做可行性实验，不修改正式 pipeline，不改变用户界面，也不接入网络歌词来源。

实验关注三层能力：

1. 从 MMS_FA 的 emission 做最简单的 CTC greedy decode，确认歌声中是否还能恢复出有意义的罗马字片段。
2. 将已知歌词作为约束，只在已知锚点之间观察/恢复疑难读音，例如 `この [宇宙] で` 中的 `宇宙`。
3. 如果自由恢复不稳，比较两个候选读音谁与同一段音频更匹配，让音频充当“裁判”。

## Design

新增独立实验目录 `experiments/audio-reading/`，复用当前 `torchaudio.pipelines.MMS_FA` 模型加载方式，但不调用正式 `MMSForcedAligner`。实验代码直接暴露声学 emission 的解码结果，输出结构化 JSON，便于人工比较。

第一步只实现纯函数级 CTC greedy decode，并通过合成 emission 单元测试验证：连续重复字符合并、blank 被删除、字符顺序保留。随后 probe 脚本再负责读取真实音频并调用 MMS_FA。

真实音频不提交仓库。实验输入目录加入 `.gitignore`；仓库只保存案例说明、脚本和结果摘要。

## Success criteria

第一轮不是要求完整准确转写整首歌。只要真实歌声上出现以下任一结果，就值得继续：

- emission 解码能保留足够多的实际发音骨架；
- 在已知锚点之间能区分 `そら` 与 `うちゅう` 之类候选；
- 候选读音的声学分数能稳定偏向实际唱法。

如果三者都不成立，则停止把 MMS_FA 作为读音恢复主方向，回到网络同曲读音/自动注音方案。
