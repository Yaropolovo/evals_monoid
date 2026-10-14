"""Inspect AI model provider for Yandex Eliza API.

Eliza is a multi-backend gateway. The endpoint path determines the backend:
    https://api.eliza.yandex.net/<backend>/v1/...

Two protocols are supported:
- **OpenAI-compatible** Chat Completions (openai, openrouter, together,
  deepseek, gemini, ...). Built on ``OpenAICompatibleAPI``.
- **Anthropic native** Messages API (``anthropic`` backend). Built on
  ``AnthropicAPI``.

Model name format:
    eliza/<backend>/<model>

Examples:
    eliza/openai/gpt-4o-mini
    eliza/anthropic/claude-opus-4-1
    eliza/openrouter/anthropic/claude-3.5-sonnet
    eliza/together/meta-llama/Llama-3.1-70B-Instruct
    eliza/deepseek/deepseek-chat

Usage:
    import eliza_provider  # registers the "eliza" provider

    from inspect_ai import eval
    eval(task, model="eliza/openai/gpt-4o-mini")
    eval(task, model="eliza/anthropic/claude-opus-4-1")

Environment:
    SOY_TOKEN: Your Yandex Eliza OAuth token
"""

import json
import os
import warnings
from typing import Any

import httpx
from inspect_ai.model import GenerateConfig, modelapi
from inspect_ai.model._providers.anthropic import AnthropicAPI
from inspect_ai.model._providers.openai_compatible import OpenAICompatibleAPI

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

ELIZA_HOST = "https://api.eliza.yandex.net"

OPENAI_COMPAT_BACKENDS: frozenset[str] = frozenset({
    "openai",
    "openrouter",
    "together",
    "deepseek",
    "gemini",
})

ANTHROPIC_BACKEND = "anthropic"


class ElizaTransport(httpx.AsyncBaseTransport):
    """httpx transport that adapts requests/responses for the Eliza API.

    - Forces ``Authorization: OAuth <token>`` (overwriting any Bearer or x-api-key
      the upstream SDK set).
    - For JSON responses, unwraps the ``{"response": {...}, ...}`` Eliza envelope.
    - For SSE (text/event-stream) responses, passes through unchanged so
      streaming continues to work.
    - Disables SSL verification (Eliza endpoint).
    """

    def __init__(self, oauth_token: str) -> None:
        self._token = oauth_token
        self._inner = httpx.AsyncHTTPTransport(
            verify=False,
            limits=httpx.Limits(
                max_connections=1000,
                max_keepalive_connections=100,
            ),
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # Anthropic SDK sets x-api-key; OpenAI SDK sets Authorization: Bearer.
        # Eliza expects exactly Authorization: OAuth <token>.
        request.headers.pop("x-api-key", None)
        request.headers["authorization"] = f"OAuth {self._token}"

        response = await self._inner.handle_async_request(request)

        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            # Streaming response: pass through unchanged. The Eliza envelope
            # is only applied to non-streaming JSON responses.
            return response

        try:
            body_chunks: list[bytes] = []
            async for chunk in response.stream:
                body_chunks.append(chunk)
            body = b"".join(body_chunks)
        finally:
            await response.aclose()

        try:
            data = json.loads(body)
            if isinstance(data, dict) and "response" in data:
                body = json.dumps(data["response"]).encode()
        except (json.JSONDecodeError, ValueError):
            pass

        return httpx.Response(
            status_code=response.status_code,
            headers=response.headers,
            stream=httpx.ByteStream(body),
            extensions=response.extensions,
        )

    async def aclose(self) -> None:
        await self._inner.aclose()


def _make_http_client(token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=ElizaTransport(token),
        timeout=httpx.Timeout(120.0),
        follow_redirects=True,
    )


def _resolve_token(api_key: str | None) -> str:
    token = api_key or os.environ.get("SOY_TOKEN", "")
    if not token:
        raise RuntimeError(
            "SOY_TOKEN environment variable is not set. "
            "Set it to your Yandex Eliza OAuth token."
        )
    return token


def _parse_eliza_model_name(model_name: str) -> tuple[str, str]:
    """Parse '<backend>/<model>' into (backend, model).

    inspect_ai strips the leading 'eliza/' before passing model_name to the
    provider, so what arrives here is '<backend>/<model>' (e.g. 'openai/gpt-4o-mini').
    """
    parts = model_name.split("/", 1)
    if len(parts) < 2:
        raise ValueError(
            f"Eliza model names must be 'eliza/<backend>/<model>', "
            f"got 'eliza/{model_name}'. "
            f"Example: 'eliza/openai/gpt-4o-mini'. "
            f"Supported backends: anthropic, {', '.join(sorted(OPENAI_COMPAT_BACKENDS))}."
        )
    backend, model = parts

    if (
        backend not in OPENAI_COMPAT_BACKENDS
        and backend != ANTHROPIC_BACKEND
    ):
        warnings.warn(
            f"Eliza backend {backend!r} is not in the known list. "
            f"Assuming OpenAI-compatible protocol at /{backend}/v1/chat/completions.",
            stacklevel=3,
        )

    return backend, model


class _ElizaOpenAICompatAPI(OpenAICompatibleAPI):
    """Internal: Eliza for OpenAI-compatible backends."""

    def __init__(
        self,
        model_name: str,
        base_url: str | None = None,
        api_key: str | None = None,
        config: GenerateConfig = GenerateConfig(),
        **model_args: Any,
    ) -> None:
        backend, _ = _parse_eliza_model_name(model_name)
        self._backend = backend
        token = _resolve_token(api_key)
        self._eliza_token = token

        model_args.pop("http_client", None)
        backend_base_url = base_url or f"{ELIZA_HOST}/{backend}/v1"

        super().__init__(
            model_name=model_name,
            base_url=backend_base_url,
            api_key=token,
            config=config,
            service="eliza",
            service_base_url=backend_base_url,
            http_client=_make_http_client(token),
            **model_args,
        )

    def service_model_name(self) -> str:
        """Strip the backend prefix from the model name.

        inspect_ai has already stripped 'eliza/', so self.model_name is
        '<backend>/<model>'. We want just '<model>' for the API payload.
        """
        return self.model_name.split("/", 1)[-1]

    def initialize(self) -> None:
        if hasattr(self, "http_client") and self.http_client.is_closed:
            self.http_client = _make_http_client(self._eliza_token)
        super().initialize()


class _ElizaAnthropicAPI(AnthropicAPI):
    """Internal: Eliza for the Anthropic native Messages API.

    Hits ``https://api.eliza.yandex.net/anthropic/v1/messages`` and uses the
    standard Anthropic SDK with our custom transport for OAuth auth and
    response envelope unwrapping.
    """

    def __init__(
        self,
        model_name: str,
        base_url: str | None = None,
        api_key: str | None = None,
        config: GenerateConfig = GenerateConfig(),
        **model_args: Any,
    ) -> None:
        token = _resolve_token(api_key)
        self._eliza_token = token

        # Anthropic SDK posts to "/v1/messages" relative to base_url, so we
        # must NOT include "/v1" here. (OpenAI SDK posts to "/chat/completions"
        # and so its base_url DOES need the "/v1" suffix.)
        anthropic_base_url = base_url or f"{ELIZA_HOST}/anthropic"

        # Inject our http_client and force non-streaming (the transport
        # supports SSE pass-through, but to keep the envelope-unwrap path
        # simple we leave Anthropic's streaming heuristics off by default).
        model_args.pop("http_client", None)
        model_args["http_client"] = _make_http_client(token)
        model_args.setdefault("streaming", False)

        super().__init__(
            model_name=model_name,
            base_url=anthropic_base_url,
            api_key=token,
            config=config,
            **model_args,
        )

    def _create_client(self) -> Any:
        """Bypass AnthropicAPI's Bedrock/Vertex/Azure/env-var detection and
        always construct a plain AsyncAnthropic against the Eliza endpoint."""
        from anthropic import AsyncAnthropic

        return AsyncAnthropic(
            base_url=self.base_url,
            api_key=self.api_key,
            **self.model_args,
        )


class ElizaAPI:
    """Dispatcher facade for the 'eliza' provider.

    Routes to the OpenAI-compatible or Anthropic implementation based on the
    backend segment in the model name. ``__new__`` returns an instance of the
    underlying impl class directly; this class itself is never instantiated.
    """

    def __new__(
        cls,
        model_name: str,
        base_url: str | None = None,
        api_key: str | None = None,
        config: GenerateConfig | None = None,
        **model_args: Any,
    ):
        if config is None:
            config = GenerateConfig()
        backend, _ = _parse_eliza_model_name(model_name)
        if backend == ANTHROPIC_BACKEND:
            return _ElizaAnthropicAPI(
                model_name, base_url, api_key, config, **model_args
            )
        return _ElizaOpenAICompatAPI(
            model_name, base_url, api_key, config, **model_args
        )


@modelapi(name="eliza")
def eliza():
    return ElizaAPI
