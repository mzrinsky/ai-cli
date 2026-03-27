import os
import shutil
import sys

from typing import List, Optional, Generator, BinaryIO
from shared_storage import IStorageModel, FileAttachment, StoredFile

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


class StorageModelS3(IStorageModel):
  """Default implementation of IStorageModel for S3 storage using boto3."""

  def __init__(self, bucket: str, local_storage_path: str, init_args: Optional[dict]):
    self._bucket = bucket
    self._local_storage_path = local_storage_path
    if init_args is None:
      init_args = {}
    if "region_name" not in init_args:
      init_args["region_name"] = "us-east-1"
    self._client_config = init_args.copy()
    if "config" not in init_args:
      init_args["config"] = Config(signature_version="s3v4")

    self._client = boto3.client("s3", **init_args)

  @property
  def bucket(self) -> str:
    return self._bucket

  @property
  def local_storage_path(self) -> str:
    return self._local_storage_path

  @local_storage_path.setter
  def local_storage_path(self, local_storage_path: str) -> None:
    self._local_storage_path = local_storage_path

  def in_storage(self, stored_file: StoredFile) -> bool:
    """Check if a file is already in S3 storage."""
    try:
      self._client.head_object(Bucket=self._bucket, Key=stored_file.remote_path)
      return True
    except ClientError as e:
      if e.response["Error"]["Code"] == "404":
        return False
      raise

  def in_local(self, stored_file: StoredFile) -> bool:
    """Check if a file is already in local storage."""
    local_path = os.path.join(self._local_storage_path, stored_file.remote_path)
    return os.path.exists(local_path)

  def upload(
    self, attachment: FileAttachment, remote_path_prefix: Optional[str] = None
  ) -> StoredFile:
    """Upload a file attachment to S3 storage."""
    # Generate the remote path using the attachment's UUID
    if remote_path_prefix:
      attachment.remote_path_prefix = remote_path_prefix
    if attachment.remote_path_prefix:
      remote_path = (
        f"{attachment.remote_path_prefix}/{attachment.uuid}/{attachment.original_filename}"
      )
    else:
      remote_path = f"{attachment.uuid}/{attachment.original_filename}"

    # Upload to S3
    self._client.upload_file(
      attachment.file_path,
      self._bucket,
      remote_path,
      ExtraArgs={"ContentType": "application/octet-stream"},
    )

    # Return a StoredFile object with the remote path
    return StoredFile(remote_path=remote_path, remote_path_prefix=remote_path_prefix)

  def batch_upload(
    self, attachments: List[FileAttachment], remote_path_prefix: Optional[str] = None
  ) -> List[StoredFile]:
    """Upload multiple file attachments to S3 storage."""
    stored_files = []
    for attachment in attachments:
      stored_file = self.upload(attachment=attachment, remote_path_prefix=remote_path_prefix)
      print(f"SharedStorageS3 -> batch_upload : StoredFile {vars(stored_file)}")
      stored_files.append(stored_file)
    return stored_files

  def download(self, remote_path: Optional[str] = None, stored_file: Optional[StoredFile] = None) -> StoredFile:
    """Download a file from S3 to local storage."""
    if remote_path:
      local_path = os.path.join(self._local_storage_path, remote_path)
      local_dir = os.path.dirname(local_path)
      os.makedirs(local_dir, exist_ok=True)
      self._client.download_file(self._bucket, remote_path, local_path)
      return StoredFile(remote_path=remote_path)
    if stored_file:
      local_path = os.path.join(self._local_storage_path, stored_file.remote_path)
      local_dir = os.path.dirname(local_path)
      os.makedirs(local_dir, exist_ok=True)
      self._client.download_file(self._bucket, stored_file.remote_path, local_path)
      return stored_file

  def batch_download(
    self, remote_path: List[str], stored_file: List[StoredFile]
  ) -> List[StoredFile]:
    """Download multiple files from S3 to local storage."""
    results = []
    for path in remote_path:
      stored = self.download(remote_path=path)
      results.append(stored)
    for stored in stored_file:
      local_path = os.path.join(self._local_storage_path, stored.remote_path)
      local_dir = os.path.dirname(local_path)
      os.makedirs(local_dir, exist_ok=True)
      self._client.download_file(self._bucket, remote_path, local_path)
      results.append(stored)
    return results

  def sync_to_local(self, stored_files: List[StoredFile]) -> List[StoredFile]:
    """Check if the List of StoredFiles exist in local storage and if not,
    batch_download the files to local storage."""
    _stored_files = []
    for stored in stored_files:
      if not self.in_local(stored_file=stored):
        self.download(stored_file=stored)
        _stored_files.append(stored)
    return _stored_files

  def cleanup_local_path(self, stored_files: List[StoredFile]):
    """This will REMOVE all files in the stored_files remote_path_prefix if it exists,
    otherwise it will just remove the stored_file."""
    for file in stored_files:
      if file.remote_path_prefix:
        # If remote_path_prefix exists, remove all files under that prefix
        prefix_path = os.path.join(self._local_storage_path, file.remote_path_prefix)
        if os.path.exists(prefix_path):
          shutil.rmtree(prefix_path)
      else:
        # Remove the base-most path from the stored_file.remote_path
        local_path = os.path.join(self._local_storage_path, file.remote_path)
        if os.path.exists(local_path):
          os.remove(local_path)

  def delete(self, stored_file: Optional[StoredFile] = None, remote_path: Optional[str] = None):
    """Delete a file from storage."""
    s3 = boto3.resource('s3', **self._client_config)
    bucket = s3.Bucket(self._bucket)
    if stored_file and remote_path and stored_file.remote_path != remote_path:
      raise ValueError("stored_file and remote_path cannot both be provided")
    if remote_path:
      # This single call efficiently lists and then deletes the objects in batches
      bucket.objects.filter(Prefix=remote_path).delete()
      # this deletes any versioned files with that prefix
      bucket.object_versions.filter(Prefix=remote_path).delete()
    if stored_file:
      # This single call efficiently lists and then deletes the objects in batches
      bucket.objects.filter(Prefix=stored_file.remote_path).delete()
      # this deletes any versioned files with that prefix
      bucket.object_versions.filter(Prefix=stored_file.remote_path).delete()

  def delete_prefix(self, remote_path: str):
    """Delete all files with a given prefix."""
    s3 = boto3.resource('s3', **self._client_config)
    bucket = s3.Bucket(self._bucket)
    # This single call efficiently lists and then deletes the objects in batches
    bucket.objects.filter(Prefix=remote_path).delete()
    # this deletes any versioned files with that prefix
    bucket.object_versions.filter(Prefix=remote_path).delete()

  def cleanup_remote_path(self, stored_files: List[StoredFile]):
    s3 = boto3.resource('s3', **self._client_config)
    bucket = s3.Bucket(self._bucket)
    for stored_file in stored_files:
      # This single call efficiently lists and then deletes the objects in batches
      bucket.objects.filter(Prefix=stored_file.remote_path_prefix).delete()
      # this deletes any versioned files with that prefix
      bucket.object_versions.filter(Prefix=stored_file.remote_path_prefix).delete()

  def open(self, stored_file: StoredFile) -> Generator[BinaryIO, None, None]:
    """Return a context manager for a local file handle.

    This should be used with a 'with' statement to ensure proper
    resource management.

    Example:
        with storage_model.open(stored_file) as fh:
            fh.read()"""
    local_path = os.path.join(self._local_storage_path, stored_file.remote_path)
    with open(local_path, "rb") as f:
      yield f
