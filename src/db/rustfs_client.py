from __future__ import annotations

from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.config import settings


def _build_client():
    if not settings.rustfs_endpoint:
        raise RuntimeError("RUSTFS_ENDPOINT is required")
    if not settings.rustfs_access_key or not settings.rustfs_secret_key:
        raise RuntimeError("RUSTFS_ACCESS_KEY and RUSTFS_SECRET_KEY are required")

    return boto3.client(
        "s3",
        endpoint_url=settings.rustfs_endpoint,
        aws_access_key_id=settings.rustfs_access_key,
        aws_secret_access_key=settings.rustfs_secret_key,
        region_name=settings.rustfs_region,
        use_ssl=settings.rustfs_secure,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def get_rustfs_client():
    return _build_client()


def _bucket_missing(error: ClientError) -> bool:
    error_code = error.response.get("Error", {}).get("Code", "")
    return error_code in {"404", "NoSuchBucket", "NotFound", "NoSuchBucketPolicy"}


def ensure_bucket(bucket_name: str) -> dict[str, Any]:
    client = get_rustfs_client()

    try:
        client.head_bucket(Bucket=bucket_name)
        return {"bucket": bucket_name, "created": False}
    except ClientError as error:
        if not _bucket_missing(error):
            raise

    create_kwargs: dict[str, Any] = {"Bucket": bucket_name}
    if settings.rustfs_region and settings.rustfs_region != "us-east-1":
        create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": settings.rustfs_region}

    client.create_bucket(**create_kwargs)
    return {"bucket": bucket_name, "created": True}


def ensure_default_buckets() -> dict[str, dict[str, Any]]:
    return {
        settings.rustfs_gameplay_bucket: ensure_bucket(settings.rustfs_gameplay_bucket),
        settings.rustfs_catalog_bucket: ensure_bucket(settings.rustfs_catalog_bucket),
    }


def put_object(bucket_name: str, object_key: str, body: bytes, content_type: str | None = None) -> dict[str, Any]:
    client = get_rustfs_client()

    request: dict[str, Any] = {
        "Bucket": bucket_name,
        "Key": object_key,
        "Body": body,
    }
    if content_type:
        request["ContentType"] = content_type

    response = client.put_object(**request)
    return {
        "bucket": bucket_name,
        "object_key": object_key,
        "etag": response.get("ETag"),
    }