import subprocess
import sys
from langchain_core.tools import tool

@tool(response_format="content")
def ping(host_or_ip: str):
    """Ping an ip address or hostname to determine it's availability"""
    param = ['-n', '1'] if sys.platform == 'win32' else ['-c', '1']
    response = subprocess.run(['ping'] + param + [host_or_ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return f"{str(response.stdout)}{str(response.stderr)}"
