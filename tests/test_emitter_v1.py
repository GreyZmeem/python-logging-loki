# -*- coding: utf-8 -*-

import logging
from logging.config import dictConfig as loggingDictConfig
from queue import Queue
from typing import Tuple
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

from logging_loki.emitter import LokiEmitterV1

emitter_url: str = "https://example.net/loki/api/v1/push/"
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
def emitter_v1() -> Tuple[LokiEmitterV1, MagicMock]:
    """Create v1 emitter with mocked http session."""
    response = MagicMock()
    response.status_code = LokiEmitterV1.success_response_code
    session = MagicMock()
    session().post = MagicMock(return_value=response)

    instance = LokiEmitterV1(url=emitter_url)
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


def test_record_sent_to_emitter_url(emitter_v1):
    emitter, session = emitter_v1
    emitter(create_record(), "")

    got = session().post.call_args
    assert got[0][0] == emitter_url


def test_default_tags_added_to_payload(emitter_v1):
    emitter, session = emitter_v1
    emitter.tags = {"app": "emitter"}
    emitter(create_record(), "")

    stream = get_stream(session)
    level = logging.getLevelName(record_kwargs["level"]).lower()
    expected = {
        emitter.level_tag: level,
        emitter.logger_tag: record_kwargs["name"],
        "app": "emitter",
    }
    assert stream["stream"] == expected


def test_extra_tag_added(emitter_v1):
    emitter, session = emitter_v1
    record = create_record(extra={"tags": {"extra_tag": "extra_value"}})
    emitter(record, "")

    stream = get_stream(session)
    assert stream["stream"]["extra_tag"] == "extra_value"


@pytest.mark.parametrize(
    "emitter_v1, label",
    (
        (emitter_v1, "test_'svc"),
        (emitter_v1, 'test_"svc'),
        (emitter_v1, "test svc"),
        (emitter_v1, "test-svc"),
        (emitter_v1, "test.svc"),
        (emitter_v1, "!test_svc?"),
    ),
    indirect=["emitter_v1"],
)
def test_label_properly_formatted(emitter_v1, label: str):
    emitter, session = emitter_v1
    record = create_record(extra={"tags": {label: "extra_value"}})
    emitter(record, "")

    stream = get_stream(session)
    assert stream["stream"]["test_svc"] == "extra_value"


def test_empty_label_is_not_added_to_stream(emitter_v1):
    emitter, session = emitter_v1
    record = create_record(extra={"tags": {"!": "extra_value"}})
    emitter(record, "")

    stream = get_stream(session)
    assert set(stream["stream"]) == {emitter.logger_tag, emitter.level_tag}


def test_non_dict_extra_tag_is_not_added_to_stream(emitter_v1):
    emitter, session = emitter_v1
    record = create_record(extra={"tags": "invalid"})
    emitter(record, "")

    stream = get_stream(session)
    assert set(stream["stream"]) == {emitter.logger_tag, emitter.level_tag}


def test_raises_value_error_on_non_successful_response(emitter_v1):
    emitter, session = emitter_v1
    session().post().status_code = None
    with pytest.raises(ValueError):
        emitter(create_record(), "")
        pytest.fail("Must raise ValueError on non-successful Loki response")  # pragma: no cover


def test_logged_messaged_added_to_values(emitter_v1):
    emitter, session = emitter_v1
    emitter(create_record(), "Test message")

    stream = get_stream(session)
    assert stream["values"][0][1] == "Test message"


@freeze_time("2019-11-04 00:25:08.123456")
def test_timestamp_added_to_values(emitter_v1):
    emitter, session = emitter_v1
    emitter(create_record(), "")

    stream = get_stream(session)
    expected = 1572827108123456000
    assert stream["values"][0][0] == str(expected)


def test_session_is_closed(emitter_v1):
    emitter, session = emitter_v1
    emitter(create_record(), "")
    emitter.close()
    session().close.assert_called_once()
    assert emitter._session is None  # noqa: WPS437


def test_can_build_tags_from_converting_dict(emitter_v1):
    logger_name = "converting_dict_tags_v1"
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            logger_name: {
                "class": "logging_loki.LokiQueueHandler",
                "queue": Queue(-1),
                "url": emitter_url,
                "tags": {"test": "test"},
                "version": "1",
            },
        },
        "loggers": {logger_name: {"handlers": [logger_name], "level": "DEBUG"}},
    }
    loggingDictConfig(config)

    logger = logging.getLogger(logger_name)
    emitter: LokiEmitterV1 = logger.handlers[0].handler.emitter
    emitter.build_tags(create_record())
