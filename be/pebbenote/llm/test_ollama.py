from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

import ollama
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import SpanKind, StatusCode

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
        self.adapter._ollama.chat.return_value = chat_response("- milk")

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
                "gen_ai.request.temperature": self.adapter.temperature,
                "gen_ai.response.model": "test-model",
                "gen_ai.usage.input_tokens": 12,
                "gen_ai.usage.output_tokens": 34,
                "pebbenote.llm.task": "note",
            },
        )

    async def test_completion_uses_configured_temperature(self):
        self.adapter.temperature = 0.7
        self.adapter._ollama.chat.return_value = chat_response("- milk")

        await self.adapter.get_completion(self.chat)

        options = self.adapter._ollama.chat.call_args.kwargs["options"]
        self.assertEqual(options["temperature"], 0.7)
        [span] = self.exporter.get_finished_spans()
        self.assertEqual(span.attributes["gen_ai.request.temperature"], 0.7)

    async def test_completion_drops_a_code_block(self):
        self.adapter._ollama.chat.return_value = chat_response(
            "```markdown\n- milk\n    - oat\n```"
        )

        note = await self.adapter.get_completion(self.chat)

        self.assertEqual(note, "- milk\n    - oat")

    async def test_failed_chat_marks_span_as_error(self):
        self.adapter._ollama.chat.side_effect = ConnectionError()

        with self.assertRaises(ConnectionError):
            await self.adapter.get_completion(self.chat)

        [span] = self.exporter.get_finished_spans()
        self.assertEqual(span.status.status_code, StatusCode.ERROR)
        self.assertEqual(span.attributes["error.type"], "ConnectionError")

    async def test_failing_classifier_still_records_the_error(self):
        self.adapter._ollama.systemone = AsyncMock(side_effect=ConnectionError())

        with self.assertLogs("pebbenote"):
            classification = await self.adapter.classify_input("buy milk")

        self.assertEqual(classification.kind, "note")
        self.assertTrue(classification.needs_history)
        [span] = self.exporter.get_finished_spans()
        self.assertEqual(span.attributes["pebbenote.llm.task"], "classify")
        self.assertEqual(span.attributes["error.type"], "ConnectionError")

    async def test_classifier_answers_kind_and_history(self):
        def choice(value: str) -> ollama.SystemOneChoiceAnswer:
            return ollama.SystemOneChoiceAnswer(
                type="choice", choice=value, probabilities={}, confidence=1
            )

        self.adapter._ollama.systemone = AsyncMock(
            return_value=ollama.SystemOneResponse(
                model="test-model",
                answers={"kind": choice("note"), "history": choice("history")},
                usage=ollama.SystemOneUsage(input_tokens=5, output_tokens=1),
            )
        )

        classification = await self.adapter.classify_input("undo that")

        self.assertEqual(classification.kind, "note")
        self.assertTrue(classification.needs_history)
        questions = self.adapter._ollama.systemone.call_args.kwargs["questions"]
        self.assertEqual(set(questions), {"kind", "history"})

    async def test_rewritten_instruction_starts_with_a_capital(self):
        self.adapter._ollama.chat.return_value = chat_response(
            "i should never use capital letters."
        )

        instruction = await self.adapter.rewrite_instruction("no capitals")

        self.assertEqual(instruction, "I should never use capital letters.")
