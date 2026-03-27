import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Generator, BinaryIO
from uuid import uuid4


class FileAttachment(ABC):
  """A file that has been attached but not yet put into storage. i.e. a local file."""

  def __init__(self, file_path: str):
    self._handle_update(file_path=file_path)

  def _handle_update(self, file_path: str, remote_path_prefix: Optional[str] = None) -> None:
    self._file_path = file_path
    self._original_filename = os.path.basename(file_path)
    self._uuid = str(uuid4())
    self._remote_path_prefix = remote_path_prefix

  @property
  def file_path(self) -> str:
    return self._file_path

  @file_path.setter
  def file_path(self, file_path: str) -> None:
    self._handle_update(file_path=file_path, remote_path_prefix=self._remote_path_prefix)

  @property
  def remote_path_prefix(self) -> Optional[str]:
    return self._remote_path_prefix

  @remote_path_prefix.setter
  def remote_path_prefix(self, remote_path_prefix: Optional[str]):
    self._remote_path_prefix = remote_path_prefix

  @property
  def original_filename(self) -> str:
    return self._original_filename

  @property
  def uuid(self) -> str:
    return self._uuid


class StoredFile:
  """A file from storage."""

  def __init__(self, remote_path: str, remote_path_prefix: Optional[str] = None):
    self._remote_path = remote_path
    self._remote_path_prefix = remote_path_prefix

  @property
  def remote_path(self) -> str:
    return self._remote_path

  @remote_path.setter
  def remote_path(self, remote_path: str) -> None:
    self._remote_path = remote_path

  @property
  def remote_path_prefix(self) -> Optional[str]:
    """Returns the path prefix this file is stored under (the remote_path should be this plus any path)."""
    return self._remote_path_prefix

  @remote_path_prefix.setter
  def remote_path_prefix(self, remote_path_prefix: Optional[str]) -> None:
    """Returns the path prefix this file is stored under."""
    self._remote_path_prefix = remote_path_prefix


class IStorageModel(ABC):
  """Define the StorageModel Interface.
  This is just done for clarity and for future expansion..
  I don't think this is a super common pattern or anything in python."""

  @abstractmethod
  def __init__(self, bucket: str, local_storage_path: str):
    pass

  @property
  @abstractmethod
  def bucket(self) -> str:
    pass

  @property
  @abstractmethod
  def local_storage_path(self) -> str:
    pass

  @local_storage_path.setter
  @abstractmethod
  def local_storage_path(self, local_storage_path: str) -> None:
    pass

  @abstractmethod
  def in_storage(self, stored_file: StoredFile) -> bool:
    """Return a boolean indicating if the stored_file exists remote storage"""
    pass

  @abstractmethod
  def in_local(self, stored_file: StoredFile) -> bool:
    """Return a boolean indicating if the stored_file exists in self.local_storage_path"""
    pass

  @abstractmethod
  def upload(
    self, attachment: FileAttachment, remote_path_prefix: Optional[str] = None
  ) -> StoredFile:
    """Upload a FileAttachment to remote storage and return a StoredFile object,
    optionally, placing the FileAttachment in a remote_path_prefix."""
    pass

  @abstractmethod
  def batch_upload(
    self, attachments: List[FileAttachment], remote_path_prefix: Optional[str] = None
  ) -> List[StoredFile]:
    """Upload a list of FileAttachments to remote storage and return a list of StoredFile objects,
    optionally, placing the FileAttachments in a remote_path_prefix."""
    pass

  @abstractmethod
  def download(
    self, remote_path: Optional[str] = None, stored_file: Optional[StoredFile] = None
  ) -> StoredFile:
    pass

  @abstractmethod
  def batch_download(
    self, remote_path: List[str], stored_file: List[StoredFile]
  ) -> List[StoredFile]:
    pass

  @abstractmethod
  def sync_to_local(self, stored_files: List[StoredFile]) -> List[StoredFile]:
    """Check if the List of StoredFiles exist in local storage and if not,
    batch_download the files to local storage."""
    pass

  @abstractmethod
  def cleanup_local_path(self, stored_files: List[StoredFile]):
    """This will REMOVE all files in the stored_files remote_path_prefix if it exists,
    otherwise it will just remove the stored_file."""
    pass

  @abstractmethod
  def delete(self, stored_file: Optional[StoredFile] = None, remote_path: Optional[str] = None):
    pass

  @abstractmethod
  def delete_prefix(self, remote_path: str):
    pass

  @abstractmethod
  def cleanup_remote_path(self, stored_files: List[StoredFile]):
    pass

  @abstractmethod
  def open(self, stored_file: StoredFile) -> Generator[BinaryIO, None, None]:
    """Return a context manager for a local file handle."""
    pass


class StorageModelFactory:
  """Factory class for creating SharedStorage Models.
  Use this to create an instance of a SharedStorage Model."""

  @staticmethod
  def create(provider: str, init_args: dict) -> IStorageModel:
    if provider == "s3":
      from shared_storage_s3 import StorageModelS3

      return StorageModelS3(**init_args)

    raise ValueError(f"Unknown storage model provider: {provider}")
