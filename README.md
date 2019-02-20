python-logging-loki
===================

[![PyPI version](https://img.shields.io/pypi/v/python-logging-loki.svg)](https://pypi.org/project/python-logging-loki/)
[![Python version](https://img.shields.io/badge/python-3.5%20%7C%203.6%20%7C%203.7-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/pypi/l/python-logging-loki.svg)](https://opensource.org/licenses/MIT)

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
    url="https://my-loki-instnace/api/prom/push", 
    tags={"application": "my-app"},
    auth=("username", "password"),    
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
from queue import Queue


queue = Queue(-1)
handler = logging.handlers.QueueHandler(queue)
handler_loki = logging_loki.LokiHandler(
    url="https://my-loki-instnace/api/prom/push", 
    tags={"application": "my-app"},
    auth=("username", "password"),    
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
from queue import Queue


handler = logging_loki.LokiQueueHandler(
    Queue(-1),
    url="https://my-loki-instnace/api/prom/push", 
    tags={"application": "my-app"},
    auth=("username", "password"),
)

logger = logging.getLogger("my-logger")
logger.addHandler(handler)
logger.error(...)
```
