from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

import ollama
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import SpanKind, StatusCode
from pydantic import ValidationError

from . import telemetry
from .ollama import OllamaAdapter
from .schemas import Chat, Message


def chat_response(content: str) -> ollama.ChatResponse:
    return ollama.ChatResponse(
        model="test-model",
        message=ollama.Message(role="assistant", content=content),
        prompt_eval_count=12,
        eval_count=34,
    )


class OllamaTelemetryTestCase(IsolatedAsyncioTestCase):
    def setUp(self):
        self.exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        tracer_patch = patch.object(telemetry, "tracer", provider.get_tracer(__name__))
        tracer_patch.start()
        self.addCleanup(tracer_patch.stop)

        self.adapter = OllamaAdapter()
        self.adapter._ollama.chat = AsyncMock()
        self.chat = Chat(messages=[Message(kind="user", content="buy milk")])

    async def test_completion_span_has_genai_attributes(self):
        self.adapter._ollama.chat.return_value = chat_response(
            '{"items": [{"text": "milk"}]}'
        )

        await self.adapter.get_completion(self.chat)

        [span] = self.exporter.get_finished_spans()
        self.assertEqual(span.name, f"chat {self.adapter.model}")
        self.assertEqual(span.kind, SpanKind.CLIENT)
        self.assertEqual(
            dict(span.attributes or {}),
            {
                "gen_ai.operation.name": "chat",
                "gen_ai.provider.name": "ollama",
                "gen_ai.request.model": self.adapter.model,
                "gen_ai.request.temperature": 0,
                "gen_ai.response.model": "test-model",
                "gen_ai.usage.input_tokens": 12,
                "gen_ai.usage.output_tokens": 34,
                "pebbenote.llm.task": "note",
            },
        )

    async def test_invalid_answer_marks_span_as_error(self):
        self.adapter._ollama.chat.return_value = chat_response("not json")

        with self.assertRaises(ValidationError), self.assertLogs("pebbenote"):
            await self.adapter.get_completion(self.chat)

        [span] = self.exporter.get_finished_spans()
        self.assertEqual(span.status.status_code, StatusCode.ERROR)
        self.assertEqual(span.attributes["error.type"], "ValidationError")

    async def test_failing_classifier_still_records_the_error(self):
        self.adapter._ollama.systemone = AsyncMock(side_effect=ConnectionError())

        with self.assertLogs("pebbenote"):
            kind = await self.adapter.classify_input("buy milk")

        self.assertEqual(kind, "note")
        [span] = self.exporter.get_finished_spans()
        self.assertEqual(span.attributes["pebbenote.llm.task"], "classify")
        self.assertEqual(span.attributes["error.type"], "ConnectionError")
