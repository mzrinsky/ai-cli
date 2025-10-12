from dataclasses import dataclass, field
from typing import Optional
from types import SimpleNamespace
from io import TextIOWrapper
from socket import gethostname
import yaml
import warnings


@dataclass
class AppConfig:
  # the verbosity level for the client ( from the command line or config file. )
  verbose: int = 0
  # The host_id for this client
  host_id: str = field( default_factory=gethostname )
  # the role to assume on this client
  role: str = 'hybrid'
  # the queue type to use
  queue_backend: str = 'none'
  # any init args to pass to the queue
  queue_backend_options: Optional[ dict ] = None
  # a job to seed (publish) upon starting
  job: Optional[ str ] = 'invoke_llm'
  # control hybrid client behavior
  wait_for_result: bool = True  # wait for results (Result Consumer)
  worker: bool = True  # work on jobs locally (Job Consumer)
  # the playbook file containing details for the job invocation
  playbook_file: Optional[ str | TextIOWrapper ] = None
  # contains system prompts from the config file + command line
  system_prompt: Optional[ list[ str ] ] = None
  # contains user prompts from the config file + command line
  user_prompt: Optional[ list[ str ] ] = None
  # the config file that was loaded with app-level config options
  config_file: Optional[ str | TextIOWrapper ] = None
  no_banner: bool = False

  def from_yaml( self, config_file: Optional[ str | TextIOWrapper ] = None, cmd_args: Optional[ SimpleNamespace ] = None ):

    # load items from config file..
    if isinstance( config_file, str ):
      with open( config_file, 'r' ) as file:
        config_data = yaml.safe_load( file )
    elif isinstance( config_file, TextIOWrapper ):
      config_data = yaml.safe_load( config_file )
    else:
      config_data = {}

    if self.config_file != config_file:
      self.config_file = config_file

    # process config file items..
    for key, value in config_data.items():
      mapped_key = key
      if key == "playbook":
        mapped_key = "playbook_file"
      elif key == "prompt":
        new_system_prompt = value.get( "system", self.system_prompt )
        if new_system_prompt.strip():
          if (self.system_prompt):
            self.system_prompt.append( new_system_prompt )
          else:
            self.system_prompt = [ new_system_prompt ]

        new_user_prompt = value.get( "user", self.user_prompt )
        if new_user_prompt.strip():
          if self.user_prompt:
            self.user_prompt.append( new_user_prompt )
          else:
            self.user_prompt = [ new_user_prompt ]

        continue
      if hasattr( self, mapped_key ) and key != "config_file":
        setattr( self, mapped_key, value )

    # set defaults from cmd_args..
    if cmd_args:
      if isinstance(cmd_args.system_prompt, str) and cmd_args.system_prompt.strip():
        if self.system_prompt:
          self.system_prompt.append( cmd_args.system_prompt )
        else:
          self.system_prompt = [ cmd_args.system_prompt ]

      if isinstance(cmd_args.user_prompt, str) and cmd_args.user_prompt.strip():
        if self.user_prompt:
          self.user_prompt.append( cmd_args.user_prompt )
        else:
          self.user_prompt = [ cmd_args.user_prompt ]

      if cmd_args.playbook:
        self.playbook_file = cmd_args.playbook

      if cmd_args.role:
        self.role = cmd_args.role

      if cmd_args.job:
        self.job = cmd_args.job

      if cmd_args.host_id:
        self.host_id = cmd_args.host_id

      if cmd_args.no_banner:
        self.no_banner = cmd_args.no_banner

      if cmd_args.verbose:
        self.verbose = cmd_args.verbose

    if self.queue_backend == 'none' and self.worker == False:
      raise ValueError(
        "Cannot run a local-only non-shared in-memory queue with no worker, if you do not want a local worker use rabbitmq queue type, if you do not want rabbitmq you need to use local worker."
      )
