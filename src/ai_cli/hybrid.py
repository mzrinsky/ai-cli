from ai_cli.app import AppConfig
from ai_cli.job_queue import JobLoader, JobConsumer, ResponseConsumer, JobSeeder, IQueue, JobRequest, JobResponse, JobResult
from ai_cli.util import OutputFormatter
import os
from rich.console import Console
from rich.markdown import Markdown
from socket import gethostname
from typing import Optional
import warnings


class HybridClient():

  _outstanding_jobs = []

  def __init__( self, app_config: AppConfig, queue: IQueue, console: Console, playbook: Optional[ dict ] = None ):
    self.console = console
    self._app_config = app_config
    self._playbook = playbook
    self._loader = JobLoader()
    self._queue = queue
    self._outout_formatter = OutputFormatter( app_config=self._app_config )
    if app_config.worker or app_config.wait_for_result:
      job_dir = os.path.join( os.path.dirname( __file__ ), '..', '..', 'jobs' )
      self._loaded_jobs = self._loader.load_jobs( job_dir=job_dir, app_config=app_config, console=self.console )
    if app_config.worker:
      self._job_consumer = JobConsumer(
        supported_jobs=list( self._loaded_jobs.keys() ), queue=self._queue, request_callback=self._dispatch_request, host_id=gethostname()
      )
    if app_config.wait_for_result:
      self._response_consumer = ResponseConsumer(
        queue=self._queue, supported_jobs=list( self._loaded_jobs.keys() ), response_callback=self._dispatch_response, host_id=gethostname()
      )
    self._job_seeder = JobSeeder( queue=self._queue )

  def _mark_job_complete( self, response: JobResponse ):
    for job in list( self._outstanding_jobs ):
      if str( job.message_id ) == response.request_message_id:
        self._outstanding_jobs.remove( job )
        break

  def _dispatch_request( self, request: JobRequest ):
    if self._app_config.verbose > 3:
      self.console.print( f"HybridClient._dispatch_request -> {request}" )
    if request.job_name in self._loaded_jobs:
      result = self._loaded_jobs[ request.job_name ].run( request=request )
      self._job_consumer.respond_to_request( request=request, result=result )
    else:
      warnings.warn( f"No loaded jobs match job request, queues may be misconfigured." )
      # TODO: it's safer to dead-letter this right away..?
      self._job_consumer.nack_request( request=request )

  def _dispatch_response( self, response: JobResponse ):
    if self._app_config.verbose > 3:
      self.console.print( f"HybridClient._dispatch_response : {response}" )
    # thanks to using pickle and wrapping the result in a response,
    # the result will be automatically thawed into any custom result type returned by the job.
    output = self._outout_formatter.format( response.result )
    self.console.print( Markdown( output ) )
    self._response_consumer.ack_response( response=response )
    self._mark_job_complete( response=response )
    if not len( self._outstanding_jobs ):
      if self._app_config.verbose:
        self.console.print( "All jobs complete, exiting." )
      exit()

  def run( self ):
    if self._app_config.verbose > 1:
      self.console.print( "Hybrid Client Running." )
    if self._app_config.job and self._playbook:
      if self._app_config.verbose > 1:
        self.console.print( f"HybridClient -> sending job request {self._app_config.job}" )
      # any documents need to get processed here.. and attached at the request level..
      # this step ensures the documents are moved to some sort of shared storage so they are available to any job consumers.
      new_job = JobRequest( job_name=self._app_config.job, origin=gethostname(), job_playbook=self._playbook, attachments=self._app_config.attachments )
      self._outstanding_jobs.append( new_job )
      if self._app_config.verbose:
        self.console.print( f"Seeding job '{new_job.job_name}' to queue ..." )
        self.console.print( Markdown( self._outout_formatter.format( object=new_job ) ) )
      self._job_seeder.send_request( request=new_job )
    if self._app_config.wait_for_result and self._app_config.worker:
      if self._app_config.verbose:
        self.console.print( "Waiting for job result ..." )
      self._job_consumer.start_consuming()
