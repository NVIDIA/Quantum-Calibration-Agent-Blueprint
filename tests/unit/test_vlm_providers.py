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

"""Tests for vlm.providers module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from vlm.providers import (
    get_vlm_client,
    NVIDIAProvider,
    AnthropicProvider,
    CustomEndpointProvider,
)


# ---------------------------------------------------------------------------
# get_vlm_client: correct provider type
# ---------------------------------------------------------------------------


class TestGetVlmClientProviderTypes:
    def test_nvidia_provider(self):
        client = get_vlm_client({"provider": "nvidia", "model": "some-model"})
        assert isinstance(client, NVIDIAProvider)

    def test_litellm_returns_nvidia_provider(self):
        client = get_vlm_client({"provider": "litellm", "model": "some-model"})
        assert isinstance(client, NVIDIAProvider)

    def test_anthropic_provider(self):
        client = get_vlm_client({"provider": "anthropic", "model": "claude-sonnet-4-6"})
        assert isinstance(client, AnthropicProvider)

    def test_custom_provider(self):
        client = get_vlm_client(
            {"provider": "custom", "endpoint": "http://localhost:8000/v1/chat/completions", "model": "m"}
        )
        assert isinstance(client, CustomEndpointProvider)

    def test_default_provider_is_nvidia(self):
        client = get_vlm_client({})
        assert isinstance(client, NVIDIAProvider)


# ---------------------------------------------------------------------------
# get_vlm_client: unknown provider raises ValueError
# ---------------------------------------------------------------------------


class TestGetVlmClientUnknownProvider:
    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown VLM provider: bogus"):
            get_vlm_client({"provider": "bogus"})


# ---------------------------------------------------------------------------
# get_vlm_client: config values passed correctly
# ---------------------------------------------------------------------------


class TestGetVlmClientConfigPassthrough:
    def test_nvidia_config_values(self):
        cfg = {
            "provider": "nvidia",
            "model": "my-model",
            "api_key": "key123",
            "temperature": 0.5,
            "max_tokens": 2048,
        }
        client = get_vlm_client(cfg)
        assert client.model == "my-model"
        assert client.api_key == "key123"
        assert client.temperature == 0.5
        assert client.max_tokens == 2048

    def test_anthropic_config_values(self):
        cfg = {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "api_key": "sk-ant-xxx",
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        client = get_vlm_client(cfg)
        assert client.model == "claude-sonnet-4-6"
        assert client.api_key == "sk-ant-xxx"
        assert client.temperature == 0.7
        assert client.max_tokens == 1024

    def test_custom_config_values(self):
        cfg = {
            "provider": "custom",
            "endpoint": "http://localhost:8000/v1/chat/completions",
            "model": "custom-model",
            "api_key": "tok",
            "temperature": 0.3,
            "max_tokens": 512,
        }
        client = get_vlm_client(cfg)
        assert client.endpoint == "http://localhost:8000/v1/chat/completions"
        assert client.model == "custom-model"
        assert client.api_key == "tok"
        assert client.temperature == 0.3
        assert client.max_tokens == 512


# ---------------------------------------------------------------------------
# get_vlm_client: api_key_env reads from environment
# ---------------------------------------------------------------------------


class TestGetVlmClientApiKeyEnv:
    def test_nvidia_api_key_env(self, monkeypatch):
        monkeypatch.setenv("MY_NVIDIA_KEY", "env-key-nvidia")
        client = get_vlm_client({"provider": "nvidia", "api_key_env": "MY_NVIDIA_KEY"})
        assert client.api_key == "env-key-nvidia"

    def test_anthropic_api_key_env(self, monkeypatch):
        monkeypatch.setenv("MY_ANTHROPIC_KEY", "env-key-anthropic")
        client = get_vlm_client({"provider": "anthropic", "api_key_env": "MY_ANTHROPIC_KEY"})
        assert client.api_key == "env-key-anthropic"

    def test_custom_api_key_env(self, monkeypatch):
        monkeypatch.setenv("MY_CUSTOM_KEY", "env-key-custom")
        client = get_vlm_client({
            "provider": "custom",
            "endpoint": "http://localhost:8000",
            "api_key_env": "MY_CUSTOM_KEY",
        })
        assert client.api_key == "env-key-custom"

    def test_api_key_takes_precedence_over_env(self, monkeypatch):
        monkeypatch.setenv("MY_KEY", "from-env")
        client = get_vlm_client({
            "provider": "nvidia",
            "api_key": "explicit-key",
            "api_key_env": "MY_KEY",
        })
        assert client.api_key == "explicit-key"


# ---------------------------------------------------------------------------
# NVIDIAProvider.analyze_images
# ---------------------------------------------------------------------------


class TestNVIDIAProviderAnalyzeImages:
    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        provider = NVIDIAProvider(model="test-model", api_key="key")

        mock_response = MagicMock()
        mock_response.content = "Analysis result from NVIDIA"

        mock_chat_cls = MagicMock()
        mock_chat_instance = MagicMock()
        mock_chat_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat_instance

        mock_human_msg = MagicMock()

        with patch.dict("sys.modules", {
            "langchain_nvidia_ai_endpoints": MagicMock(ChatNVIDIA=mock_chat_cls),
            "langchain_core": MagicMock(),
            "langchain_core.messages": MagicMock(HumanMessage=mock_human_msg),
        }):
            result = await provider.analyze_images("Describe", ["abc123"], "png")

        assert result == "Analysis result from NVIDIA"
        mock_chat_instance.ainvoke.assert_awaited_once()

        # Verify HumanMessage was called with content containing image_url
        call_args = mock_human_msg.call_args
        content = call_args[1].get("content") if call_args[1] else call_args[0][0]
        assert any(
            item.get("type") == "image_url"
            and "base64,abc123" in item["image_url"]["url"]
            for item in content
            if isinstance(item, dict) and "image_url" in item
        )

    @pytest.mark.asyncio
    async def test_raises_runtime_error_on_failure(self):
        provider = NVIDIAProvider(model="test-model", api_key="key")

        mock_chat_cls = MagicMock()
        mock_chat_instance = MagicMock()
        mock_chat_instance.ainvoke = AsyncMock(side_effect=Exception("API down"))
        mock_chat_cls.return_value = mock_chat_instance

        with patch.dict("sys.modules", {
            "langchain_nvidia_ai_endpoints": MagicMock(ChatNVIDIA=mock_chat_cls),
            "langchain_core": MagicMock(),
            "langchain_core.messages": MagicMock(HumanMessage=MagicMock()),
        }):
            with pytest.raises(RuntimeError, match="VLM analysis failed"):
                await provider.analyze_images("Describe", ["img"], "png")


# ---------------------------------------------------------------------------
# AnthropicProvider.analyze_images
# ---------------------------------------------------------------------------


class TestAnthropicProviderAnalyzeImages:
    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        provider = AnthropicProvider(model="claude-sonnet-4-6", api_key="key")

        mock_response = MagicMock()
        mock_response.content = "Analysis result from Anthropic"

        mock_chat_cls = MagicMock()
        mock_chat_instance = MagicMock()
        mock_chat_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat_instance

        mock_human_msg = MagicMock()

        with patch.dict("sys.modules", {
            "langchain_anthropic": MagicMock(ChatAnthropic=mock_chat_cls),
            "langchain_core": MagicMock(),
            "langchain_core.messages": MagicMock(HumanMessage=mock_human_msg),
        }):
            result = await provider.analyze_images("Describe", ["imgdata"], "jpeg")

        assert result == "Analysis result from Anthropic"
        mock_chat_instance.ainvoke.assert_awaited_once()

        # Verify HumanMessage was called with content containing base64 image source
        call_args = mock_human_msg.call_args
        content = call_args[1].get("content") if call_args[1] else call_args[0][0]
        assert any(
            item.get("type") == "image"
            and item["source"]["type"] == "base64"
            and item["source"]["data"] == "imgdata"
            and item["source"]["media_type"] == "image/jpeg"
            for item in content
            if isinstance(item, dict) and item.get("type") == "image"
        )

    @pytest.mark.asyncio
    async def test_raises_runtime_error_on_failure(self):
        provider = AnthropicProvider(model="claude-sonnet-4-6", api_key="key")

        mock_chat_cls = MagicMock()
        mock_chat_instance = MagicMock()
        mock_chat_instance.ainvoke = AsyncMock(side_effect=Exception("Anthropic error"))
        mock_chat_cls.return_value = mock_chat_instance

        with patch.dict("sys.modules", {
            "langchain_anthropic": MagicMock(ChatAnthropic=mock_chat_cls),
            "langchain_core": MagicMock(),
            "langchain_core.messages": MagicMock(HumanMessage=MagicMock()),
        }):
            with pytest.raises(RuntimeError, match="VLM analysis failed"):
                await provider.analyze_images("Describe", ["img"], "png")


# ---------------------------------------------------------------------------
# CustomEndpointProvider.analyze_images
# ---------------------------------------------------------------------------


class TestCustomEndpointProviderAnalyzeImages:
    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        provider = CustomEndpointProvider(
            endpoint="http://localhost:8000/v1/chat/completions",
            model="custom-model",
            api_key="tok",
        )

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Custom result"}}]
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch.dict("sys.modules", {"httpx": MagicMock()}):
            import sys
            httpx_mock = sys.modules["httpx"]
            httpx_mock.AsyncClient.return_value = mock_client

            result = await provider.analyze_images("Describe", ["b64img"], "png")

        assert result == "Custom result"
        mock_client.post.assert_awaited_once()

        # Verify the POST body structure
        call_kwargs = mock_client.post.call_args
        json_body = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert json_body["model"] == "custom-model"
        assert json_body["messages"][0]["role"] == "user"
        assert any(
            c.get("type") == "image_url" and "base64,b64img" in c["image_url"]["url"]
            for c in json_body["messages"][0]["content"]
            if isinstance(c, dict) and c.get("type") == "image_url"
        )

    @pytest.mark.asyncio
    async def test_raises_runtime_error_on_failure(self):
        provider = CustomEndpointProvider(
            endpoint="http://localhost:8000/v1/chat/completions",
            model="custom-model",
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))

        with patch.dict("sys.modules", {"httpx": MagicMock()}):
            import sys
            httpx_mock = sys.modules["httpx"]
            httpx_mock.AsyncClient.return_value = mock_client

            with pytest.raises(RuntimeError, match="VLM analysis failed"):
                await provider.analyze_images("Describe", ["img"], "png")

    @pytest.mark.asyncio
    async def test_authorization_header_set(self):
        provider = CustomEndpointProvider(
            endpoint="http://localhost:8000/v1/chat/completions",
            model="m",
            api_key="secret",
        )

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch.dict("sys.modules", {"httpx": MagicMock()}):
            import sys
            sys.modules["httpx"].AsyncClient.return_value = mock_client

            await provider.analyze_images("Describe", ["img"], "png")

        call_kwargs = mock_client.post.call_args
        headers = call_kwargs[1].get("headers", call_kwargs.kwargs.get("headers", {}))
        assert headers.get("Authorization") == "Bearer secret"


# ---------------------------------------------------------------------------
# Import errors for missing packages
# ---------------------------------------------------------------------------


class TestImportErrors:
    @pytest.mark.asyncio
    async def test_nvidia_missing_langchain_nvidia(self):
        provider = NVIDIAProvider(model="m", api_key="k")

        with patch.dict("sys.modules", {"langchain_nvidia_ai_endpoints": None}):
            with pytest.raises(RuntimeError, match="langchain-nvidia-ai-endpoints is required"):
                await provider.analyze_images("prompt", ["img"])

    @pytest.mark.asyncio
    async def test_anthropic_missing_langchain_anthropic(self):
        provider = AnthropicProvider(model="m", api_key="k")

        with patch.dict("sys.modules", {"langchain_anthropic": None}):
            with pytest.raises(RuntimeError, match="langchain-anthropic is required"):
                await provider.analyze_images("prompt", ["img"])

    @pytest.mark.asyncio
    async def test_custom_missing_httpx(self):
        provider = CustomEndpointProvider(endpoint="http://x", model="m")

        with patch.dict("sys.modules", {"httpx": None}):
            with pytest.raises(RuntimeError, match="httpx is required"):
                await provider.analyze_images("prompt", ["img"])
