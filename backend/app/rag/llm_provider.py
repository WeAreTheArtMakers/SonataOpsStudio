from __future__ import annotations

import hashlib
import logging
import random
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMProvider(Protocol):
    name: str

    async def chat(self, system_prompt: str, user_prompt: str) -> str:
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...


def deterministic_embedding(text: str, dims: int = 1536) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], byteorder="big", signed=False)
    rng = random.Random(seed)
    return [rng.uniform(-1.0, 1.0) for _ in range(dims)]


@dataclass
class MockProvider:
    name: str = "mock"

    async def chat(self, system_prompt: str, user_prompt: str) -> str:
        signature = hashlib.md5((system_prompt + user_prompt).encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
        return (
            "## Summary\n"
            "The anomaly likely reflects a combination of recent operational changes and demand variation [1][2].\n\n"
            "## Likely Causes\n"
            "1. Deployment or config drift in upstream systems [1].\n"
            "2. Campaign or traffic burst increasing load [2].\n\n"
            "## Business Impact\n"
            "Elevated risk of slower response and reduced conversion during peak intervals [2].\n\n"
            "## Next Steps\n"
            "- Validate release window and rollback threshold [1].\n"
            "- Scale capacity guardrails for near-term traffic [2].\n"
            f"\n_Deterministic mock signature: {signature}_"
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [deterministic_embedding(text) for text in texts]


@dataclass
class OpenAICompatibleProvider:
    name: str
    api_key: str
    base_url: str
    model: str

    async def chat(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as exc:
                logger.exception("invalid llm response format")
                raise RuntimeError("invalid llm response") from exc

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Demo-safe deterministic embeddings for both providers.
        return [deterministic_embedding(text) for text in texts]


def build_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()

    if provider == "groq" and settings.groq_api_key:
        return OpenAICompatibleProvider(
            name="groq",
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile",
        )

    if provider == "zai" and settings.zai_api_key:
        return OpenAICompatibleProvider(
            name="zai",
            api_key=settings.zai_api_key,
            base_url="https://api.z.ai/v1",
            model="glm-4.5",
        )

    return MockProvider()
