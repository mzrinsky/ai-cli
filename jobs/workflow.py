import sys
import os
import inspect

from dataclasses import dataclass, field
from ai_cli.job_queue import IJob, JobRequest, IJobResult, JobResult, JobLoader
from ai_cli.workflow import WorkflowLoader
from typing import Optional


@dataclass( frozen=True )
class LlmResult( IJobResult ):
  """A custom JobResult implementation that returns the llm state"""
  type: str = 'llm_result'
  value: Optional[ str ] = None
  error: Optional[ str ] = None
  state: list = field( default_factory=list )


class Workflow( IJob ):
  _app_config: dict = {}
  _request: JobRequest
  _output: list[ str ] = []
  _errors: list[ str ] = []
  _console: any

  def __init__(self, app_config: dict, console: any):
    self._app_config = app_config
    self._console = console
    self._loader = JobLoader()
    job_dir = os.path.dirname( __file__ )
    self._loaded_jobs = self._loader.load_jobs( job_dir=job_dir, app_config=app_config, console=self._console, exclude=["workflow"] )
    if app_config.verbose > 3:
      console.print(f"Loaded Jobs is now: {self._loaded_jobs}")

  def run( self, request: JobRequest ) -> JobResult:
    workflow_data = request.job_playbook
    job_list = WorkflowLoader.get_jobs(workflow=workflow_data)
    self._output.append(f"Found workflow job list: {job_list}")
    self._output.append(f"Loaded Jobs: {self._loaded_jobs}")

    return JobResult( value="\n".join(self._output) )
