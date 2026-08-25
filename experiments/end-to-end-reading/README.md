# 真实歌曲端到端注音对照

目的：不用孤立词直接喂注音器，而是让同一首真实歌曲完整走一遍 nicokara-cloud，比较“纯本地注音”和“启用 DeepSeek”两种实际结果。

测试歌曲：クリープハイプ《おやすみ泣き声、さよなら歌姫》。请自行准备原始 MV 与逐行歌词，本目录不保存歌曲或完整歌词。

重点检查：

- `歌声`：预期 `うたごえ`
- `泣き声`：预期 `なきごえ`
- `歌姫`：预期 `うたひめ`
- `無き声`：预期 `なきごえ`
- 歌词中的 `君`：结合上下文检查是否被误读为 `くん`

## 0. 准备

Windows 推荐直接使用项目 README 的 Docker Desktop 部署方式。

```powershell
git clone https://github.com/leo-grayrat/nicokara-cloud.git
cd nicokara-cloud
git switch experiment/audio-reading
docker compose up --build
```

首次运行会下载较大的 Whisper、UVR、MMS 模型。浏览器访问 `http://localhost:3000`。

## 1. 第一次：不启用 DeepSeek

确认当前 PowerShell 没有设置 DeepSeek Key：

```powershell
Remove-Item Env:DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
docker compose up --build
```

打开网页，用原始 MV + 普通逐行歌词提交任务。不要预先加入 `{漢字|かな}` 等人工注音。

到“确认假名注音”页面时：

1. 先不要修改任何读音；
2. 记录 `歌声 / 泣き声 / 歌姫 / 無き声 / 君` 的自动结果；
3. 记下任务 ID（任务页地址中可看到）；
4. 把 `storage/jobs/<任务ID>/lyrics_processed.json` 复制出来，命名为 `local.json`；
5. 然后可以继续确认并完成后面的时间轴和视频生成，以确认错误读音是否会继续影响对齐和字幕。

## 2. 第二次：启用 DeepSeek

停止服务：

```powershell
docker compose down
```

在当前 PowerShell 临时设置自己的 DeepSeek API Key：

```powershell
$env:DEEPSEEK_API_KEY="你的Key"
docker compose up
```

再次提交**同一个 MV、同一份歌词、同样的 ON/OFF VOCAL 选择**。仍然不要预先人工注音。

同样在确认页修改前记录结果，并复制：

```text
storage/jobs/<第二次任务ID>/lyrics_processed.json
```

命名为 `deepseek.json`。

不要把 API Key 写进仓库或上传给别人。

## 3. 自动提取目标词

在本目录执行：

```powershell
python compare_readings.py local.json deepseek.json
```

会输出两次运行记录的 `provider` 和目标词读音。把两份原始 JSON 或这份输出交回来即可。

如果只完成了一次运行，也可以：

```powershell
python compare_readings.py local.json
```

## 4. 这次实验回答什么

这组实验主要回答：

1. 不配置 DeepSeek 时，真实完整流程是否复现此前局部测试发现的错误；
2. 配置 DeepSeek 后，`泣き声 / 無き声 / 君` 是否真的得到改善；
3. DeepSeek 与本地结果不同时，最终确认页和后续时间轴使用的是哪一个；
4. 错误读音是否进一步造成 Mora 对齐或最终字幕问题。

先记录事实，不在这一轮修改正式注音架构。
