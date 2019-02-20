import logging
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Optional, Tuple, Dict, Any

import requests
import rfc3339

BasicAuth = Optional[Tuple[str, str]]


class LokiQueueHandler(QueueHandler):
    """
    This handler automatically creates listener and `LokiHandler` to handle logs queue.
    """

    def __init__(self, queue: Queue, url: str, tags: Optional[dict] = None, auth: BasicAuth = None):
        super().__init__(queue)
        self.handler = LokiHandler(url, tags, auth)
        self.listener = QueueListener(self.queue, self.handler)
        self.listener.start()


class LokiHandler(logging.Handler):
    """
    This handler sends log records to Loki via HTTP API.
    https://github.com/grafana/loki/blob/master/docs/api.md
    """

    level_tag: str = "severity"
    logger_tag: str = "logger"

    def __init__(self, url: str, tags: Optional[dict] = None, auth: BasicAuth = None):
        super().__init__()

        # Tags that will be added to all records handled by this handler.
        self.tags = tags or {}

        # Loki HTTP API endpoint (e.g `http://127.0.0.1/api/prom/push`)
        self.url = url

        # Optional tuple with username and password for basic authentication
        self.auth = auth

        self._session: requests.Session = None

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = self.auth or None
        return self._session

    def handleError(self, record):
        super().handleError(record)
        if self._session is not None:
            self._session.close()
            self._session = None

    def emit(self, record: logging.LogRecord):
        """
        Send log record to Loki.
        """
        # noinspection PyBroadException
        try:
            labels = self.build_labels(record)
            ts = rfc3339.format(record.created)
            line = self.format(record)
            payload = {"streams": [{"labels": labels, "entries": [{"ts": ts, "line": line}]}]}
            resp = self.session.post(self.url, json=payload)
            if resp.status_code != 204:
                raise ValueError("Unexpected Loki API response status code: %s" % resp.status_code)
        except Exception:
            self.handleError(record)

    def build_labels(self, record: logging.LogRecord) -> str:
        """
        Return Loki labels string.
        """
        tags = self.build_tags(record)
        labels = ",".join(['%s="%s"' % (k, str(v).replace('"', '\\"')) for k, v in tags.items()])
        return "{%s}" % labels

    def build_tags(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        Return tags that must be send to Loki with a log record.
        """
        tags = self.tags.copy()
        tags[self.level_tag] = record.levelname.lower()
        tags[self.logger_tag] = record.name

        extra_tags = getattr(record, "tags", {})
        if isinstance(extra_tags, dict):
            tags.update(extra_tags)

        return tags
