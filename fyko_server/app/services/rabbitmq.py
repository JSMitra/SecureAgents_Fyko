"""RabbitMQ publish service using aio-pika."""

import json
import logging
import os

import aio_pika

logger = logging.getLogger(__name__)

RABBITMQ_URL: str = os.environ.get(
    "RABBITMQ_URL",
    "amqp://fyko:fykopass@rabbitmq:5672/",
)

QUEUE_NAME = "ann_requests"

_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None


async def get_channel() -> aio_pika.abc.AbstractChannel:
    """Return (or lazily create) a shared channel."""
    global _connection, _channel
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(RABBITMQ_URL)
    if _channel is None or _channel.is_closed:
        _channel = await _connection.channel()
    return _channel


async def publish_ann_request(
    ulid: str,
    callback_url: str,
    use_complex_model: bool,
) -> None:
    """Publish an ANN generation job to the ann_requests queue."""
    channel = await get_channel()

    # Declare non-durable queue (matches worker declaration).
    queue = await channel.declare_queue(QUEUE_NAME, durable=False)

    payload = json.dumps(
        {
            "ulid": ulid,
            "callback_url": callback_url,
            "use_complex_model": use_complex_model,
        }
    )

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=payload.encode(),
            delivery_mode=aio_pika.DeliveryMode.NOT_PERSISTENT,
            content_type="application/json",
        ),
        routing_key=queue.name,
    )
    logger.info("Published ANN request %s to RabbitMQ", ulid)


async def close_rabbitmq() -> None:
    """Gracefully close the RabbitMQ connection."""
    global _connection
    if _connection and not _connection.is_closed:
        await _connection.close()
