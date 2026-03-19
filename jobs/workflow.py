import sys
import os
import inspect

from dataclasses import dataclass, field
from ai_cli.job_queue import IJob, JobRequest, IJobResult, JobResult, JobLoader
from ai_cli.workflow import WorkflowLoader
from typing import Optional


class Workflow(IJob):
  _app_config: dict = {}
  _request: JobRequest
  _output: list[str] = []
  _errors: list[str] = []
  _console: any

  def __init__(self, app_config: dict, console: any):
    self._app_config = app_config
    self._console = console
    self._loader = JobLoader()
    # we want to get our own copy of the loaded jobs, excluding ourself (or it will be a circular reference)
    job_dir = os.path.dirname(__file__)
    self._loaded_jobs = self._loader.load_jobs(
      job_dir=job_dir, app_config=app_config, console=self._console, exclude=["workflow"]
    )
    if app_config.verbose > 3:
      console.print(f"Loaded Jobs is now: {self._loaded_jobs}")

  def run(self, request: JobRequest) -> IJobResult:
    # when running workflows, the job_playbook is the workflow data..
    # we use the helper method to get the list of jobs from the workflow data
    workflow_data = request.job_playbook
    job_list = WorkflowLoader.get_jobs(workflow=workflow_data)

    self._output.append(f"Found workflow job list: {job_list}")
    self._output.append(f"Loaded Jobs: {self._loaded_jobs}")

    # run all the jobs in the workflow..
    for job_name in job_list:
      # this "could" re-queue the messages for another worker..
      # but currently it is doing all work for a workflow on the same worker
      # so that any files only need to be sync'd to one worker, this could change though.

      # make a new JobRequest, with the same details as our current workflow JobRequest.
      # but now running the actual workflow job with it's playbook data.
      new_request = JobRequest(
        job_name=job_name,
        origin=request.origin,
        job_playbook=workflow_data[job_name],
        response_dest=request.response_dest,
        message_id=request.message_id,
        ack_id=request.ack_id,
      )
      # we run it the same way the WorkerClient or HybridClient does..
      result = self._loaded_jobs[job_name].run(request=new_request)
      # Here there needs to be a better system..
      # I think it needs to return a list of JobResults.. so something needs a little refactor in the response pipeline.
      self._output.append(f"Job '{job_name}' returned result: {result}")

    # for now we just return a new JobResult with all the output combined so we can see it worked.
    return JobResult(value="\n".join(self._output))
