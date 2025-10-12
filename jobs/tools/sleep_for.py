from time import sleep
from langchain_core.tools import tool

@tool(response_format="content")
def sleep_for(seconds: int):
    """Sleeps for a given number of seconds."""
    sleep(seconds)
    return f"Slept for {seconds} seconds"