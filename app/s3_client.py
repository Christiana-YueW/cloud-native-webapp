"""
S3 client wrapper with automatic metrics collection.
"""
import logging
import time
from typing import Any, BinaryIO, Dict, Optional

import boto3

from app.metrics import send_timing

logger = logging.getLogger("csye6225")

_s3_client = None


def get_s3_client():
    """Get or create the S3 client singleton."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


def upload_file(bucket: str, key: str, file_obj: BinaryIO, content_type: str) -> Dict[str, Any]:
    """
    Upload a file to S3 with automatic timing metrics.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key (path)
        file_obj: File-like object to upload
        content_type: MIME type of the file
    
    Returns:
        Dict with upload metadata
    """
    start_time = time.perf_counter()
    s3_client = get_s3_client()

    try:
        logger.info(f"s3_upload_started bucket={bucket} key={key}")

        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_obj,
            ContentType=content_type,
        )

        duration_ms = (time.perf_counter() - start_time) * 1000
        send_timing("s3.upload.duration", duration_ms)

        logger.info(
            f"s3_upload_completed bucket={bucket} key={key} duration_ms={duration_ms:.2f}"
        )

        return {
            "bucket": bucket,
            "key": key,
            "content_type": content_type,
        }

    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000
        send_timing("s3.upload.duration", duration_ms)

        logger.exception(
            f"s3_upload_failed bucket={bucket} key={key} duration_ms={duration_ms:.2f}"
        )
        raise


def upload_fileobj(
    file_obj: BinaryIO,
    bucket: str,
    key: str,
    extra_args: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Upload a file object to S3 with automatic timing metrics.

    This matches boto3's upload_fileobj signature for compatibility.
    
    Args:
        file_obj: File-like object to upload
        bucket: S3 bucket name
        key: S3 object key (path)
        extra_args: Optional dict of extra args (e.g., {'ContentType': 'application/pdf'})
    
    Returns:
        Dict with upload metadata
    """
    start_time = time.perf_counter()
    s3_client = get_s3_client()

    extra_args = extra_args or {}
    content_type = extra_args.get("ContentType", "application/octet-stream")

    try:
        logger.info(f"s3_upload_started bucket={bucket} key={key}")

        s3_client.upload_fileobj(
            file_obj,
            bucket,
            key,
            ExtraArgs=extra_args,
        )

        duration_ms = (time.perf_counter() - start_time) * 1000
        send_timing("s3.upload.duration", duration_ms)

        logger.info(
            f"s3_upload_completed bucket={bucket} key={key} duration_ms={duration_ms:.2f}"
        )

        return {
            "bucket": bucket,
            "key": key,
            "content_type": content_type,
        }

    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000
        send_timing("s3.upload.duration", duration_ms)

        logger.exception(
            f"s3_upload_failed bucket={bucket} key={key} duration_ms={duration_ms:.2f}"
        )
        raise




def delete_file(bucket: str, key: str) -> None:
    """
    Delete a file from S3 with automatic timing metrics.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key (path)
    """
    start_time = time.perf_counter()
    s3_client = get_s3_client()

    try:
        logger.info(f"s3_delete_started bucket={bucket} key={key}")

        s3_client.delete_object(
            Bucket=bucket,
            Key=key,
        )

        duration_ms = (time.perf_counter() - start_time) * 1000
        send_timing("s3.delete.duration", duration_ms)

        logger.info(
            f"s3_delete_completed bucket={bucket} key={key} duration_ms={duration_ms:.2f}"
        )

    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000
        send_timing("s3.delete.duration", duration_ms)

        logger.exception(
            f"s3_delete_failed bucket={bucket} key={key} duration_ms={duration_ms:.2f}"
        )
        raise