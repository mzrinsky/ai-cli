import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

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
    if "config" not in init_args:
      init_args["config"] = Config(signature_version="s3v4")
    if "region_name" not in init_args:
      init_args["region_name"] = "us-east-1"
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

  def upload(self, attachment: FileAttachment) -> StoredFile:
    """Upload a file attachment to S3 storage."""
    # Generate the remote path using the attachment's UUID
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
    return StoredFile(remote_path)

  def batch_upload(self, attachments: List[FileAttachment]) -> List[StoredFile]:
    """Upload multiple file attachments to S3 storage."""
    stored_files = []
    for attachment in attachments:
      stored_file = self.upload(attachment)
      stored_files.append(stored_file)
    return stored_files

  def download(self, remote_path: str) -> StoredFile:
    """Download a file from S3 to local storage."""
    local_path = os.path.join(self._local_storage_path, os.path.basename(remote_path))
    self._client.download_file(self._bucket, remote_path, local_path)
    return StoredFile(remote_path)

  def batch_download(
    self, remote_path: List[str], stored_file: List[StoredFile]
  ) -> List[StoredFile]:
    """Download multiple files from S3 to local storage."""
    results = []
    for path in remote_path:
      self.download(remote_path=path)
      results.append(StoredFile(path))
    for stored in stored_file:
      local_path = os.path.join(self._local_storage_path, os.path.basename(stored.remote_path))
      self._client.download_file(self._bucket, remote_path, local_path)
      results.append(stored)
    return results

  def delete(self, stored_file: Optional[StoredFile] = None, remote_path: Optional[str] = None):
    """Delete a file from storage."""
    bucket = self._client.Bucket(self._bucket)
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
    bucket = self._client.Bucket(self._bucket)
    # This single call efficiently lists and then deletes the objects in batches
    bucket.objects.filter(Prefix=remote_path).delete()
    # this deletes any versioned files with that prefix
    bucket.object_versions.filter(Prefix=remote_path).delete()

  def open(self, stored_file: StoredFile) -> Generator[BinaryIO, None, None]:
    """Return a context manager for a local file handle.

    This should be used with a 'with' statement to ensure proper
    resource management.

    Example:
        with storage_model.local_fh(stored_file) as fh:
            fh.read()
            fh.write(data)"""
    local_path = os.path.join(self._local_storage_path, stored_file.remote_path)
    with open(local_path, "rb") as f:
      yield f
