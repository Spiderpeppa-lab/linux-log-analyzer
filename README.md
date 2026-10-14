# Linux 日志智能分析器

读取 Linux 日志，用正则提取字段，用 pandas 统计服务和级别，生成 Markdown 报告并给出智能摘要。

```bash
python3 -m venv .venv
.venv/bin/pip install pandas tabulate
.venv/bin/python analyze_logs.py data/sample.log -o reports/sample.md
```

调用 AI 生成中文诊断（支持 OpenAI 兼容服务）：

```bash
export AI_API_KEY='在终端中设置，不要写入文件'
export AI_BASE_URL='https://api.openai.com/v1'  # 可选
export AI_MODEL='gpt-4o-mini'                    # 可选
.venv/bin/python analyze_logs.py data/sample.log --ai -o reports/ai-report.md
```

未设置 `AI_API_KEY` 时会使用本地规则摘要，方便离线演示；程序默认只读日志，不修改系统文件。
