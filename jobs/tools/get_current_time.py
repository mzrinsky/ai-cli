from datetime import datetime 
from langchain_core.tools import tool

@tool( response_format = "content" )
def get_current_time():
  """Get the current time."""
  return datetime.now().strftime( "%I:%M %p" )