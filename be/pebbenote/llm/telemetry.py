"""
Spans and metrics of LLM calls, following the OpenTelemetry GenAI semantic
conventions. Prompts and answers aren't recorded, they hold the user's notes.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Literal

from opentelemetry import metrics, trace
from opentelemetry.trace import Span, SpanKind
from opentelemetry.util.types import AttributeValue

type LlmTask = Literal["note", "classify", "rewrite_instruction", "title"]

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

token_usage = meter.create_histogram(
    "gen_ai.client.token.usage",
    unit="{token}",
    description="Number of input and output tokens used",
)
operation_duration = meter.create_histogram(
    "gen_ai.client.operation.duration",
    unit="s",
    description="GenAI operation duration",
)


class LlmCall:
    def __init__(self, span: Span, attributes: dict[str, AttributeValue]) -> None:
        self.span = span
        self.attributes = attributes

    def record_response(
        self, model: str | None, input_tokens: int | None, output_tokens: int | None
    ) -> None:
        if model:
            self.attributes["gen_ai.response.model"] = model
            self.span.set_attribute("gen_ai.response.model", model)
        for token_type, count in (("input", input_tokens), ("output", output_tokens)):
            if count is None:
                continue
            self.span.set_attribute(f"gen_ai.usage.{token_type}_tokens", count)
            token_usage.record(
                count, {**self.attributes, "gen_ai.token.type": token_type}
            )


@contextmanager
def llm_call(
    model: str, task: LlmTask, temperature: float | None = None
) -> Iterator[LlmCall]:
    """A span and the duration metric around one call to the model"""
    attributes: dict[str, AttributeValue] = {
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": "ollama",
        "gen_ai.request.model": model,
        "pebbenote.llm.task": task,
    }
    span_attributes = dict(attributes)
    if temperature is not None:
        span_attributes["gen_ai.request.temperature"] = temperature
    start = perf_counter()
    with tracer.start_as_current_span(
        f"chat {model}", kind=SpanKind.CLIENT, attributes=span_attributes
    ) as span:
        call = LlmCall(span, attributes)
        try:
            yield call
        except Exception as e:
            attributes["error.type"] = type(e).__qualname__
            span.set_attribute("error.type", attributes["error.type"])
            raise
        finally:
            operation_duration.record(perf_counter() - start, attributes)
