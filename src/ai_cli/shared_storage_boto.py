from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol
import pickle
from uuid import uuid4
from shared_storage import IStorageModel, StorageModelError
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

class BotoStorageModel( IStorageModel ):

    """An implementation of the IStorageModel interface using the boto3 module."""

    def __init__( self, init_args: dict ):
        if "config" not in init_args:
            init_args["config"] = Config(signature_version='s3v4')
        if "region_name" not in init_args:
            init_args["region_name"] = "us-east-1"
        if "default_bucket" in init_args:
            del init_args["default_bucket"]

        self.client = boto3.client( 's3', **init_args )

    def list_buckets(self) -> dict:
        try:
            return self.client.list_buckets()
        except Exception as e:
            raise StorageModelError(f"Failed to list buckets: {e}") from e
    
    def upload_file(self, file_name: str, bucket: str, object_name: str) -> bool:
        try:
            return self.client.upload_file(file_name, bucket, object_name)
        except ClientError as e:
            raise StorageModelError(f"Failed to upload file: {e}") from e

    def download_file(self, file_name: str, bucket: str, object_name: str):
        try:
            return self.client.download_file(bucket, object_name, file_name)
        except Exception as e:
            raise StorageModelError(f"Failed to download file: {e}") from e
