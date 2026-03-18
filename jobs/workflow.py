import sys
import os
import inspect

from dataclasses import dataclass, field
from ai_cli.job_queue import IJob, JobRequest, IJobResult, JobResult
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

  def run( self, request: JobRequest ) -> JobResult:
    self._output = ["WIP - No work done."]
    return JobResult( value="\n".join(self._output) )