from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def clickhouse_rows_from_points(points: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for point in points:
        ts = point["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        rows.append(
            (
                point["workspace_id"],
                point["metric_name"],
                ts,
                float(point["value"]),
                json.dumps(point.get("tags", {}), separators=(",", ":")),
            )
        )
    return rows
