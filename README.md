python-logging-loki
===================

[![PyPI version](https://img.shields.io/pypi/v/python-logging-loki.svg)](https://pypi.org/project/python-logging-loki/)
[![Python version](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/pypi/l/python-logging-loki.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://travis-ci.org/GreyZmeem/python-logging-loki.svg?branch=master)](https://travis-ci.org/GreyZmeem/python-logging-loki)

Python logging handler for Loki.  
https://grafana.com/loki

Installation
============
```bash
pip install python-logging-loki
```

Usage
=====

```python
import logging
import logging_loki


handler = logging_loki.LokiHandler(
    url="https://my-loki-instance/loki/api/v1/push", 
    tags={"application": "my-app"},
    auth=("username", "password"),
    version="1",
)

logger = logging.getLogger("my-logger")
logger.addHandler(handler)
logger.error(
    "Something happened", 
    extra={"tags": {"service": "my-service"}},
)
```

Example above will send `Something happened` message along with these labels:
- Default labels from handler
- Message level as `serverity`
- Logger's name as `logger` 
- Labels from `tags` item of `extra` dict

The given example is blocking (i.e. each call will wait for the message to be sent).  
But you can use the built-in `QueueHandler` and` QueueListener` to send messages in a separate thread.  

```python
import logging.handlers
import logging_loki
from multiprocessing import Queue


queue = Queue(-1)
handler = logging.handlers.QueueHandler(queue)
handler_loki = logging_loki.LokiHandler(
    url="https://my-loki-instance/loki/api/v1/push", 
    tags={"application": "my-app"},
    auth=("username", "password"),
    version="1",
)
logging.handlers.QueueListener(queue, handler_loki)

logger = logging.getLogger("my-logger")
logger.addHandler(handler)
logger.error(...)
```

Or you can use `LokiQueueHandler` shortcut, which will automatically create listener and handler.

```python
import logging.handlers
import logging_loki
from multiprocessing import Queue


handler = logging_loki.LokiQueueHandler(
    Queue(-1),
    url="https://my-loki-instance/loki/api/v1/push", 
    tags={"application": "my-app"},
    auth=("username", "password"),
    version="1",
)

logger = logging.getLogger("my-logger")
logger.addHandler(handler)
logger.error(...)
```

Adding extra callable tags
--------------------------

Having a prior definition of:
```python
import logging
import logging_loki
from multiprocessing import Queue
from myapp.tracing import tracer

get_context = lambda: tracer.active_span.context
add_trace_id = lambda: hex(get_context().trace_id)[
                       2:] if tracer is not None and tracer.active_span is not None else None
add_span_id = lambda: hex(get_context().span_id)[2:] if tracer is not None and tracer.active_span else None
```

If you want to add extra span IDs or trace IDs do the following:

```python
handler = logging_loki.LokiQueueHandler(
    Queue(-1),
    url="https://my-loki-instance/loki/api/v1/push", 
    tags={"application": "my-app", 'span_id': add_span_id, 'trace_id': add_trace_id},
    auth=("username", "password"),
    version="1"
)
logger = logging.getLogger("my-logger")
logger.addHandler(handler)
logger.error(...)
```

Basically if your callable returns a non-None value, it will be added as a tag. No casting to string will be made.

You can use also the blocking approach of:

```python
handler = logging_loki.LokiHandler(
    url="https://my-loki-instance/loki/api/v1/push", 
    tags={"application": "my-app", "trace_id": add_trace_id, "span_id": add_span_id},
    auth=("username", "password"),
    version="1",
)

logger = logging.getLogger("my-logger")
logger.addHandler(handler)
logger.error(
    "Something happened", 
    extra={"tags": {"service": "my-service"}},
)
```

Note that Loki version "0" will not support callable tags.


Supplying extra tags
--------------------

If you want to supply extra tags, you can do it twofold:

```python
logger.error('Something happened', extra={'test': 4})
logger.error('Something happened', extra={'tags': {'test': 4}})
```