# query_builder.py
class QueryBuildError(Exception):
    pass

import re

_ident = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def _q(ident: str) -> str:
    if not isinstance(ident, str) or not _ident.match(ident):
        raise QueryBuildError(f"Invalid identifier: {ident!r}")
    return f"`{ident}`"

def build_select(dataset, columns, filters, order_by, limit, offset, roles):
    if not dataset or not _ident.match(dataset):
        raise QueryBuildError("Unknown or missing dataset")

    # Columns
    if not columns:
        select_cols = ["*"]
        selected_cols = []
    else:
        select_cols = [_q(c) for c in columns]
        selected_cols = list(columns)

    # WHERE (ignored for now; safe stub)
    where_sql = ""

    # ORDER BY
    ob = []
    for item in (order_by or []):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise QueryBuildError("Invalid order_by item")
        col, direction = item
        direction = (direction or "").lower()
        if direction not in ("asc", "desc"):
            raise QueryBuildError("Order direction must be 'asc' or 'desc'")
        ob.append(f"{_q(col)} {direction.upper()}")
    order_sql = f" ORDER BY {', '.join(ob)}" if ob else ""

    # LIMIT/OFFSET
    lim_sql = ""
    if limit is not None:
        if not isinstance(limit, int) or limit < 0:
            raise QueryBuildError("limit must be a non-negative integer")
        lim_sql += f" LIMIT {limit}"
        if offset:
            if not isinstance(offset, int) or offset < 0:
                raise QueryBuildError("offset must be a non-negative integer")
            lim_sql += f" OFFSET {offset}"

    sql = f"SELECT {', '.join(select_cols)} FROM {_q(dataset)}{where_sql}{order_sql}{lim_sql}"
    params = {}
    return sql, params, selected_cols or select_cols
