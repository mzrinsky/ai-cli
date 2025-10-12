from datetime import datetime 
from langchain_core.tools import tool

@tool( response_format = "content" )
def get_current_date():
  """Get the current date."""
  return datetime.now().strftime( "%Y-%m-%d" )