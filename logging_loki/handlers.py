# -*- coding: utf-8 -*-

import logging
from logging.handlers import MemoryHandler, QueueHandler
from logging.handlers import QueueListener
import os
from queue import Queue
import time
from typing import Optional, Union

from logging_loki.emitter import BasicAuth, LokiEmitter

LOKI_MAX_BATCH_BUFFER_SIZE = int(os.environ.get('LOKI_MAX_BATCH_BUFFER_SIZE', 10))

class LokiQueueHandler(QueueHandler):
    """This handler automatically creates listener and `LokiHandler` to handle logs queue."""

    handler: Union['LokiBatchHandler', 'LokiHandler']

    def __init__(self, queue: Queue, batch_interval: Optional[float] = None, **kwargs):
        """Create new logger handler with the specified queue and kwargs for the `LokiHandler`."""
        super().__init__(queue)

        loki_handler = LokiHandler(**kwargs)  # noqa: WPS110

        if batch_interval:
            self.handler = LokiBatchHandler(batch_interval, target=loki_handler)
        else: 
            self.handler = loki_handler

        self.listener = QueueListener(self.queue, self.handler)
        self.listener.start()

    def flush(self) -> None:
        super().flush()
        self.handler.flush()

    def __del__(self):
        self.listener.stop()

class LokiHandler(logging.Handler):
    """
    Log handler that sends log records to Loki.

    `Loki API <https://github.com/grafana/loki/blob/master/docs/api.md>`_
    """

    emitter: LokiEmitter

    def __init__(
        self,
        url: str,
        tags: Optional[dict] = None,
        headers: Optional[dict] = None,
        auth: Optional[BasicAuth] = None,
        as_json: Optional[bool] = False,
        props_to_labels: Optional[list[str]] = None,
    ):
        """
        Create new Loki logging handler.

        Arguments:
            url: Endpoint used to send log entries to Loki (e.g. `https://my-loki-instance/loki/api/v1/push`).
            tags: Default tags added to every log record.
            auth: Optional tuple with username and password for basic HTTP authentication.
            headers: Optional record with headers that are send with each POST to loki.
            as_json: Flag to support sending entire JSON record instead of only the message.
            props_to_labels: List of properties that sould be converted to loki labels.

        """
        super().__init__()
        self.emitter = LokiEmitter(url, tags, headers, auth, as_json, props_to_labels)

    def handleError(self, record):  # noqa: N802
        """Close emitter and let default handler take actions on error."""
        self.emitter.close()
        super().handleError(record)

    def emit(self, record: logging.LogRecord):
        """Send log record to Loki."""
        # noinspection PyBroadException
        try:
            self.emitter(record, self.format(record))
        except Exception:
            self.handleError(record)

    def emit_batch(self, records: list[logging.LogRecord]):
        """Send a batch of log records to Loki."""
        # noinspection PyBroadException
        try:
            self.emitter.emit_batch([(record, self.format(record)) for record in records])
        except Exception:
            for record in records:
                self.handleError(record)

class LokiBatchHandler(MemoryHandler):
    interval: float # The interval at which batched logs are sent in seconds
    _last_flush_time: float
    target: LokiHandler

    def __init__(self, interval: float, capacity: int = LOKI_MAX_BATCH_BUFFER_SIZE, **kwargs):
        super().__init__(capacity, **kwargs)
        self.interval = interval
        self._last_flush_time = time.time()

    def flush(self) -> None:
        self.acquire()
        try:
            if self.target and self.buffer:
                self.target.emit_batch(self.buffer)
                self.buffer.clear()
        finally:
            self.release()
        self._last_flush_time = time.time()

    def shouldFlush(self, record: logging.LogRecord) -> bool:
        return (
            super().shouldFlush(record) or 
            (time.time() - self._last_flush_time >= self.interval)
        )