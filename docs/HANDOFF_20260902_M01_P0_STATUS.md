# SubtitleFlow M01 P0 双语字幕工作状态与交接文档

**日期**: 2026-09-02  
**作者/维护者**: Kiwi / SubtitleFlow Core  
**当前状态**: P0 完成并通过全量回归验证，支持无缝切换到下一台电脑继续开发

---

## 1. 本次完成的核心工作

### 1.1 双语单行与 1 对 1 精准对齐
- **同屏排版行预折叠 (`src/subtitleflow/cue_views.py`)**:
  日文源 ASS 常为了排版折成同起止时间的上下两行（如 `\pos(..., 898)` 和 `\pos(..., 1018)`），在证据提取层预先合并为逻辑上的单句，避免分词断裂。
- **对齐层防跨句贪婪合并 (`src/subtitleflow/alignment.py`)**:
  在 `_match_cost` 中加入组内间隙约束（内部 gap > 600ms 拒绝合并）与重叠率下限（overlap < 0.20 拒绝匹配），彻底解决旧对齐把相隔数秒的前置感叹词（如 `(一同)ああっ`）强行揉进后续台词的问题。
- **文本单行压平 (`src/subtitleflow/reconciliation.py`)**:
  日文源文本压平为单行，非必要（字符数 > 34 且超宽）不拆行。
- **统一基线与固定行距 (`src/subtitleflow/layout.py` & `compile.py`)**:
  单行双语垂直坐标全片固定为 `ZH: 394` / `JA: 460`，中日行距全局一致，不再随内容波动。

### 1.2 跨平台与字体修复
- **macOS Canonical Path 修复 (`src/subtitleflow/review.py`)**:
  基于 `paths.title.resolve()` 计算相对路径，解决 macOS `/var` 与 `/private/var` 符号链接导致的 subpath 报错。
- **字体特殊字符规范化 (`src/subtitleflow/text.py`)**:
  自动将日文连贯符号 `➡` (U+27A1) 规范化为文泉驿微米黑支持的 `→` (U+2192)，避免 libass 触发系统 ZapfDingbats 意外回退。

---

## 2. 验证与产物状态

- **单元测试**: 150 个 pytest 全部 PASS (`pytest -q`)
- **代码规范**: Ruff format & Ruff check 全部 PASS
- **打包检查**: `uv build` 成功，Wheel 与 sdist 正常生成
- **系统状态**: `subflow --json doctor` 全部检查项通过
- **最终产物（已生成于 `SubtitleFlow-local-artifacts/final-m01-p0/`）**:
  - `M01.jp-zh-bilingual.ass`（双语对齐字幕，1627 对白事件，包含 691 对 1:1 日语对白）
  - `SubtitleFlow-M01-JP-ZHCN-Bilingual-Demo.zip`（包含 ASS、报告、字体清单及 12 张渲染图的确定性发布包）
  - 12 张 1080p 真实 FFmpeg/libass 渲染帧

---

## 3. 换电脑继续工作指引

### 3.1 检出分支
在另一台电脑上：
```bash
git fetch origin
git checkout feat/m01-p0-bilingual-collector
uv sync --all-extras --dev
```

### 3.2 运行完整验证与产物 Pilot
```bash
# 验证代码与测试
uv run pytest -q
uv run ruff check .

# 运行 M01 双语产物生成（需本地安装带 libass 的 ffmpeg）
SUBTITLEFLOW_M01_ARTIFACT_DIR=/path/to/artifacts uv run python tools/run_m01_artifact_pilot.py
```

---

## 4. 明确 Deferred 的事项（供下一阶段参考）
1. **Full-video visual QA**: 需要完整 1080p 视频文件支持。
2. **Scene occlusion review**: 画面遮挡与复杂场景避让。
3. **MKV remux / attachment verification**: 需要安装 `mkvtoolnix` (`mkvmerge` / `mkvextract`)。
4. **全片语义深度校对（Human Review）**: 当前 Pilot 包含 1 个受控语义修正 fixture（犹太洲 -> 犹他州），全片 824 句的逐句人工审校可在后续阶段推进。
