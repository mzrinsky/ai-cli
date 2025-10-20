import argparse
import os
from rich.console import Console
from ai_cli.config import AppConfig
from ai_cli.job_queue import IQueue, JobQueueFactory
from ai_cli.playbook import PlaybookLoader
from ai_cli.worker import WorkerClient
from ai_cli.hybrid import HybridClient
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Optional
from io import TextIOWrapper

VERSION = "0.2.0"


class App:
  l33t_header = """[color(197)] ▄▄▄· ▪         ▄▄· ▄▄▌  ▪  [/color(197)]
[color(198)]▐█ ▀█ ██       ▐█ ▌▪██•  ██ [/color(198)]
[color(199)]▄█▀▀█ ▐█· ▐██  ██ ▄▄██▪  ▐█·[/color(199)]
[color(200)]▐█ ▪▐▌▐█▌      ▐███▌▐█▌▐▌▐█▌[/color(200)]
[color(201)] ▀  ▀ ▀▀▀      ·▀▀▀ .▀▀▀ ▀▀▀[/color(201)]
[color(249)]Created By:[/color(249)]     [color(255)]Matt Zrinsky[/color(255)]
"""
  config_paths = [ os.path.expanduser( '~/.config/ai-cli/' ) ]
  _playbook = None

  def __init__( self ):
    self.console = Console()
    pass

  def _init_queue( self ) -> IQueue:
    return JobQueueFactory.create_queue( queue_type=self._config.queue_backend, init_args=self._config.queue_backend_options )

  def run_client_role( self ):
    if self._config.verbose > 1:
      self.console.print( "Initializing queue ..." )
    self._queue = self._init_queue()
    if self._config.verbose > 1:
      self.console.print( f"Running in role '{self._config.role}' ..." )
    if self._config.role == 'hybrid':
      self._hybrid = HybridClient( app_config=self._config, queue=self._queue, console=self.console, playbook=self._playbook )
      self._hybrid.run()
    elif self._config.role == 'worker':
      self._worker = WorkerClient( app_config=self._config, queue=self._queue, console=self.console )
      self._worker.run()
    else:
      raise Exception( f"Unsupported client role '{self._config.role}'" )

  def _parse_args( self ) -> SimpleNamespace:
    parser = argparse.ArgumentParser(
      description='CLI tool to manage and run AI tasks using a task queue.',
      epilog='See: https://github.com/mzrinsky/langchain-demos',
    )
    parser.add_argument( '-V', '--version', action='version', version=VERSION )
    parser.add_argument( '-b', '--no-banner', action='store_true', help="Don't print the l33t banner." )
    parser.add_argument( '-v', '--verbose', action='count', default=0, help='Increase output verbosity on client (-vvvv for full info).' )
    parser.add_argument( '-c', '--config', required=False, type=argparse.FileType( 'r' ), help="A yaml application config file." )
    parser.add_argument( '-i', '--host-id', required=False, help='Name to use for host id' )
    parser.add_argument( '-r', '--role', choices=[ 'worker', 'logger', 'seeder', 'hybrid' ], required=False )
    parser.add_argument( '-p', '--playbook', required=False, type=argparse.FileType( 'r' ), help='Playbook to use' )
    parser.add_argument( '-j', '--job', required=False, help='Name of job to use default is invoke_llm' )
    parser.add_argument( '-s', '--system-prompt', required=False, help='System prompt to use with invoke_llm job' )
    parser.add_argument( '-u', '--user-prompt', required=False, help='User prompt to use with invoke_llm job' )
    parser.add_argument( '-a', '--attachment', required=False, help='Attach a document to give the LLM as context' )

    return parser.parse_args()

  def _validate_args( self, parsed_args: SimpleNamespace ):
    pass

  def _inject_config_into_playbook( self, config: AppConfig, playbook_data: dict ) -> Optional[ dict ]:
    """This method injects the prompt data from the config file into the playbook data.

    Note:
      This breaks some separation of concerns to increase usability?
      If this stays it should move to the AppConfig layer maybe?
      This might go away some day the use-cases here are not super clear at this point.. needs real-world testing."""
    if config.system_prompt:
      if "prompt" not in playbook_data:
        playbook_data[ "prompt" ] = { "system": config.system_prompt }
      elif "system" not in playbook_data[ "prompt" ]:
        playbook_data[ "prompt" ][ "system" ] = config.system_prompt
      else:
        if isinstance( playbook_data[ "prompt" ][ "system" ], list ):
          playbook_data[ "prompt" ][ "system" ].extend( config.system_prompt )
        elif isinstance( playbook_data[ "prompt" ][ "system" ], str ):
          playbook_data[ "prompt" ][ "system" ] = [ playbook_data[ "prompt" ][ "system" ], *config.system_prompt ]

    if "prompt" in playbook_data and "system" in playbook_data[ "prompt" ] and not isinstance( playbook_data[ "prompt" ][ "system" ], list ):
      playbook_data[ "prompt" ][ "system" ] = [ playbook_data[ "prompt" ][ "system" ] ]

    if config.user_prompt:
      if "prompt" not in playbook_data:
        playbook_data[ "prompt" ] = { "user": config.user_prompt }
      elif "user" not in playbook_data[ "prompt" ]:
        playbook_data[ "prompt" ][ "user" ] = config.user_prompt
      else:
        if isinstance( playbook_data[ "prompt" ][ "user" ], list ):
          playbook_data[ "prompt" ][ "user" ].extend( config.user_prompt )
        elif isinstance( playbook_data[ "prompt" ][ "user" ], str ):
          playbook_data[ "prompt" ][ "user" ] = [ playbook_data[ "prompt" ][ "user" ], *config.user_prompt ]

    if "prompt" in playbook_data and "user" in playbook_data[ "prompt" ] and not isinstance( playbook_data[ "prompt" ][ "user" ], list ):
      playbook_data[ "prompt" ][ "user" ] = [ playbook_data[ "prompt" ][ "user" ] ]

    # inject any attachments from the config into the playbook..
    # this is bridging a gap between command line args and the playbooks.. (for convenience..)
    if config.attachments:
      if "docs" not in playbook_data:
        playbook_data["docs"] = config.attachments
      else:
        playbook_data["docs"].extend( config.attachments )

    return playbook_data

  def _lookup_config_file( self, parsed_args: SimpleNamespace ) -> Optional[ TextIOWrapper ]:
    if parsed_args.config:
      return parsed_args.config
    else:
      for config_path in self.config_paths:
        config_file = os.path.join( config_path, 'default.yaml' )
        if os.path.exists( config_file ):
          return open( config_file, 'r' )

  def _load_config( self, config_file: Optional[ TextIOWrapper ], parsed_args: SimpleNamespace ) -> AppConfig:
    """Load any config files, apply any command line args, and return an AppConfig"""
    app_config = AppConfig()
    app_config.from_yaml( config_file=config_file, cmd_args=parsed_args )
    return app_config

  def run( self ):
    try:
      # this bootstrapping process is not the best.. but it's fine for now..
      # it would be better if the debug logging could happen on _lookup_config_file so it says what files it tries to load.
      parsed_args = self._parse_args()
      self._validate_args( parsed_args )
      config_file = self._lookup_config_file( parsed_args=parsed_args )
      self._config = self._load_config( config_file=config_file, parsed_args=parsed_args )
      if not self._config.no_banner:
        self.console.print( self.l33t_header )
      if self._config.config_file and self._config.verbose:
        self.console.print( f"Loading config file '{self._config.config_file.name}' ..." )
      elif self._config.verbose:
        self.console.print( f"No config file specified, and default not found." )
      if self._config.verbose > 3:
        self.console.print( self._config )
      if ( self._config.playbook_file ):
        if self._config.verbose:
          if isinstance( self._config.playbook_file, TextIOWrapper ):
            filename = self._config.playbook_file.name
          else:
            filename = self._config.playbook_file
          self.console.print( f"Loading playbook file '{filename}' ..." )
        self._playbook = PlaybookLoader.load_playbook( playbook_file=self._config.playbook_file )
        if self._playbook:
          self._playbook = self._inject_config_into_playbook( config=self._config, playbook_data=self._playbook )
      self.run_client_role()
    except KeyboardInterrupt as e:
      self.console.print( f"\nCaught keyboard interrupt. Exiting." )
      exit()
    except Exception as e:
      self.console.print_exception()
      exit( 1 )
