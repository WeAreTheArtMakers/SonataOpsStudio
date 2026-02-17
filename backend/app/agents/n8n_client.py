from __future__ import annotations

import logging
from typing import Any

import httpx
from opentelemetry import propagate, trace

from app.config import get_settings

logger = logging.getLogger(__name__)


class N8NClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def _post(self, url: str, payload: dict[str, Any]) -> None:
        tracer = trace.get_tracer("sonataops.n8n")
        with tracer.start_as_current_span("n8n.webhook") as span:
            span.set_attribute("http.url", url)

            if self.settings.n8n_mock_mode:
                logger.info("n8n mock mode payload=%s url=%s", payload, url)
                return

            headers: dict[str, str] = {}
            propagate.inject(headers)

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                span.set_attribute("http.status_code", response.status_code)
                response.raise_for_status()

    async def incident_narrator(self, payload: dict[str, Any]) -> None:
        await self._post(self.settings.n8n_webhook_incident, payload)

    async def exec_brief_generator(self, payload: dict[str, Any]) -> None:
        await self._post(self.settings.n8n_webhook_exec_brief, payload)

    async def anomaly_correlator(self, payload: dict[str, Any]) -> None:
        await self._post(self.settings.n8n_webhook_anomaly_correlator, payload)
