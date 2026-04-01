# this file provides multi provider llm fallback
import json
import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LlmRouter:
    # this class sends one prompt through configured fallback providers
    def __init__(self) -> None:
        # this method loads provider settings once
        self.settings = get_settings()
        self.chain = [item.strip().lower() for item in self.settings.llm_chain.split(",") if item.strip()]

    async def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 700) -> dict:
        # this function tries providers one by one until one works
        failures: list[str] = []

        for provider in self.chain:
            try:
                if provider in {"gemini", "euron"}:
                    model = self.settings.gemini_model if provider == "gemini" else self.settings.euron_model
                    content = await self._call_openrouter(model, system_prompt, user_prompt, max_tokens)
                elif provider == "groq":
                    content = await self._call_groq(system_prompt, user_prompt, max_tokens)
                    model = self.settings.groq_model
                elif provider in {"local", "ollama", "qwen"}:
                    content = await self._call_ollama(system_prompt, user_prompt)
                    model = self.settings.ollama_model
                else:
                    failures.append(f"unknown provider {provider}")
                    continue

                return {
                    "provider": provider,
                    "model": model,
                    "content": content,
                }
            except Exception as exc:
                message = f"{provider} failed: {exc}"
                failures.append(message)
                logger.warning(message)

        raise RuntimeError("all llm providers failed", failures)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
    async def _call_openrouter(self, model: str, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        # this function calls openrouter models such as gemini and euron
        if not self.settings.openrouter_api_key:
            raise RuntimeError("missing openrouter api key")

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.post(
                f"{self.settings.openrouter_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

        if response.status_code >= 400:
            raise RuntimeError(f"openrouter status {response.status_code}: {response.text[:200]}")

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("openrouter returned no choices")

        return (choices[0].get("message", {}).get("content") or "").strip()

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
    async def _call_groq(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        # this function calls groq as a fallback provider
        if not self.settings.groq_api_key:
            raise RuntimeError("missing groq api key")

        payload = {
            "model": self.settings.groq_model,
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.post(
                f"{self.settings.groq_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

        if response.status_code >= 400:
            raise RuntimeError(f"groq status {response.status_code}: {response.text[:200]}")

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("groq returned no choices")

        return (choices[0].get("message", {}).get("content") or "").strip()

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
    async def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        # this function calls local ollama model as final fallback
        payload = {
            "model": self.settings.ollama_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.settings.ollama_base_url}/api/chat", json=payload)

        if response.status_code >= 400:
            raise RuntimeError(f"ollama status {response.status_code}: {response.text[:200]}")

        data = response.json()
        message = data.get("message", {}).get("content", "")
        if not message:
            raise RuntimeError("ollama returned empty content")

        return message.strip()


def parse_json_from_text(content: str) -> Optional[dict]:
    # this function tries to parse json from llm output
    try:
        return json.loads(content)
    except Exception:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except Exception:
                return None
    return None
