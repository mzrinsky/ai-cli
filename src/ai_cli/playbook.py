import os
from io import TextIOWrapper
from typing import Optional
import yaml
import yaml_include


class PlaybookLoader():

  @staticmethod
  def load_playbook( playbook_file: Optional[ TextIOWrapper | str ] = None ):
    """Load a YAML playbook file and return the parsed data."""
    if isinstance( playbook_file, str ):
      #print( f"PlaybookLoader.load_playbook -> Loading from str {playbook_file}" )
      base_path = os.path.dirname( playbook_file )
      yaml.add_constructor( '!Inc', yaml_include.Constructor( base_dir=base_path ), Loader=yaml.SafeLoader )
      with open( playbook_file, 'r' ) as stream:
        playbook_data = yaml.safe_load( stream )
        return playbook_data
    elif isinstance( playbook_file, TextIOWrapper ):
      #print( f"PlaybookLoader.load_playbook -> Loading from TextIOWrapper {playbook_file}" )
      base_path = os.path.dirname( os.path.abspath( playbook_file.name ) )
      yaml.add_constructor( '!Inc', yaml_include.Constructor( base_dir=base_path ), Loader=yaml.SafeLoader )
      playbook_data = yaml.safe_load( stream=playbook_file )
      return playbook_data
    else:
      raise Exception( "Unsupported format." )
