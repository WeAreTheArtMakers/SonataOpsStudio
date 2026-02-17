from __future__ import annotations


def artifact_keys(workspace_id: str, metric_name: str, artifact_id: str) -> tuple[str, str]:
    prefix = f"{workspace_id}/audio/{metric_name}/{artifact_id}"
    return f"{prefix}.wav", f"{prefix}.mp3"
