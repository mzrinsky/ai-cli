from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


@dataclass( frozen=True )
class IStorageModel( ABC ):
  """Interface for shared storage models."""

  @abstractmethod
  def __init__( self, init_args: dict ):
     pass

  @abstractmethod
  def list_buckets( self ) -> dict:
    pass

  @abstractmethod
  def upload_file( self, file_name: str, bucket: str, object_name: str) -> bool:
    pass

  @abstractmethod
  def download_file( self, file_name: str, bucket: str, object_name: str):
    pass


class StorageModelError(Exception):
    """Exception class for storage model errors."""
    
    def __init__(self, message: str, cause: Exception = None):
        super().__init__(message)
        self.cause = cause


class StorageModelFactory:
    """Factory for creating instances of shared storage models."""
    
    @staticmethod
    def create_storage_model(provider: str, init_args: dict) -> IStorageModel:
        if provider == 's3':
            from shared_storage_boto import BotoStorageModel
            return BotoStorageModel(init_args=init_args)
        
        raise ValueError( f"Unknown storage model provider: {provider}" )
