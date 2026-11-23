"""
OpenTelemetry setup, shared by the API and the worker.

Telemetry is off unless OTEL_EXPORTER_OTLP_ENDPOINT is set. Everything else
comes from the standard OTEL_* variables: OTEL_SERVICE_NAME names the process,
OTEL_{TRACES,METRICS,LOGS}_EXPORTER=none turns off one signal.

FastAPI and the taskiq OpenTelemetryMiddleware use the global providers, so
setting them here is enough to instrument requests and tasks. Queries,
Redis (the broker) and httpx (the Ollama client) are instrumented here.
"""

import logging
import os

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import (
    Decision,
    ParentBased,
    Sampler,
    SamplingResult,
)
from opentelemetry.trace import SpanKind

_configured = False


class SkipBackgroundCalls(Sampler):
    """
    Drops traces that start with a client call. Outside a request or a task
    those are background noise, like the worker polling Redis for tasks.
    """

    def should_sample(
        self,
        parent_context,
        trace_id,
        name,
        kind=None,
        attributes=None,
        links=None,
        trace_state=None,
    ):
        if kind == SpanKind.CLIENT:
            return SamplingResult(Decision.DROP)
        return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes)

    def get_description(self) -> str:
        return "SkipBackgroundCalls"


def telemetry_enabled() -> bool:
    return bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")) and (
        os.getenv("OTEL_SDK_DISABLED", "").lower() != "true"
    )


def _signal_enabled(signal: str) -> bool:
    return os.getenv(f"OTEL_{signal}_EXPORTER", "otlp").strip().lower() != "none"


def setup_telemetry() -> None:
    """Sets the global providers, once per process"""
    global _configured
    if _configured or not telemetry_enabled():
        return
    _configured = True

    resource = Resource.create()

    if _signal_enabled("TRACES"):
        tracer_provider = TracerProvider(
            resource=resource, sampler=ParentBased(root=SkipBackgroundCalls())
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(tracer_provider)

    if _signal_enabled("METRICS"):
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())],
        )
        metrics.set_meter_provider(meter_provider)

    if _signal_enabled("LOGS"):
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter())
        )
        set_logger_provider(logger_provider)
        # Existing loggers get exported too, with the ids of the current span.
        # Root gets the app's loggers; uvicorn's own don't propagate to it.
        handler = LoggingHandler(logger_provider=logger_provider)
        for name in ("", "uvicorn", "uvicorn.access"):
            logging.getLogger(name).addHandler(handler)

    # On the driver, the SQLAlchemy instrumentation doesn't support 2.1 yet
    AsyncPGInstrumentor().instrument()
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
