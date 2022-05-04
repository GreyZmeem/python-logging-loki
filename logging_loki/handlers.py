# -*- coding: utf-8 -*-

import logging
import warnings
from logging.handlers import QueueHandler
from logging.handlers import QueueListener
from queue import Queue
from typing import Dict
from typing import Optional
from typing import Type

from logging_loki import const
from logging_loki import emitter


class LokiQueueHandler(QueueHandler):
    """This handler automatically creates listener and `LokiHandler` to handle logs queue."""

    def __init__(self, queue: Queue, **kwargs):
        """Create new logger handler with the specified queue and kwargs for the `LokiHandler`."""
        super().__init__(queue)
        self.handler = LokiHandler(**kwargs)  # noqa: WPS110
        self.listener = QueueListener(self.queue, self.handler)
        self.listener.start()


class LokiHandler(logging.Handler):
    """
    Log handler that sends log records to Loki.

    `Loki API <https://github.com/grafana/loki/blob/master/docs/api.md>`_
    """

    def __init__(
        self,
        url: str,
        tags: Optional[dict] = None,
        auth: Optional[emitter.BasicAuth] = None,
        emitter: emitter.LokiEmitter = emitter.LokiEmitter,
    ):
        """
        Create new Loki logging handler.

        Arguments:
            url: Endpoint used to send log entries to Loki (e.g. `https://my-loki-instance/loki/api/v1/push`).
            tags: Default tags added to every log record.
            auth: Optional tuple with username and password for basic HTTP authentication.
            version: Version of Loki emitter to use.

        """
        super().__init__()
        self.emitter = emitter(url, tags, auth)

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
