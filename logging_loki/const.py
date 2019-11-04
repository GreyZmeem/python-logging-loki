# -*- coding: utf-8 -*-

import string
from typing import Tuple

#: Default Loki emitter version.
emitter_ver: str = "0"
#: Size of LRU cache for LogQL label formatting.
format_label_lru_size: int = 256

#: Success HTTP status code from Loki API.
success_response_code: int = 204

#: Label name indicating logging level.
level_tag: str = "severity"
#: Label name indicating logger name.
logger_tag: str = "logger"

#: String contains chars that can be used in label names in LogQL.
label_allowed_chars: str = "".join((string.ascii_letters, string.digits, "_"))
#: A list of pairs of characters to replace in the label name.
label_replace_with: Tuple[Tuple[str, str], ...] = (
    ("'", ""),
    ('"', ""),
    (" ", "_"),
    (".", "_"),
    ("-", "_"),
)
