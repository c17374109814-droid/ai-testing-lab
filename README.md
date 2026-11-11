# ai-testing-lab

面向「AI 测试工程师」的学习 + 作品集仓库：**把 LLM 应用的评测做成可回归、可上 CI 的测试资产**。

> 目标岗位能力：评测集设计 → 指标定义 → 自动化跑分 → 阈值门禁 → badcase 复盘。
> 每个目录都对应面试可讲的一环，`reports/` 就是你的成长记录。

## 目录结构

```
ai-testing-lab/
├─ README.md                    # 路线图 + 每周进度
├─ evals/
│  ├─ golden_set.jsonl          # 评测样本（逐周扩充到 50+ 条）
│  └─ judge.py                  # LLM-as-judge：逐条打分 + 生成报告
├─ suites/
│  ├─ test_rag.py               # RAG 质量：相关性 / 忠实度（deepeval）
│  └─ test_injection.py         # Prompt 注入 / 越狱：拒绝行为检测
├─ reports/
│  └─ *.md                      # 每次跑分报告（自动生成）
└─ .github/workflows/eval.yml   # push 即跑，低于阈值直接 fail
```

## 快速开始

```bash
pip install -r requirements.txt
export JUDGE_API_KEY=sk-xxx          # DeepSeek / OpenAI / 兼容网关的 key
python evals/judge.py --threshold 0.85
pytest suites/ -v
```

> `suites/test_injection.py` 的 `inj-10` 是故意泄露的演示样本，已标为 `xfail`，所以 pytest 整体是绿的；把它改成正确拒绝后会出现 `XPASS`，提醒你更新预期。

默认评测模型走 DeepSeek（`https://api.deepseek.com` + `deepseek-chat`），换模型用：

```bash
export JUDGE_BASE_URL=https://api.openai.com/v1
export JUDGE_MODEL=gpt-4o-mini
```

## 12 周进度

| 周 | 目标 | 交付物 |
|---|---|---|
| 1–2 | Python + LLM API 基础 | 能调通模型、会改 prompt/温度 |
| 3–4 | 第一个 eval | `golden_set` 20 条 + 跑分报告 |
| 5–6 | RAG 测试 | 检索与生成分开测 |
| 7–8 | 安全 + 性能 | 注入用例库、延迟/成本拆解 |
| 9–10 | CI 门禁 | `eval.yml` 跑通，指标不达标即 fail |
| 11–12 | 收尾 | README 作品集化、面试题复盘 |

## 评测方法说明（面试重点）

- **golden_set 来源**：真实用户问题 + 产品文档片段 + 人工确认的参考答案；禁止用模型自己生成的标准答案当标尺。
- **LLM-as-judge 的偏差**：位置偏差、自我偏好、打分漂移。应对：固定 judge 模型版本、打分规则写死、抽样人工复核、周期性用人工标注校准。
- **阈值**：0.85 是演示值；真实项目按业务容忍度定，并区分「必须 100% 的核心用例」和「允许波动的边缘用例」。

## CI 说明

仓库 Settings → Secrets and variables → Actions 里添加 `JUDGE_API_KEY`（变量可选 `JUDGE_BASE_URL` / `JUDGE_MODEL`）。
未配置时流水线跳过评测但保留报告归档，因此 fork 者不会因为没 key 就红。

## 反模式（别这么做）

- 只 star 不写、只 commit 不 PR——提交历史里看不到任何决策过程。
- 把教程代码原样搬进作品集——面试追问「为什么这么设计」就露馅。
- 评测集全是模型生成——自己给自己出题、自己打分，没有意义。
