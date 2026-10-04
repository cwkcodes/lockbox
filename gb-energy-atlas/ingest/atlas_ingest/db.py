from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from . import config


def connect(**kw) -> psycopg.Connection:
    return psycopg.connect(config.DSN, row_factory=dict_row, **kw)
