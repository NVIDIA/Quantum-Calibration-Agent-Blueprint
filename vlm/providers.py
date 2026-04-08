# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""VLM provider abstraction supporting NVIDIA and custom OpenAI-compatible endpoints."""

import os
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

logger = logging.getLogger(__name__)


class VLMProvider(ABC):
    """Abstract base class for VLM providers."""

    @abstractmethod
    async def analyze_images(
        self,
        prompt: str,
        images_base64: List[str],
        image_format: str = "png",
    ) -> str:
        """Analyze images with the VLM.

        Args:
            prompt: Analysis instructions
            images_base64: List of base64-encoded images
            image_format: Image format (png, jpeg)

        Returns:
            Analysis text from the VLM
        """
        pass


class NVIDIAProvider(VLMProvider):
    """VLM provider using official langchain-nvidia-ai-endpoints."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        api_key_env: Optional[str] = None,
        temperature: float = 0,
        max_tokens: int = 8192,
    ):
        """Initialize NVIDIA provider.

        Args:
            model: NVIDIA model name (e.g., "google/gemma-4-31b-it")
            api_key: API key (optional, can use api_key_env instead)
            api_key_env: Environment variable name for API key
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self.model = model
        self.api_key = api_key or os.environ.get(api_key_env or "", "")
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def analyze_images(
        self,
        prompt: str,
        images_base64: List[str],
        image_format: str = "png",
    ) -> str:
        """Analyze images using NVIDIA endpoint."""
        try:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            from langchain_core.messages import HumanMessage
        except ImportError as e:
            raise RuntimeError(
                "langchain-nvidia-ai-endpoints is required. Install with: pip install langchain-nvidia-ai-endpoints"
            ) from e

        # Build message content with images
        content = [{"type": "text", "text": prompt}]
        for img_b64 in images_base64:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{image_format};base64,{img_b64}"
                    },
                }
            )

        try:
            chat = ChatNVIDIA(
                model=self.model,
                api_key=self.api_key if self.api_key else None,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            message = HumanMessage(content=content)
            response = await chat.ainvoke([message])
            return response.content
        except Exception as e:
            logger.error(f"NVIDIA VLM call failed: {e}")
            raise RuntimeError(f"VLM analysis failed: {e}") from e


class AnthropicProvider(VLMProvider):
    """VLM provider using Anthropic Claude models."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        api_key_env: Optional[str] = None,
        temperature: float = 0,
        max_tokens: int = 4096,
    ):
        """Initialize Anthropic provider.

        Args:
            model: Claude model name (e.g., "claude-sonnet-4-6")
            api_key: API key (optional, can use api_key_env instead)
            api_key_env: Environment variable name for API key
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self.model = model
        self.api_key = api_key or os.environ.get(api_key_env or "", "")
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def analyze_images(
        self,
        prompt: str,
        images_base64: List[str],
        image_format: str = "png",
    ) -> str:
        """Analyze images using Anthropic Claude."""
        try:
            from langchain_anthropic import ChatAnthropic
            from langchain_core.messages import HumanMessage
        except ImportError as e:
            raise RuntimeError(
                "langchain-anthropic is required. Install with: pip install langchain-anthropic"
            ) from e

        # Build message content with images
        content = []
        for img_b64 in images_base64:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": f"image/{image_format}",
                        "data": img_b64,
                    },
                }
            )
        content.append({"type": "text", "text": prompt})

        try:
            chat = ChatAnthropic(
                model=self.model,
                api_key=self.api_key if self.api_key else None,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            message = HumanMessage(content=content)
            response = await chat.ainvoke([message])
            return response.content
        except Exception as e:
            logger.error(f"Anthropic VLM call failed: {e}")
            raise RuntimeError(f"VLM analysis failed: {e}") from e


class CustomEndpointProvider(VLMProvider):
    """VLM provider for custom OpenAI-compatible endpoints."""

    def __init__(
        self,
        endpoint: str,
        model: str,
        api_key: Optional[str] = None,
        api_key_env: Optional[str] = None,
        temperature: float = 0,
        max_tokens: int = 8192,
    ):
        """Initialize custom endpoint provider.

        Args:
            endpoint: API endpoint URL
            model: Model name
            api_key: API key (optional)
            api_key_env: Environment variable name for API key
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key or os.environ.get(api_key_env or "", "")
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def analyze_images(
        self,
        prompt: str,
        images_base64: List[str],
        image_format: str = "png",
    ) -> str:
        """Analyze images using custom endpoint."""
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError(
                "httpx is required for custom endpoints. Install with: pip install httpx"
            ) from e

        # Build message content
        content = [{"type": "text", "text": prompt}]
        for img_b64 in images_base64:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{image_format};base64,{img_b64}"},
                }
            )

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": content}],
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                    },
                    timeout=120.0,
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Custom endpoint call failed: {e}")
            raise RuntimeError(f"VLM analysis failed: {e}") from e


def get_vlm_client(config: dict) -> VLMProvider:
    """Create VLM client from configuration.

    Args:
        config: VLM configuration dict with keys:
            - provider: "nvidia", "anthropic", or "custom"
            - model: Model name/string
            - api_key or api_key_env: API key configuration
            - endpoint: (for custom) API endpoint URL
            - temperature: Sampling temperature
            - max_tokens: Max response tokens

    Returns:
        VLMProvider instance
    """
    provider = config.get("provider", "nvidia")

    if provider in ("nvidia", "litellm"):  # litellm for backwards compat
        return NVIDIAProvider(
            model=config.get("model", "google/gemma-4-31b-it"),
            api_key=config.get("api_key"),
            api_key_env=config.get("api_key_env"),
            temperature=config.get("temperature", 0),
            max_tokens=config.get("max_tokens", 4096),
        )
    elif provider == "anthropic":
        return AnthropicProvider(
            model=config.get("model", "claude-sonnet-4-6"),
            api_key=config.get("api_key"),
            api_key_env=config.get("api_key_env"),
            temperature=config.get("temperature", 0),
            max_tokens=config.get("max_tokens", 4096),
        )
    elif provider == "custom":
        return CustomEndpointProvider(
            endpoint=config["endpoint"],
            model=config.get("model", ""),
            api_key=config.get("api_key"),
            api_key_env=config.get("api_key_env"),
            temperature=config.get("temperature", 0),
            max_tokens=config.get("max_tokens", 4096),
        )
    else:
        raise ValueError(f"Unknown VLM provider: {provider}")
