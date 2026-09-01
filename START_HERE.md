# START HERE

SubtitleFlow 是一套**通用的、多证据源字幕生产工作流**。它不是《哆啦A梦》专用脚本；《哆啦A梦》只作为压力测试样例。

## 1. 环境

最低：Python 3.11+。

推荐工具：

- OpenCode V2：AI 编排、研究、语义候选、独立 QA。
- OpenCC：台繁→简体字转换。
- FFmpeg/ffprobe：媒体探测与实际画面字幕渲染。
- MKVToolNix (`mkvmerge`)：最终无损 Remux。

安装开发模式：

```bash
python -m venv .venv
# macOS/Linux
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[full]'
subflow doctor
```

也可以用 uv：

```bash
uv sync --extra full
uv run subflow doctor
```

## 2. 在仓库根目录启动 OpenCode

```bash
opencode
```

OpenCode 会读取：

- `AGENTS.md`
- `opencode.jsonc`
- `.opencode/agents/`
- `.opencode/skills/`
- `.opencode/commands/subtitle/`

## 3. 建一个项目

例如：

```bash
subflow project init my-series --name "My Series"
subflow title init my-series movie-01 --name "Movie 01"
```

导入四种证据：

```bash
subflow source add my-series movie-01 A /path/to/timing-master.ass
subflow source add my-series movie-01 B /path/to/jp-zh.ass
subflow source add my-series movie-01 C /path/to/ja.ass
subflow source add my-series movie-01 D /path/to/tw-dub.ass
```

角色固定：

- A：Timing Master
- B：日配中文现成译本
- C：日文原字幕
- D：台配字幕/台配对白文本

## 4. OpenCode 日常入口

```text
/subtitle/research my-series movie-01
/subtitle/prepare my-series movie-01
/subtitle/run my-series movie-01
/subtitle/review my-series movie-01
/subtitle/semantic-qa my-series movie-01
/subtitle/visual-review my-series movie-01
/subtitle/release my-series movie-01
/subtitle/remux my-series movie-01
```

`/subtitle/run` 的设计目标是：**自动推进到下一个必须由人决定的 Gate，然后停。**

## 5. 最重要的质量规则

- 原始 source 永不直接修改。
- 不按字幕行号硬对齐。
- 台配字幕忠于台配；日配字幕忠于日文原文。
- 确定性的旧译名/术语可自动改。
- 任何语义修改必须人工批准。
- ASS 特效/定位/绘图事件默认保护。
- 成功渲染 PNG 只表示 Render 通过；必须真正检查画面后才能标记 Visual QA。
- QA 之后 workfile / glossary / config / review 发生变化，旧 QA 自动视为 stale。
- 没有实际运行 `mkvmerge` 就不能说 Remux 通过。

详细流程见 `docs/workflow.md`。
