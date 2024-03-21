import logging
import time

import logging_loki
from logging_loki.emitter import LokiEmitterV1


def test_callable_tags():
    class MyEmitter(LokiEmitterV1):

        def build_payload(self, record, line) -> dict:
            labels = self.build_tags(record)
            ns = 1e9
            ts = str(int(time.time() * ns))
            stream = {
                "stream": labels,
                "values": [[ts, line, self.get_entry_labels(record, line)]],
            }
            return {"streams": [stream]}

        def __call__(self, record, line_no):
            payload = self.build_payload(record, line_no)
            stream = payload['streams'][0]['values'][0][2]
            assert 'application' in stream
            assert stream['value'] == 5
            assert stream['device'] == 'test'
            assert stream['levelname'] == 'WARNING'

    # Register a mock emitter
    logging_loki.LokiHandler.emitters['mock_emitter'] = MyEmitter

    handler = logging_loki.LokiHandler(
        url="https://example.com/loki/api/v1/push",
        tags={"application": "my-app", 'value': lambda: 5},
        auth=("username", "password"),
        version="mock_emitter"
    )
    logger = logging.getLogger("my-logger")
    logger.addHandler(handler)
    logger.warning('Error occurred', extra={'tags': {'device': 'test'}})
    logger.warning('Error occurred', extra={'device': 'test'})


def test_not_support_v0():
    try:
        logging_loki.LokiHandler(
            url="https://example.com/loki/api/v1/push",
            tags={"application": "my-app", 'value': lambda: 5},
            auth=("username", "password"),
            version="0")
    except ValueError:
        pass
    else:
        assert False, 'V0 supports callable labels'
