# 歌词读音结构诊断

这个实验只回答一个问题：**当前仓库在“分词 → 生成假名 → 再拆回汉字”这条链路里，到底在哪一步丢失了跨词/跨成分的读音变化。**

它不会修改正式注音逻辑。

## 第一首真实测试歌曲

选择クリープハイプ《おやすみ泣き声、さよなら歌姫》（2012）。

这首歌特别适合作为连浊结构测试，因为同一首歌里反复出现：

- `歌声` → `うたごえ`
- `泣き声` → `なきごえ`
- `歌姫` → `うたひめ`
- `無き声` → `なきごえ`

其中 `歌声`、`泣き声` 都能测试后项 `声` 的连浊，而 `歌姫` 提供了一个很好的“不发生类似浊化”的对照。`無き声` 又能观察不同表记是否仍映射到同一实际读音。

默认案例还保留一条很短的真实歌词上下文，避免只测试孤立词；不在仓库中保存整首歌词。

## 为什么要看这三份结果

当前本地注音大致是：

```text
歌词
  ↓
Janome 分词
  ↓
每个 Janome token 单独交给 pykakasi
  ↓
拼成整行读音
  ↓
split_token_by_kanji 再把读音分回具体汉字
```

因此同一个输入同时记录：

1. `janome_reading`：Janome 词典/形态分析自己给这个 token 的读音；
2. `pykakasi_for_token`：当前仓库实际更接近采用的“逐 Janome token 调 pykakasi”结果；
3. `pykakasi_whole`：不经过 Janome 切分，直接让 pykakasi 处理整串文字的结果。

这样可以区分几种完全不同的问题：

- Janome 已把 `泣き声` 当整体并给出 `なきごえ`，但 pykakasi 给错：说明现有代码可能丢掉了已经存在的读音信息；
- Janome 切成 `泣き / 声`，各自读音都正确，但拼接成 `なきこえ`：说明真正缺的是**成分之间的连浊/构词关系处理**；
- Janome 和 pykakasi 对整个词都已经正确：说明最初看到的错误来自别的路径（例如 DeepSeek 或旧版本），不能再把问题归咎于当前本地处理器。

## 运行

在已经安装 backend 依赖的环境中：

```bash
cd experiments/reading-structure
python probe_reading_structure.py
```

默认检查这首歌里的：

- `歌声`
- `泣き声`
- `歌姫`
- `無き声`
- 一条包含 `歌声` 的短歌词上下文

也可以追加任意歌词片段：

```bash
python probe_reading_structure.py 笑い声 雨音 星空
```

写入 JSON：

```bash
python probe_reading_structure.py --output result.json
```

## 最值得先看的字段

例如 `泣き声`：

```text
text
pykakasi_whole
pykakasi_after_janome_split
janome_joined_reading

tokens:
  surface
  part_of_speech
  base_form
  infl_type / infl_form
  janome_reading
  janome_phonetic
  pykakasi_for_token
```

这里暂时不实现任何连浊规则。先确认真实歌曲中的切词和读音来源，再决定修复点。
