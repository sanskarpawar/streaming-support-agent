"""
Langfuse tracing helpers.

Wraps each agent invocation and tool call with Langfuse spans.
If LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are not set, all calls
are no-ops so the app runs without Langfuse configured.
"""
from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Generator

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_langfuse: Any = None


def _get_langfuse() -> Any:
    global _langfuse
    if _langfuse is not None:
        return _langfuse
    settings = get_settings()
    if not settings.langfuse_enabled:
        return None
    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        logger.info("langfuse_initialised", host=settings.langfuse_host)
    except Exception as exc:
        logger.warning("langfuse_init_failed", error=str(exc))
        _langfuse = None
    return _langfuse


class Tracer:
    """Thin wrapper around Langfuse trace + span lifecycle."""

    def __init__(self, conversation_id: str, customer_id: int, user_message: str) -> None:
        self._conversation_id = conversation_id
        self._lf = _get_langfuse()
        self._trace: Any = None
        if self._lf:
            try:
                self._trace = self._lf.trace(
                    name="agent_turn",
                    id=f"{conversation_id}-{int(time.time())}",
                    user_id=str(customer_id),
                    input=user_message,
                    metadata={"conversation_id": conversation_id},
                )
            except Exception as exc:
                logger.warning("langfuse_trace_failed", error=str(exc))
                self._trace = None

    @contextmanager
    def span(self, name: str, metadata: dict | None = None) -> Generator[None, None, None]:
        if not self._trace:
            yield
            return
        span = None
        start = time.perf_counter()
        try:
            span = self._trace.span(name=name, metadata=metadata or {})
            yield
        finally:
            latency = round((time.perf_counter() - start) * 1000, 2)
            if span:
                try:
                    span.end(metadata={"latency_ms": latency})
                except Exception:
                    pass

    def log_generation(
        self,
        name: str,
        model: str,
        input_text: str,
        output_text: str,
        usage: dict | None = None,
    ) -> None:
        if not self._trace:
            return
        try:
            self._trace.generation(
                name=name,
                model=model,
                input=input_text,
                output=output_text,
                usage=usage or {},
            )
        except Exception as exc:
            logger.warning("langfuse_generation_failed", error=str(exc))

    def log_token_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        total = prompt_tokens + completion_tokens
        settings = get_settings()
        logger.info(
            "token_usage",
            conversation_id=self._conversation_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            model=settings.openai_model,
        )
        if not self._trace:
            return
        try:
            self._trace.update(
                usage={"input": prompt_tokens, "output": completion_tokens, "total": total}
            )
        except Exception:
            pass

    def finish(self, output: str) -> None:
        if not self._trace:
            return
        try:
            self._trace.update(output=output)
            self._lf.flush()
        except Exception:
            pass
