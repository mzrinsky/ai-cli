
from ai_cli.app import AppConfig
from ai_cli.job_queue import JobRequest

class OutputFormatter():

  def __init__( self, app_config: AppConfig ):
    self._app_config = app_config

  def format( self, object: any ) -> str:
    """Handle formatting the output of results."""
    # print( object )
    if hasattr( object, "type" ) and object.type == "llm_result":
      # format llm_result for display in the terminal
      output = ""
      if self._app_config.verbose:
        output = "- **Response**: "
      for message in object.state[ "messages" ]:
        if message.type == "ai":
          output = output + message.content
      return output
    elif isinstance( object, JobRequest ):
      # format JobRequest for display in the terminal
      output = ""
      if object.job_name == "invoke_llm":
        output = output + "**Job**: " + object.job_name + "\n- **System Prompt**: " + str( ", " ).join(
          object.job_playbook[ "prompt" ][ "system" ]
        ) + "\n- **User Prompt**: " + str( ", " ).join( object.job_playbook[ "prompt" ][ "user" ] ) + "\n"
      else:
        output = str(object)
      return output
    else:
      # this serves as a translation layer, on the client side, from JobResults to strings of output for the terminal
      return str( object )
