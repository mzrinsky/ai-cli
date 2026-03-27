import sys
import os
import inspect


from dataclasses import dataclass, field
from ai_cli.job_queue import IJob, IJobRequest, JobRequest, IJobResult, JobResult, JobLoader
from ai_cli.shared_storage import IStorageModel, StoredFile
from ai_cli.workflow import WorkflowLoader
from ai_cli.config import AppConfig
from typing import Optional
from rich.console import Console
import json


class Workflow(IJob):
  _app_config: AppConfig
  _request: JobRequest
  _storage_model: IStorageModel
  _output: list[str] = []
  _errors: list[str] = []
  _console: Console

  def __init__(self, app_config: AppConfig, console: Console, storage_model: IStorageModel):
    self._app_config = app_config
    self._console = console
    self._storage_model = storage_model
    self._loader = JobLoader()
    # we want to get our own copy of the loaded jobs, excluding ourself (or it will be a circular reference)
    job_dir = os.path.dirname(__file__)
    self._loaded_jobs = self._loader.load_jobs(
      job_dir=job_dir, app_config=app_config, console=self._console, storage_model=storage_model, exclude=["workflow"]
    )
    if app_config.verbose > 3:
      console.print(f"Loaded Jobs is now: {self._loaded_jobs}")

  def run(self, request: IJobRequest) -> list[IJobResult]:
    self._console.print(f"Workflow Job Got Request: {request}")
    self._console.print(f"Workflow Stored Files: {request.job_playbook.stored_files}")
    for file in request.job_playbook.stored_files:
      self._console.print(f"SharedFile is: {vars(file)}")
    self._console.print(f"Syncing files to local: {request.job_playbook.stored_files}")
    self._storage_model.sync_to_local(stored_files=request.job_playbook.stored_files)

    # when running workflows, the job_playbook is the workflow data..
    # we use the helper method to get the list of jobs from the workflow data
    workflow_data = request.job_playbook.job_playbook

    self._output.append(f"Loaded Jobs: {self._loaded_jobs}")
    


    workflow_jobs = workflow_data["workflow"]

    # this "could" re-queue the messages for another worker..
    # but currently it is doing all work for a workflow on the same worker
    # so that any files only need to be sync'd to one worker, this could change though.

    job_results = []

    # Iterate through each workflow job
    for workflow_job in workflow_jobs:
      # Iterate through each key-value pair in the workflow job
      for job_name, job_playbook in workflow_job.items():
        # Process each key-value pair here
        # make a new JobRequest, with the same details as our current workflow JobRequest.
        # but now running the actual workflow job with it's playbook data.
        new_request = JobRequest(
          job_name=job_name,
          origin=request.origin,
          job_playbook=job_playbook,
          response_dest=request.response_dest,
          message_id=request.message_id,
          ack_id=request.ack_id,
        )
        # we run it the same way the WorkerClient or HybridClient does..
        result = self._loaded_jobs[job_name].run(request=new_request)
        job_results.append(result)

        self._output.append(f"Job '{job_name}' returned result: {result}")

    self._console.print(f"Finished: {request.job_playbook.stored_files}")
    self._storage_model.cleanup_local_path(stored_files=request.job_playbook.stored_files)

    return job_results
