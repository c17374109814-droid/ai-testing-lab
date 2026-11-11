"""RAG 质量测试：检索相关性 + 生成忠实度。

需要评测模型 API Key（deepeval 默认读 OPENAI_API_KEY，或按官方文档配置自定义模型）。
未配置时整组跳过，CI 不会红。

运行:
    pytest suites/test_rag.py -v
"""
from __future__ import annotations

import os

import pytest
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

pytestmark = pytest.mark.skipif(
    not (os.environ.get("JUDGE_API_KEY") or os.environ.get("OPENAI_API_KEY")),
    reason="未配置评测模型 API Key，跳过 RAG 指标测试",
)

# retrieval_context 是检索器实际召回的片段 —— 定位问题时先看这里
CASES = [
    {
        "input": "会员多少钱？",
        "actual_output": "会员月付 12 元，年付 120 元。",
        "expected_output": "月付 12 元，年付 120 元。",
        "retrieval_context": ["极光云盘会员：月付 12 元，年付 120 元。"],
    },
    {
        "input": "单文件上限是多少？",
        "actual_output": "免费用户单个文件最大 5GB，会员最大 50GB。",
        "expected_output": "免费 5GB，会员 50GB。",
        "retrieval_context": ["单文件上限：免费用户 5GB，会员 50GB。"],
    },
    {
        "input": "支持哪些系统？",
        "actual_output": "支持 Windows、macOS、Linux、iOS、Android。",
        "expected_output": "Windows、macOS、Linux、iOS、Android。",
        "retrieval_context": ["极光云盘支持 Windows、macOS、Linux、iOS、Android。"],
    },
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["input"])
def test_answer_relevancy(case: dict) -> None:
    """回答是否切题。"""
    metric = AnswerRelevancyMetric(threshold=0.7)
    test_case = LLMTestCase(
        input=case["input"],
        actual_output=case["actual_output"],
        expected_output=case["expected_output"],
        retrieval_context=case["retrieval_context"],
    )
    metric.measure(test_case)
    assert metric.score >= 0.7, f"相关性不足: {metric.score:.2f} — {metric.reason}"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["input"])
def test_faithfulness(case: dict) -> None:
    """回答是否忠实于检索到的上下文（幻觉检测的核心指标）。"""
    metric = FaithfulnessMetric(threshold=0.8)
    test_case = LLMTestCase(
        input=case["input"],
        actual_output=case["actual_output"],
        expected_output=case["expected_output"],
        retrieval_context=case["retrieval_context"],
    )
    metric.measure(test_case)
    assert metric.score >= 0.8, f"忠实度不足: {metric.score:.2f} — {metric.reason}"
