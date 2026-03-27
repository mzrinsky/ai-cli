from ai_cli.app import AppConfig
from ai_cli.shared_storage import IStorageModel, FileAttachment, StoredFile
from ai_cli.job_queue import (
  JobLoader,
  JobConsumer,
  ResponseConsumer,
  JobSeeder,
  IQueue,
  JobRequest,
  JobResponse,
)
from ai_cli.util import OutputFormatter
from dataclasses import field
import os
from rich.console import Console
from rich.markdown import Markdown
from socket import gethostname
from typing import Optional
from uuid import uuid4
import warnings


class HybridClient:
  _outstanding_jobs = []

  def __init__(
    self,
    app_config: AppConfig,
    queue: IQueue,
    console: Console,
    playbook: Optional[dict] = None,
    storage_model: Optional[IStorageModel] = None,
    file_attachments: list[FileAttachment] = field(default_factory=list),
    workflow: Optional[dict] = None,
  ):
    self.console = console
    self._app_config = app_config
    self._playbook = playbook
    self._workflow = workflow
    self._loader = JobLoader()
    self._queue = queue
    self._storage_model = storage_model
    self._file_attachments = file_attachments
    self._outout_formatter = OutputFormatter(app_config=self._app_config)
    if app_config.worker or app_config.wait_for_result:
      job_dir = os.path.join(os.path.dirname(__file__), "..", "..", "jobs")
      self._loaded_jobs = self._loader.load_jobs(
        job_dir=job_dir, app_config=app_config, console=self.console, storage_model=storage_model
      )
    if app_config.worker:
      self._job_consumer = JobConsumer(
        supported_jobs=list(self._loaded_jobs.keys()),
        queue=self._queue,
        request_callback=self._dispatch_request,
        host_id=gethostname(),
      )
    if app_config.wait_for_result:
      self._response_consumer = ResponseConsumer(
        queue=self._queue,
        supported_jobs=list(self._loaded_jobs.keys()),
        response_callback=self._dispatch_response,
        host_id=gethostname(),
      )
    self._job_seeder = JobSeeder(queue=self._queue)

  def _mark_job_complete(self, response: JobResponse):
    for job in list(self._outstanding_jobs):
      if str(job.message_id) == response.request_message_id:
        self._outstanding_jobs.remove(job)
        break

  def _dispatch_request(self, request: JobRequest):
    if self._app_config.verbose > 3:
      self.console.print(f"HybridClient._dispatch_request -> {request}")
    if request.job_name in self._loaded_jobs:
      result = self._loaded_jobs[request.job_name].run(request=request)
      self._job_consumer.respond_to_request(request=request, result=result)
    else:
      warnings.warn("No loaded jobs match job request, queues may be misconfigured.")
      # TODO: it's safer to dead-letter this right away..?
      self._job_consumer.nack_request(request=request)

  def _dispatch_response(self, response: JobResponse):
    if self._app_config.verbose > 3:
      self.console.print(f"HybridClient._dispatch_response : {vars(response)}")

    self._storage_model.delete_prefix(remote_path=response.request_message_id)

    self.console.print(f"ReplyTo: {response.request_message_id}")

    output = self._outout_formatter.format(response.result)
    self.console.print(Markdown(output))
    self._response_consumer.ack_response(response=response)
    self._mark_job_complete(response=response)
    if not len(self._outstanding_jobs):
      if self._app_config.verbose:
        self.console.print("All jobs complete, exiting.")
      exit()

  def _store_file_attachments(self, remote_path_prefix: str) -> list[StoredFile]:
    stored_files = []
    if self._storage_model:
      stored_files = self._storage_model.batch_upload(
        attachments=self._file_attachments, remote_path_prefix=remote_path_prefix
      )
      for file in stored_files:
        self.console.print(f"HybridClient -> _store_file_attachments got StoredFile: {vars(file)}")
    return stored_files

  def _cleanup_stored_files(self, stored_files: list[StoredFile]):
    self._storage_model.cleanup_remote_path(stored_files=stored_files)

  def run(self):
    if self._app_config.verbose > 1:
      self.console.print("Hybrid Client Running.")
    if self._app_config.job and self._playbook:
      if self._app_config.verbose > 1:
        self.console.print(f"HybridClient -> sending job request '{self._app_config.job}'")
      request_id = str(uuid4())
      stored_files = []
      if self._file_attachments:
        if self._app_config.verbose > 1:
          self.console.print(
            f"Storing {len(self._file_attachments)} FileAttachments for JobRequest '{request_id}' ..."
          )
        stored_files = self._store_file_attachments(remote_path_prefix=request_id)
      new_job = JobRequest(
        message_id=request_id,
        job_name=self._app_config.job,
        origin=gethostname(),
        job_playbook=self._playbook,
        stored_files=stored_files,
      )
      self._outstanding_jobs.append(new_job)
      if self._app_config.verbose:
        self.console.print(f"Seeding job '{new_job.job_name}' to queue ...")
        self.console.print(Markdown(self._outout_formatter.format(object=new_job)))
      self._job_seeder.send_request(request=new_job)
    elif self._workflow:
      if self._app_config.verbose > 1:
        if "name" in self._workflow:
          workflow_name = self._workflow["name"]
        if not workflow_name:
          workflow_name = self._app_config.workflow_file.name
        self.console.print(f"HybridClient -> sending workflow request '{workflow_name}'")
        request_id = str(uuid4())
        stored_files = []
        if self._file_attachments:
          if self._app_config.verbose > 1:
            self.console.print(
              f"Storing {len(self._file_attachments)} FileAttachments for JobRequest '{request_id}' ..."
            )
          stored_files = self._store_file_attachments(remote_path_prefix=request_id)
        new_job = JobRequest(
          message_id=request_id,
          job_name="workflow",
          origin=gethostname(),
          job_playbook=self._workflow,
          stored_files=stored_files,
        )
        self._outstanding_jobs.append(new_job)
        if self._app_config.verbose:
          self.console.print(f"Seeding job '{new_job.job_name}' to queue ...")
          self.console.print(Markdown(self._outout_formatter.format(object=new_job)))
        self._job_seeder.send_request(request=new_job)
    if self._app_config.wait_for_result and self._app_config.worker:
      if self._app_config.verbose:
        self.console.print("Waiting for job result ...")
      self._job_consumer.start_consuming()
