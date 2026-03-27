from ai_cli.job_queue import IJob, JobRequest, JobResult
from ai_cli.shared_storage import IStorageModel
from rich.console import Console

class Echo(IJob):
  """Job that can echo a request back as a test job."""

  def __init__(self, app_config: dict, console: Console, storage_model: IStorageModel):
    self._console = console
    self._app_config = app_config
    self._storage_model = storage_model
    
  def run(self, request: JobRequest) -> JobResult:
    # do all the work, and return a JobResult.
    self._console.print("Running Echo job")
    if self._app_config.verbose:
      self._console.print(f"Job Playbook: {request.job_playbook}")
    return JobResult(value=f"Echo of Request: {request.job_playbook}")
