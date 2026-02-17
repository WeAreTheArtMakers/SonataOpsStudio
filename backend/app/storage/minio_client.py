from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from minio import Minio
from opentelemetry import trace

from app.config import get_settings

logger = logging.getLogger(__name__)

_minio: "MinioService | None" = None


class MinioService:
    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.minio_bucket
        self.internal_client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        # Backward-compatible attribute used by health checks.
        self.client = self.internal_client
        public = urlparse(settings.public_minio_url)
        public_endpoint = public.netloc or settings.minio_endpoint
        public_secure = (public.scheme == "https") if public.scheme else settings.minio_secure
        self.public_client = Minio(
            endpoint=public_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=public_secure,
            region="us-east-1",
        )

    def ensure_bucket(self) -> None:
        tracer = trace.get_tracer("sonataops.minio")
        with tracer.start_as_current_span("minio.ensure_bucket"):
            if not self.internal_client.bucket_exists(self.bucket):
                self.internal_client.make_bucket(self.bucket)

    def upload_file(self, object_key: str, local_path: Path, content_type: str) -> None:
        tracer = trace.get_tracer("sonataops.minio")
        with tracer.start_as_current_span("minio.upload") as span:
            span.set_attribute("storage.key", object_key)
            self.internal_client.fput_object(
                bucket_name=self.bucket,
                object_name=object_key,
                file_path=str(local_path),
                content_type=content_type,
            )

    def signed_url(self, object_key: str, expires_seconds: int = 300) -> str:
        tracer = trace.get_tracer("sonataops.minio")
        with tracer.start_as_current_span("minio.presigned_get") as span:
            span.set_attribute("storage.key", object_key)
            return self.public_client.presigned_get_object(
                bucket_name=self.bucket,
                object_name=object_key,
                expires=timedelta(seconds=expires_seconds),
            )


def init_minio() -> None:
    global _minio
    if _minio:
        return
    _minio = MinioService()
    _minio.ensure_bucket()
    logger.info("minio initialized")


def get_minio() -> MinioService:
    if _minio is None:
        raise RuntimeError("minio is not initialized")
    return _minio
