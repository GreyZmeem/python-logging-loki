# -*- coding: utf-8 -*-

import logging
import time
from logging.config import dictConfig as loggingDictConfig
from queue import Queue
from typing import Tuple
from unittest.mock import MagicMock

import pytest
import rfc3339
from freezegun import freeze_time

from logging_loki.emitter import LokiEmitterV0

emitter_url: str = "https://example.net/api/prom/push"
record_kwargs = {
    "name": "test",
    "level": logging.WARNING,
    "fn": "",
    "lno": "",
    "msg": "Test",
    "args": None,
    "exc_info": None,
}


@pytest.fixture()
def emitter_v0() -> Tuple[LokiEmitterV0, MagicMock]:
    """Create v1 emitter with mocked http session."""
    response = MagicMock()
    response.status_code = LokiEmitterV0.success_response_code
    session = MagicMock()
    session().post = MagicMock(return_value=response)

    instance = LokiEmitterV0(url=emitter_url)
    instance.session_class = session

    return instance, session


def create_record(**kwargs) -> logging.LogRecord:
    """Create test logging record."""
    log = logging.Logger(__name__)
    return log.makeRecord(**{**record_kwargs, **kwargs})


def get_stream(session: MagicMock) -> dict:
    """Return first stream item from json payload."""
    kwargs = session().post.call_args[1]
    streams = kwargs["json"]["streams"]
    return streams[0]


def test_record_sent_to_emitter_url(emitter_v0):
    emitter, session = emitter_v0
    emitter(create_record(), "")

    got = session().post.call_args
    assert got[0][0] == emitter_url


def test_default_tags_added_to_payload(emitter_v0):
    emitter, session = emitter_v0
    emitter.tags = {"app": "emitter"}
    emitter(create_record(), "")

    stream = get_stream(session)
    level = logging.getLevelName(record_kwargs["level"]).lower()
    expected_tags = (
        'app="emitter"',
        '{0}="{1}"'.format(emitter.level_tag, level),
        '{0}="{1}"'.format(emitter.logger_tag, record_kwargs["name"]),
    )
    expected = ",".join(expected_tags)
    expected = "{{{0}}}".format(expected)
    assert stream["labels"] == expected


def test_extra_tag_added(emitter_v0):
    emitter, session = emitter_v0
    record = create_record(extra={"tags": {"extra_tag": "extra_value"}})
    emitter(record, "")

    stream = get_stream(session)
    assert 'extra_tag="extra_value"' in stream["labels"]


@pytest.mark.parametrize(
    "emitter_v0, label",
    (
        (emitter_v0, "test_'svc"),
        (emitter_v0, 'test_"svc'),
        (emitter_v0, "test svc"),
        (emitter_v0, "test-svc"),
        (emitter_v0, "test.svc"),
        (emitter_v0, "!test_svc?"),
    ),
    indirect=["emitter_v0"],
)
def test_label_properly_formatted(emitter_v0, label: str):
    emitter, session = emitter_v0
    record = create_record(extra={"tags": {label: "extra_value"}})
    emitter(record, "")

    stream = get_stream(session)
    assert ',test_svc="extra_value"' in stream["labels"]


def test_empty_label_is_not_added_to_stream(emitter_v0):
    emitter, session = emitter_v0
    record = create_record(extra={"tags": {"!": "extra_value"}})
    emitter(record, "")

    stream = get_stream(session)
    assert "!" not in stream["labels"]
    assert ",=" not in stream["labels"]


def test_non_dict_extra_tag_is_not_added_to_stream(emitter_v0):
    emitter, session = emitter_v0
    record = create_record(extra={"tags": "invalid"})
    emitter(record, "")

    stream = get_stream(session)
    assert "invalid" not in stream["labels"]


def test_raises_value_error_on_non_successful_response(emitter_v0):
    emitter, session = emitter_v0
    session().post().status_code = None
    with pytest.raises(ValueError):
        emitter(create_record(), "")
        pytest.fail("Must raise ValueError on non-successful Loki response")  # pragma: no cover


def test_logged_messaged_added_to_values(emitter_v0):
    emitter, session = emitter_v0
    emitter(create_record(), "Test message")

    stream = get_stream(session)
    assert stream["entries"][0]["line"] == "Test message"


@freeze_time("2019-11-04 00:25:08.123456")
def test_timestamp_added_to_values(emitter_v0):
    emitter, session = emitter_v0
    emitter(create_record(), "")

    stream = get_stream(session)
    expected = rfc3339.format_microsecond(time.time())
    assert stream["entries"][0]["ts"] == expected


def test_session_is_closed(emitter_v0):
    emitter, session = emitter_v0
    emitter(create_record(), "")
    emitter.close()
    session().close.assert_called_once()
    assert emitter._session is None  # noqa: WPS437


def test_can_build_tags_from_converting_dict(emitter_v0):
    logger_name = "converting_dict_tags_v0"
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            logger_name: {
                "class": "logging_loki.LokiQueueHandler",
                "queue": Queue(-1),
                "url": emitter_url,
                "tags": {"test": "test"},
                "version": "0",
            },
        },
        "loggers": {logger_name: {"handlers": [logger_name], "level": "DEBUG"}},
    }
    loggingDictConfig(config)

    logger = logging.getLogger(logger_name)
    emitter: LokiEmitterV0 = logger.handlers[0].handler.emitter
    emitter.build_tags(create_record())
