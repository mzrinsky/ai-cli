import os
from io import TextIOWrapper
from typing import Optional
import yaml
import yaml_include


class WorkflowLoader:
  @staticmethod
  def load(workflow_file: Optional[TextIOWrapper | str] = None) -> dict:
    """Load a YAML workflow file and return the parsed data."""
    if isinstance(workflow_file, str):
      # print( f"PlaybookLoader.load_playbook -> Loading from str {playbook_file}" )
      base_path = os.path.dirname(workflow_file)
      yaml.add_constructor("!Inc", yaml_include.Constructor(base_dir=base_path), Loader=yaml.SafeLoader)
      with open(workflow_file, "r") as stream:
        workflow_data = yaml.safe_load(stream)
        return workflow_data
    elif isinstance(workflow_file, TextIOWrapper):
      # print( f"PlaybookLoader.load_playbook -> Loading from TextIOWrapper {playbook_file}" )
      base_path = os.path.dirname(os.path.abspath(workflow_file.name))
      yaml.add_constructor("!Inc", yaml_include.Constructor(base_dir=base_path), Loader=yaml.SafeLoader)
      workflow_data = yaml.safe_load(stream=workflow_file)
      return workflow_data
    else:
      raise ValueError("Expected workflow_file to be str or TextIOWrapper.")
