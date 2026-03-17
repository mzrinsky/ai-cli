from ai_cli.config import AppConfig
from ai_cli.job_queue import JobLoader, JobConsumer, IQueue, JobRequest, JobResult
from ai_cli.util import OutputFormatter
from ai_cli.shared_storage import IStorageModel
import os
from rich.console import Console
from socket import gethostname
from typing import Optional

class WorkerClient():

  def __init__( self, app_config: AppConfig, queue: IQueue, storage_model: Optional[ IStorageModel ], console: Console ):
    self.console = console
    self._app_config = app_config
    self._loader = JobLoader()
    self._queue = queue
    self._storage_model = storage_model
    job_dir = os.path.join( os.path.dirname( __file__ ), '..', '..', 'jobs' )
    self._loaded_jobs = self._loader.load_jobs( job_dir=job_dir, app_config=app_config, console=self.console )
    self._consumer = JobConsumer(
      supported_jobs=list( self._loaded_jobs.keys() ), queue=self._queue, request_callback=self._dispatch_request, host_id=gethostname()
    )

  def _dispatch_request( self, request: JobRequest ):
    if request.job_type in self._loaded_jobs:
      result = self._loaded_jobs[ request.job_type ].run()
      self._consumer.respond_to_request( request=request, result=result )
    else:
      self.console.log( "Config error, we should not be getting requests for jobs we can not run." )
      self._consumer.nack_request( request=request )

  def run( self ):
    self.console.print( "Worker Client Running." )
    self._consumer.start_consuming()
