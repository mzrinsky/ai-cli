import asyncio
import glob
import sys
import os
import inspect

from dataclasses import dataclass, field
from ai_cli.job_queue import IJob, JobRequest, IJobResult, JobResult
from typing import Optional
import importlib
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


@dataclass( frozen=True )
class LlmResult( IJobResult ):
  """A custom JobResult implementation that returns the llm state"""
  type: str = 'llm_result'
  value: Optional[ str ] = None
  error: Optional[ str ] = None
  state: list = field( default_factory=list )


class ChatModelFactory:
  """Factory for creating instances of LangChain chat models."""

  @staticmethod
  def create_llm( provider: str, init_args: dict ) -> BaseChatModel:
    """Create a BaseChatModel instance from a given provider and init_args."""
    if provider == 'ollama':
      from langchain_ollama import ChatOllama
      return ChatOllama( **init_args )

    raise ValueError( f"Unknown chat model provider: {provider}" )


class InvokeLlm( IJob ):

  _app_config: dict = {}
  _request: JobRequest
  _output: list[ str ] = []
  _errors: list[ str ] = []
  _local_tools: list
  _mcp_tools: list = []
  _mcp_client: Optional[ MultiServerMCPClient ] = None
  _message_state: dict = {}
  _state_history: list = []
  _console: any

  def __init__(self, app_config: dict, console: any):
    self._app_config = app_config
    self._console = console

  def _load_local_tool( self, tool_name: str, code_path: str ):
    spec = importlib.util.spec_from_file_location( tool_name, code_path )
    dynamic_tools = importlib.util.module_from_spec( spec )
    spec.loader.exec_module( dynamic_tools )
    new_tool = getattr( dynamic_tools, tool_name )
    return new_tool

  def _tool_exists( self, tools: list, tool_name: str, tool_description: str ) -> bool:
    for tool in tools:
      if tool.name == tool_name and tool.description == tool_description:
        return True
    return False

  def _load_local_tools( self ) -> Optional[ list ]:
    if "tools" not in self._request.job_playbook:
      return None

    try:
      self._local_tools = []
      for tool_def in self._request.job_playbook[ "tools" ]:
        if self._app_config.verbose > 3:
          self._console.print( tool_def )
        if "glob" in tool_def:
          # tool_path = os.path.dirname( __file__ )
          tool_path = os.path.dirname( os.path.abspath( inspect.getfile( InvokeLlm ) ) )
          if self._app_config.verbose > 2:
            if self._console:
              self._console.print( f"Using tool path: {tool_path}" )
          self._output.append( f"Using tool path: {tool_path}" )
          for filename in glob.glob( os.path.join( tool_path, tool_def[ "glob" ] ) ):
            tool_name = os.path.splitext( os.path.basename( filename ) )[ 0 ]
            self._output.append( f"Loading tool '{tool_name}' from glob: {filename}" )
            local_tool = self._load_local_tool( tool_name=tool_name, code_path=filename )
            if local_tool and not self._tool_exists( tools=self._local_tools, tool_name=local_tool.name, tool_description=local_tool.description ):
              # if we loaded the tool and it's not already tracked..
              self._local_tools.append( local_tool )
        elif "name" in tool_def and "path" in tool_def:
          # we need to try to load a single tool..
          tool_path = os.path.join( os.path.dirname( os.path.abspath( inspect.getfile( InvokeLlm ) ) ), tool_def[ "path" ] )
          if self._app_config.verbose > 1:
            self._console.print( f"Using tool path: {tool_path}" )
          self._output.append( f"Using tool path: {tool_path}" )

          local_tool = self._load_local_tool( tool_name=tool_def[ "name" ], code_path=tool_path )
          if local_tool and not self._tool_exists( tools=self._local_tools, tool_name=local_tool.name, tool_description=local_tool.description ):
            # if we loaded the tool and it's not already tracked..
            self._local_tools.append( local_tool )
        else:
          raise Exception( "Tool definition needs to have name and path or glob." )
      if self._app_config.verbose > 3:
        if (self._console):
          self._console.print( f"{self._local_tools}" )
      return self._local_tools
    except Exception as e:
      self._errors.append( str( e ) )
      raise Exception( "Failed loading tool." )

  def _init_mcp( self ) -> Optional[ MultiServerMCPClient ]:
    if "mcp" in self._request.job_playbook[ "mcp" ]:
      self._mcp_client = MultiServerMCPClient( self._request.job_playbook[ "mcp" ] )

  def _load_mcp_tools( self ) -> Optional[ list ]:
    if not self._mcp_client:
      return None
    self._mcp_tools = asyncio.run( self._mcp_client.get_tools() )
    if self._app_config.verbose > 3:
      self._console.print( str( self._mcp_tools ) )
    return self._mcp_tools

  def _reload_available_tools( self ) -> Optional[ list ]:
    """Return the list of available tools by combining the list of local_tools with the list of mcp_tools."""
    self._available_tools = []
    if self._mcp_tools:
      self._available_tools = self._mcp_tools

    if self._local_tools:
      if len( self._available_tools ):
        self._available_tools.extend( self._local_tools )
      else:
        self._available_tools = self._local_tools

    return self._available_tools

  def _load_llm( self ) -> BaseChatModel:
    """Load an LLM using the ChatModelFactory"""
    self._llm = ChatModelFactory.create_llm(
      provider=self._request.job_playbook[ "model" ][ "provider" ], init_args=self._request.job_playbook[ "model" ][ "init_args" ]
    )

  def run_llm_prompt( self, message_state: MessagesState ) -> MessagesState:
    """Lang Graph Node to run llm prompt"""
    # we assume tools are already bound.
    # loop = asyncio.get_event_loop()
    # response = loop.run_until_complete(llm.ainvoke(message_state["messages"]))
    # response = asyncio.run(llm.ainvoke(message_state["messages"]))
    response = self._llm.invoke( message_state[ "messages" ] )
    return { "messages": [ response ] }

  def run_llm_tool_response_hook( self, message_state: MessagesState ) -> MessagesState:
    """Lang Graph Node to run llm prompt with tool response"""
    # we assume tools are already bound.
    # loop = asyncio.get_event_loop()
    # response = loop.run_until_complete(llm.ainvoke(message_state["messages"]))
    # response = asyncio.run(llm.ainvoke(message_state["messages"]))
    response = self._llm.invoke( message_state[ "messages" ] )
    return { "messages": [ response ] }

  def build_tool_llm_state_graph( self ) -> StateGraph:
    """Build a state graph for running llm models with tools"""
    self._state_graph = StateGraph( MessagesState )
    self._state_graph.add_node( "run_llm_prompt", self.run_llm_prompt )
    self._state_graph.add_node( ToolNode( name="run_tools", tools=self._available_tools ) )
    self._state_graph.add_node( "run_llm_tool_response_hook", self.run_llm_tool_response_hook )

    self._state_graph.set_entry_point( "run_llm_prompt" )
    self._state_graph.add_conditional_edges(
      "run_llm_prompt",
      tools_condition,
      {
      END: END,
      "tools": "run_tools"
      },
    )
    self._state_graph.add_edge( "run_tools", "run_llm_tool_response_hook" )
    self._state_graph.add_conditional_edges(
      "run_llm_tool_response_hook",
      tools_condition,
      {
      END: END,
      "tools": "run_tools"
      },
    )
    self._state_graph.add_edge( "run_llm_tool_response_hook", END )

  def _generate_system_prompt( self ) -> str:
    system_prompt = ""
    # start with prompt from the playbook if any
    if "system" in self._request.job_playbook[ "prompt" ]:
      system_prompt_content = self._request.job_playbook[ "prompt" ][ "system" ]
      if isinstance( system_prompt_content, list ):
        system_prompt_content = "\n".join( system_prompt_content )
      if system_prompt:
        system_prompt = system_prompt + "\n" + system_prompt_content
      else:
        system_prompt = system_prompt_content
    return system_prompt

  def _generate_user_prompt( self ) -> str:
    user_prompt = ""
    # start with prompt from the playbook if any
    if "user" in self._request.job_playbook[ "prompt" ]:
      if isinstance(self._request.job_playbook["prompt"]["user"], list):
        user_prompt = "\n".join(self._request.job_playbook["prompt"]["user"])
      else:
        user_prompt = self._request.job_playbook["prompt"]["user"]
    # append any prompt from local config file.. ?
    # if "prompt" in app_config and app_config[ "prompt" ]:
    #   if user_prompt:
    #     user_prompt = user_prompt + " " + app_config[ "prompt" ]
    #   else:
    #     user_prompt = app_config[ "prompt" ]
    return user_prompt

  def run( self, request: JobRequest ) -> JobResult:
    """job_queue.IJob implementation that can invoke a tool calling, mcp supporting llm using LangChain and LangGraph."""

    try:
      self._request = request
      # attempt to load requested local tools
      self._load_local_tools()
      # attempt to load mcp client
      self._init_mcp()
      # attempt to load mcp tools
      self._load_mcp_tools()
      # build list of all available tools.
      self._reload_available_tools()
      if self._app_config.verbose > 1:
        self._console.print( f"Available Tools: {self._available_tools}" )
      # load an llm
      self._load_llm()
      self._llm = self._llm.bind_tools( tools=self._available_tools )
      # we have all the bits at this point to build the state graph and compile it..
      self.build_tool_llm_state_graph()
      self._graph = self._state_graph.compile()

      # get the prompt etc together..
      self._message_state = {
        "messages": [ {
        "role": "system",
        "content": self._generate_system_prompt()
        }, {
        "role": "user",
        "content": self._generate_user_prompt()
        } ]
      }

      # run the compiled state graph..
      for step in self._graph.stream( input=self._message_state, stream_mode="values" ):
        if self._app_config.verbose > 3:
          self._console.print( step )
        self._state_history = step
        #self._output.append( str( step ) )
        last_message = step[ "messages" ][ -1 ]
        if last_message.type == 'ai':
          self._output.append( last_message.content )

      return LlmResult( value=str( "\n" ).join( self._output ), state=self._state_history )

    except Exception as e:
      import traceback
      self._errors.append( str( e ) )
      self._errors.append( traceback.format_exc() )

    # do all the work, and return a JobResult.
    #print( f"InvokeLlm Job Ran {request}" )

    return JobResult( error=str( "\n" ).join( self._errors ), value="\n".join(self._output) )
