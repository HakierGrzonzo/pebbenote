"""
OpenTelemetry setup, shared by the API and the worker.

Telemetry is off unless OTEL_EXPORTER_OTLP_ENDPOINT is set. Everything else
comes from the standard OTEL_* variables: OTEL_SERVICE_NAME names the process,
OTEL_{TRACES,METRICS,LOGS}_EXPORTER=none turns off one signal.

FastAPI and the taskiq OpenTelemetryMiddleware use the global providers, so
setting them here is enough to instrument requests and tasks.
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
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_configured = False


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
        tracer_provider = TracerProvider(resource=resource)
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
        # Existing loggers get exported too, with the ids of the current span
        logging.getLogger().addHandler(LoggingHandler(logger_provider=logger_provider))
