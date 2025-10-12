import subprocess
from langchain_core.tools import tool

@tool(response_format="content")
def scan_nmap(ip_or_hostname: str):
    """Scan open ports on a target IP using nmap."""
    result = subprocess.run(["nmap", "-p-", ip_or_hostname], capture_output=True, text=True)
    return result.stdout
