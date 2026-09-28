import time
from dataclasses import dataclass, field
from typing import Any, Callable

from anthropic import Anthropic, APIConnectionError, InternalServerError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LoopResult:
    final_output: dict[str, Any]
    steps: int
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


class LLMClient:
    def __init__(self):
        self.settings = get_settings()
        self._client: Anthropic | None = None

    @property
    def client(self) -> Anthropic:
        if self._client is None:
            self._client = Anthropic(api_key=self.settings.ANTHROPIC_API_KEY or "dummy_key")
        return self._client

    @retry(
        retry=retry_if_exception_type((RateLimitError, InternalServerError, APIConnectionError)),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
    )
    def call_with_retry(self, **kwargs: Any) -> Any:
        return self.client.messages.create(**kwargs)

    def extract_structured(
        self,
        system: str,
        user: str,
        tool_schema: dict[str, Any],
        model: str | None = None,
    ) -> dict[str, Any]:
        """Forces a tool call to extract structured JSON matching tool_schema."""
        m = model or self.settings.LLM_MODEL_FAST
        tool_name = tool_schema["name"]

        start_time = time.time()
        response = self.call_with_retry(
            model=m,
            max_tokens=self.settings.LLM_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[tool_schema],
            tool_choice={"type": "tool", "name": tool_name},
        )
        latency = int((time.time() - start_time) * 1000)

        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens
        logger.info(
            "llm_extract_completed",
            model=m,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency,
        )

        for content_block in response.content:
            if getattr(content_block, "type", "") == "tool_use" and content_block.name == tool_name:
                return content_block.input

        raise RuntimeError(f"Model did not return tool call for '{tool_name}'")

    def run_tool_loop(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        dispatch: Callable[[str, dict[str, Any]], str],
        max_steps: int | None = None,
        model: str | None = None,
    ) -> LoopResult:
        """Executes a multi-turn tool interaction loop until submit_analysis is called or max_steps reached."""
        m = model or self.settings.LLM_MODEL
        steps_limit = max_steps or self.settings.AGENT_MAX_STEPS
        current_messages = list(messages)

        total_tokens_in = 0
        total_tokens_out = 0
        tool_history: list[dict[str, Any]] = []
        start_time = time.time()

        for step in range(1, steps_limit + 1):
            response = self.call_with_retry(
                model=m,
                max_tokens=self.settings.LLM_MAX_TOKENS,
                system=system,
                messages=current_messages,
                tools=tools,
            )

            total_tokens_in += response.usage.input_tokens
            total_tokens_out += response.usage.output_tokens

            # Append assistant message
            current_messages.append({"role": "assistant", "content": response.content})

            # Check for tool uses
            tool_uses = [b for b in response.content if getattr(b, "type", "") == "tool_use"]

            if not tool_uses:
                # No tool call; return empty/raw analysis
                break

            tool_results_content = []
            for t_use in tool_uses:
                t_name = t_use.name
                t_input = t_use.input
                tool_history.append({"name": t_name, "input": t_input})

                if t_name == "submit_analysis":
                    # Loop terminates with submission
                    latency = int((time.time() - start_time) * 1000)
                    return LoopResult(
                        final_output=t_input,
                        steps=step,
                        tokens_in=total_tokens_in,
                        tokens_out=total_tokens_out,
                        latency_ms=latency,
                        tool_calls=tool_history,
                    )

                # Dispatch tool
                try:
                    result_str = dispatch(t_name, t_input)
                except Exception as e:
                    result_str = f"Error executing tool {t_name}: {e}"

                # Enforce max chars truncation
                if len(result_str) > self.settings.TOOL_OUTPUT_MAX_CHARS:
                    result_str = result_str[: self.settings.TOOL_OUTPUT_MAX_CHARS] + "\n[truncated]"

                tool_results_content.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": t_use.id,
                        "content": result_str,
                    }
                )

            current_messages.append({"role": "user", "content": tool_results_content})

        latency = int((time.time() - start_time) * 1000)
        return LoopResult(
            final_output={},
            steps=steps_limit,
            tokens_in=total_tokens_in,
            tokens_out=total_tokens_out,
            latency_ms=latency,
            tool_calls=tool_history,
        )


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
