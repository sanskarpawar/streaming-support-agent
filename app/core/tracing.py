"""
Langfuse tracing helpers — compatible with Langfuse v4.

Wraps each agent invocation with a top-level observation and child spans.
If LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are not set, all calls are
no-ops so the app runs without Langfuse configured.

Langfuse v4 API used:
  - langfuse.start_as_current_observation()  — context manager for traces/spans
  - langfuse.start_observation()             — fire-and-forget observation (generation)
  - langfuse.set_current_trace_io()          — set output on the active trace
  - langfuse.flush()                         — flush pending events
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Generator

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
            host=settings.langfuse_base_url,
        )
        logger.info("langfuse_initialised", host=settings.langfuse_base_url)
    except Exception as exc:
        logger.warning("langfuse_init_failed", error=str(exc))
        _langfuse = None
    return _langfuse


class Tracer:
    """
    Thin wrapper around Langfuse v4 observation lifecycle.

    Usage:
        tracer = Tracer(conversation_id, customer_id, user_message)
        with tracer.span("handoff_orchestration", {...}):
            ...
        tracer.finish(final_answer)
    """

    def __init__(self, conversation_id: str, customer_id: int, user_message: str) -> None:
        self._conversation_id = conversation_id
        self._lf = _get_langfuse()
        self._obs_cm: Any = None  # top-level context manager

        if self._lf:
            try:
                self._obs_cm = self._lf.start_as_current_observation(
                    name="agent_turn",
                    as_type="agent",
                    input=user_message,
                    metadata={
                        "conversation_id": conversation_id,
                        "customer_id": customer_id,
                    },
                )
                self._obs_cm.__enter__()
            except Exception as exc:
                logger.warning("langfuse_trace_failed", error=str(exc))
                self._obs_cm = None

    @contextmanager
    def span(self, name: str, metadata: dict | None = None) -> Generator[None, None, None]:
        """Wrap a block with a Langfuse span. No-op if Langfuse is not configured.

        Separation of concerns: Langfuse setup errors are isolated before the
        yield so that body exceptions propagate normally to the caller.
        """
        if not self._lf or not self._obs_cm:
            yield
            return
        # Create the observation context *before* yielding so that if
        # creation fails we fall back cleanly without a second yield.
        try:
            ctx = self._lf.start_as_current_observation(
                name=name,
                as_type="span",
                metadata=metadata or {},
            )
        except Exception as exc:
            logger.warning("langfuse_span_failed", error=str(exc))
            yield
            return
        with ctx:
            yield

    def log_generation(
        self,
        name: str,
        model: str,
        input_text: str,
        output_text: str,
        usage: dict | None = None,
    ) -> None:
        if not self._lf or not self._obs_cm:
            return
        try:
            self._lf.start_observation(
                name=name,
                as_type="generation",
                model=model,
                input=input_text,
                output=output_text,
                usage_details=usage or {},
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
            model=settings.effective_model,
        )
        if not self._lf or not self._obs_cm:
            return
        try:
            self._lf.update_current_span(
                usage_details={
                    "input": prompt_tokens,
                    "output": completion_tokens,
                    "total": total,
                }
            )
        except Exception:
            pass

    def finish(self, output: str) -> None:
        """Set the output on the active trace and flush, then close the top-level observation."""
        if not self._lf or not self._obs_cm:
            return
        try:
            self._lf.set_current_trace_io(output=output)
        except Exception:
            pass
        try:
            self._obs_cm.__exit__(None, None, None)
        except Exception:
            pass
        try:
            self._lf.flush()
        except Exception:
            pass
