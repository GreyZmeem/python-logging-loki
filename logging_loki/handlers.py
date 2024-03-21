# -*- coding: utf-8 -*-
import copy
import logging
import warnings
from logging.handlers import QueueHandler
from logging.handlers import QueueListener
from queue import Queue
from typing import Dict, Callable, Any, Union
from typing import Optional
from typing import Type

from logging_loki import const
from logging_loki import emitter


class TagMixin:
    """
    A mixin class to support callable tags.

    This is to be inherited from as a first class, eg
    >>> class Handler(TagMixin, logging.Handler):
    >>>     pass
    """

    def __init__(self, tags=None):
        self.tags = tags or {}

    def prepare(self, record):
        # This is invoked in the same thread in which logging is invoked
        # assume the second class has a proper solution for prepare()
        try:
            record = self.__class__.__bases__[1].prepare(self, record)
        except AttributeError:      # logging.Handler has no prepare
            pass
        record.tags = getattr(record, 'tags', {})
        for key, value in (self.tags | record.tags).items():
            if callable(value):
                value = value()
            if value is None:
                continue
            record.__dict__[key] = value
        return record


class LokiQueueHandler(TagMixin, QueueHandler):
    """This handler automatically creates listener and `LokiHandler` to handle logs queue."""

    def __init__(self, queue: Queue, **kwargs):
        """Create new logger handler with the specified queue and kwargs for the `LokiHandler`."""
        QueueHandler.__init__(self, queue)
        TagMixin.__init__(self, kwargs.get("tags"))
        self.handler = LokiHandler(**kwargs)  # noqa: WPS110
        self.listener = QueueListener(self.queue, self.handler)
        self.listener.start()


class LokiHandler(TagMixin, logging.Handler):
    """
    Log handler that sends log records to Loki.

    `Loki API <https://github.com/grafana/loki/blob/master/docs/api.md>`_
    """

    emitters: Dict[str, Type[emitter.LokiEmitter]] = {
        "0": emitter.LokiEmitterV0,
        "1": emitter.LokiEmitterV1,
    }

    def __init__(
        self,
        url: str,
        tags: Optional[Dict[str, Union[Any, Callable]]] = None,
        auth: Optional[emitter.BasicAuth] = None,
        version: Optional[str] = None,
    ):
        """
        Create new Loki logging handler.

        Arguments:
            url: Endpoint used to send log entries to Loki (e.g. `https://my-loki-instance/loki/api/v1/push`).
            tags: Default tags added to every log record.
            auth: Optional tuple with username and password for basic HTTP authentication.
            version: Version of Loki emitter to use.

        """
        logging.Handler.__init__(self)
        TagMixin.__init__(self, tags)

        if version is None and const.emitter_ver == "0":
            msg = (
                "Loki /api/prom/push endpoint is in the depreciation process starting from version 0.4.0.",
                "Explicitly set the emitter version to '0' if you want to use the old endpoint.",
                "Or specify '1' if you have Loki version> = 0.4.0.",
                "When the old API is removed from Loki, the handler will use the new version by default.",
            )
            warnings.warn(" ".join(msg), DeprecationWarning)

        my_tags = tags or {}

        version = version or const.emitter_ver
        if version == '0' and any(callable(value) for value in my_tags.values()):
            raise ValueError('Loki V0 handler does not support callable tags!')

        try:
            self.emitter = self.emitters[version](url, tags, auth)
        except KeyError as exc:
            raise ValueError("Unknown emitter version: {0}".format(version)) from exc

    def handleError(self, record):  # noqa: N802
        """Close emitter and let default handler take actions on error."""
        self.emitter.close()
        super().handleError(record)

    def emit(self, record: logging.LogRecord):
        """Send log record to Loki."""
        record = self.prepare(record)
        # noinspection PyBroadException
        try:
            self.emitter(record, record.lineno)
        except Exception:
            self.handleError(record)
