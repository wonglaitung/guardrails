"""
LLM Judge 模块

与 Qwen3Guard-8B-Stream 交互，实现 Layer 2 实时裁判。
支持快速检测（无 CoT）和结构化结果返回。
支持结果缓存以减少重复调用。
"""

import json
import logging
import hashlib
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import httpx

try:
    from cachetools import TTLCache
    HAS_CACHE = True
except ImportError:
    HAS_CACHE = False
    TTLCache = None

from .config import JudgeConfig
from .exceptions import JudgeResult, JudgeTimeoutException, JudgeUnavailableException

logger = logging.getLogger(__name__)

# 缓存配置
CACHE_TTL = 300  # 5 分钟
CACHE_MAXSIZE = 1000  # 最多缓存 1000 条


class RiskLevel(Enum):
    """风险等级"""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# 快速检测 Prompt（无 CoT，追求速度）
FAST_JUDGE_PROMPT = """你是内容安全审核系统。请快速判断以下内容是否安全。

内容：
{content}

请直接输出 JSON 格式结果（不要输出其他内容）：
{{"is_safe": true/false, "risk_level": "safe/low/medium/high/critical", "risk_categories": ["category1", ...], "reason": "简短原因", "confidence": 0.0-1.0}}

风险类别可选：prompt_injection, harmful_content, pii_leakage, bias_discrimination, illegal_content, other"""

# 带上下文的检测 Prompt
CONTEXT_JUDGE_PROMPT = """你是内容安全审核系统。请结合上下文判断用户输入是否安全。

上下文：
{context}

用户输入：
{content}

请直接输出 JSON 格式结果（不要输出其他内容）：
{{"is_safe": true/false, "risk_level": "safe/low/medium/high/critical", "risk_categories": ["category1", ...], "reason": "简短原因", "confidence": 0.0-1.0}}"""

# 快速安全分数检测 Prompt（用于流式拦截）
QUICK_SCORE_PROMPT = """请快速评估以下内容的安全程度，只输出一个 0-1 之间的数字（0=完全危险，1=完全安全）：

{content}

安全分数："""


class ComplianceJudge:
    """合规性裁判 - 与 Qwen3Guard-8B-Stream 交互"""

    def __init__(self, config: JudgeConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout),
            http2=True,
        )

        # 初始化缓存
        if HAS_CACHE:
            self._judge_cache: TTLCache = TTLCache(maxsize=CACHE_MAXSIZE, ttl=CACHE_TTL)
            self._score_cache: TTLCache = TTLCache(maxsize=CACHE_MAXSIZE, ttl=CACHE_TTL)
            logger.info(f"Judge cache enabled: TTL={CACHE_TTL}s, maxsize={CACHE_MAXSIZE}")
        else:
            self._judge_cache = None
            self._score_cache = None
            logger.warning("cachetools not installed, Judge cache disabled")

        logger.info(f"ComplianceJudge initialized, endpoint: {config.endpoint}")

    async def judge(
        self,
        content: str,
        context: Optional[str] = None
    ) -> JudgeResult:
        """
        判断内容是否安全

        Args:
            content: 待检测的内容
            context: 可选的上下文信息（如对话历史）

        Returns:
            JudgeResult: 检测结果
        """
        # 生成缓存键
        cache_key = self._make_cache_key(content, context)

        # 检查缓存
        if self._judge_cache is not None and cache_key in self._judge_cache:
            cached_result = self._judge_cache[cache_key]
            logger.debug(f"Judge cache hit for content hash: {cache_key[:16]}...")
            return cached_result

        # 构建 prompt
        if context:
            prompt = CONTEXT_JUDGE_PROMPT.format(content=content, context=context)
        else:
            prompt = FAST_JUDGE_PROMPT.format(content=content)

        try:
            # 调用 Judge 服务
            response = await self.client.post(
                self.config.endpoint,
                json={
                    "model": self.config.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,  # 低温度保证一致性
                    "max_tokens": 256,
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            # 解析响应
            result = response.json()
            assistant_message = result["choices"][0]["message"]["content"]

            # 解析 JSON 结果
            judge_result = self._parse_judge_response(assistant_message)
            logger.info(f"Judge result: is_safe={judge_result.is_safe}, risk_level={judge_result.risk_level}, confidence={judge_result.confidence}")

            # 存入缓存
            if self._judge_cache is not None:
                self._judge_cache[cache_key] = judge_result
                logger.debug(f"Judge result cached: {cache_key[:16]}...")

            return judge_result

        except httpx.TimeoutException:
            logger.error(f"Judge service timeout: {self.config.endpoint}")
            raise JudgeTimeoutException(self.config.timeout, self.config.endpoint)

        except httpx.HTTPStatusError as e:
            logger.error(f"Judge service HTTP error: {e.response.status_code}")
            raise JudgeUnavailableException(self.config.endpoint, f"HTTP {e.response.status_code}")

        except httpx.RequestError as e:
            logger.error(f"Judge service request error: {e}")
            raise JudgeUnavailableException(self.config.endpoint, str(e))

        except Exception as e:
            logger.error(f"Unexpected error in judge: {e}")
            raise

    async def quick_check(self, content: str) -> float:
        """
        快速安全分数检测（用于流式拦截）

        返回 0-1 之间的安全分数，1 表示完全安全，0 表示完全危险。
        此方法追求速度，不返回详细分析。

        Args:
            content: 待检测的内容

        Returns:
            float: 安全分数 (0-1)
        """
        # 生成缓存键（quick_check 不使用 context）
        cache_key = self._make_cache_key(content, None)

        # 检查缓存
        if self._score_cache is not None and cache_key in self._score_cache:
            cached_score = self._score_cache[cache_key]
            logger.debug(f"Quick check cache hit: {cache_key[:16]}...")
            return cached_score

        prompt = QUICK_SCORE_PROMPT.format(content=content)

        try:
            response = await self.client.post(
                self.config.endpoint,
                json={
                    "model": self.config.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 10,  # 只需要一个数字
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result = response.json()
            assistant_message = result["choices"][0]["message"]["content"].strip()

            # 尝试解析分数
            try:
                # 尝试直接解析数字
                score = float(assistant_message.split()[0])
                score = max(0.0, min(1.0, score))  # 确保在 0-1 范围内
            except (ValueError, IndexError):
                # 解析失败，默认为安全（保守策略）
                logger.warning(f"Failed to parse quick_check score: {assistant_message}")
                score = 0.5

            # 存入缓存
            if self._score_cache is not None:
                self._score_cache[cache_key] = score

            return score

        except httpx.TimeoutException:
            logger.warning("Quick check timeout, defaulting to safe")
            return 0.5  # 超时时返回中等分数

        except Exception as e:
            logger.warning(f"Quick check error: {e}, defaulting to safe")
            return 0.5

    def _make_cache_key(self, content: str, context: Optional[str] = None) -> str:
        """生成缓存键"""
        key_data = f"{content}||{context or ''}"
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()

    def _parse_judge_response(self, response: str) -> JudgeResult:
        """解析 Judge 服务的响应"""
        # 尝试提取 JSON
        try:
            # 尝试直接解析
            data = json.loads(response)
        except json.JSONDecodeError:
            # 尝试从文本中提取 JSON
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # 解析失败，返回默认的安全结果
                logger.warning(f"Failed to parse judge response: {response}")
                return JudgeResult(
                    is_safe=True,
                    risk_level="safe",
                    risk_categories=[],
                    reason="Unable to parse judge response",
                    confidence=0.5,
                )

        # 构建结果
        return JudgeResult(
            is_safe=data.get("is_safe", True),
            risk_level=data.get("risk_level", "safe"),
            risk_categories=data.get("risk_categories", []),
            reason=data.get("reason", ""),
            confidence=data.get("confidence", 0.5),
        )

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
