import asyncio

from taskiq import SmartRetryMiddleware, TaskiqMessage, TaskiqMiddleware
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from .config import settings


class DelayMiddleware(TaskiqMiddleware):
    """
    Honors the "delay" label SmartRetryMiddleware puts on retries.

    The Redis broker delivers messages right away, so without this every
    retry would run immediately.
    """

    async def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        if delay := message.labels.get("delay"):
            await asyncio.sleep(float(delay))
        return message


broker = (
    # Streams need an ack, so tasks of a crashed worker are picked up again
    # once they've been idle for idle_timeout ms
    RedisStreamBroker(settings.REDIS_URL, idle_timeout=5 * 60 * 1000)
    .with_result_backend(
        # Results only matter while the API request waits for them
        RedisAsyncResultBackend(settings.REDIS_URL, result_ex_time=600)
    )
    .with_middlewares(
        DelayMiddleware(),
        SmartRetryMiddleware(
            default_retry_count=settings.ACTION_MAX_RETRIES,
            use_jitter=True,
            use_delay_exponent=True,
        ),
    )
)
