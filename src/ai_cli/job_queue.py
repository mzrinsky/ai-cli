from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol
from ai_cli.config import AppConfig
import json
import sys
import os
import re
import pickle
import base64
from importlib.util import spec_from_file_location, module_from_spec
from datetime import datetime
from uuid import uuid4
from rich.console import Console


@dataclass(frozen=True)
class IJobRequest(ABC):
  """Interface for JobRequest implementations."""

  job_name: str
  origin: str
  job_playbook: dict
  response_dest: Optional[str]
  message_id: str
  ack_id: Optional[str]


@dataclass(frozen=True)
class IJobResult(ABC):
  """Interface for job queue job results."""

  type: str
  value: Optional[str]
  error: Optional[str]


@dataclass(frozen=True)
class IJobResponse(ABC):
  """Interface for job queue job request responses."""

  job_name: str
  request_message_id: str
  request_origin: str
  response_origin: str
  response_dest: Optional[str]
  result: list[IJobResult]
  message_id: str
  ack_id: Optional[str]


@dataclass(frozen=True)
class IQueueMessage(ABC):
  """Interface for queue messages."""

  type: str
  context: str
  body: str
  created: str
  dest_queue: Optional[str]
  src_queue: Optional[str]
  reply_to: Optional[str]
  message_id: str
  ack_id: Optional[str]
  origin_host_id: Optional[str]


class QueueConsumeCallback(Protocol):
  def __call__(self, message: IQueueMessage) -> None:
    pass


class IQueue(ABC):
  """Interface for the job queue Abstracts the underlying queue storage."""

  @abstractmethod
  def consume_queues(self, queue_names: list[str], message_callback: QueueConsumeCallback):
    """Register a list of queues from which to consume messages."""
    pass

  @abstractmethod
  def start_consuming(self):
    """Start consuming messages from the registered queues."""
    pass

  @abstractmethod
  def stop_consuming(self):
    """Stop consuming messages."""
    pass

  @abstractmethod
  def send_message(self, message: IQueueMessage):
    pass

  @abstractmethod
  def ack_message(self, message: Optional[IQueueMessage] = None, ack_id: Optional[str] = None):
    pass

  @abstractmethod
  def nack_message(self, message: Optional[IQueueMessage] = None, ack_id: Optional[str] = None):
    pass


class IJobSeeder(ABC):
  """Interface for job seeders, Translates the JobRequests into JobQueue items."""

  @abstractmethod
  def __init__(self, queue: IQueue):
    pass

  @abstractmethod
  def send_request(self, request: IJobRequest):
    pass


class JobConsumerCallback(Protocol):
  def __call__(self, request: IJobRequest) -> None:
    pass


class IJobConsumer(ABC):
  """Interface for job consumers, consumes jobs for workers to work on."""

  @abstractmethod
  def __init__(
    self,
    supported_jobs: list[str],
    queue: IQueue,
    request_callback: JobConsumerCallback,
    host_id: str,
  ):
    """Takes a list of supported_jobs this consumer should consume messages for."""
    pass

  @abstractmethod
  def ack_request(self, request: IJobRequest):
    """Mark the request as complete"""
    pass

  @abstractmethod
  def nack_request(self, request: IJobRequest):
    """Mark the request as not complete."""
    pass

  @abstractmethod
  def start_consuming(self):
    """When called this method will block and request_callback will be called when there are new requests to consume."""
    pass

  @abstractmethod
  def stop_consuming(self):
    pass


class IResponseSeeder(ABC):
  """Interface for response seeders, wrapper between JobQueue and JobResponse sending"""

  @abstractmethod
  def __init__(self, queue: IQueue):
    pass

  @abstractmethod
  def respond_to_request(self, request: IJobRequest, result: list[IJobResult]):
    pass

  @abstractmethod
  def create_response(self, request: IJobRequest, result: list[IJobResult]) -> IJobResponse:
    pass

  @abstractmethod
  def send_response(self, response: IJobResponse):
    pass


class ResponseConsumerCallback(Protocol):
  def __call__(self, response: IJobResponse) -> None:
    pass


class IResponseConsumer(ABC):
  """Interface for response consumers, consumes responses from workers."""

  @abstractmethod
  def __init__(
    self,
    supported_jobs: list[str],
    queue: IQueue,
    response_callback: ResponseConsumerCallback,
    host_id: str,
  ):
    """Takes a list of supported_jobs this consumer should consume response messages for."""
    pass

  @abstractmethod
  def ack_response(self, response: IJobResponse):
    """Mark the request as complete"""
    pass

  @abstractmethod
  def nack_response(self, response: IJobResponse):
    """Mark the request as not complete."""
    pass

  @abstractmethod
  def start_consuming(self):
    """When called this method will block and request_callback will be called when there are new requests to consume."""
    pass

  @abstractmethod
  def stop_consuming(self):
    pass


class IJob(ABC):
  """Interface for job queue jobs."""

  @abstractmethod
  def __init__(self, app_config: AppConfig, console: Console):
    """The init method gets a copy of the locally running app config to determine things like log output location and verbosity"""
    pass

  @abstractmethod
  def run(self, request: IJobRequest) -> list[IJobResult]:
    """The run method is expected to execute any job logic specified in the IJobRequest and return an IJobResult"""
    pass


class JobLoader:
  """A default JobLoader implementation that loads python jobs from disk that implement the IJob interface."""

  @staticmethod
  def load_jobs(
    job_dir: str, app_config: AppConfig, console: Console, exclude: list[str] = []
  ) -> dict[str, "IJob"]:
    # try to find a job directory..
    if not os.path.exists(job_dir):
      if not os.path.isabs(job_dir):
        alt_dir = os.path.join(os.getcwd(), job_dir)
        if not os.path.exists(alt_dir):
          raise FileNotFoundError(f"The directory '{job_dir}' and '{alt_dir}' are not found.")
        else:
          job_dir = alt_dir
      else:
        raise FileNotFoundError(f"The directory '{job_dir}' is not found.")

    if app_config.verbose > 3:
      console.print(f"Loading jobs from '{job_dir}'")
    # load any .py files we find in job_dir
    jobs = {}
    for filename in os.listdir(job_dir):
      if filename.endswith(".py") and not filename.endswith("__init__.py"):
        filepath = os.path.join(job_dir, filename)
        module_name = os.path.basename(filename)[:-3]
        already_loaded = module_name in sys.modules
        if app_config.verbose > 3:
          console.print(f"Found module: '{module_name}' Already Loaded: {already_loaded}")

        try:
          module = None
          if not already_loaded:
            spec = spec_from_file_location(module_name, filepath)
            module = module_from_spec(spec) # type: ignore
            spec.loader.exec_module(module) # type: ignore
            sys.modules[module_name] = module
            if app_config.verbose > 3:
              console.print(f"Loaded module: '{module_name}' from '{filepath}'")
          else:
            module = sys.modules[module_name]

          if app_config.verbose > 3:
            if module_name in exclude:
              console.print(f"Skipping module: '{module_name}' Reason: in exclude list.")

          if module_name not in exclude:
            # convert filename into classname
            class_name = JobLoader._to_camel_case(module_name)
            if hasattr(module, class_name):
              # if the loaded file class matches what we expect, and is an instance of IJob
              cls = getattr(module, class_name)
              if issubclass(cls, IJob) and cls != IJob:
                # keep track of this job instance
                jobs[module_name] = cls(app_config=app_config, console=console)
            else:
              if app_config.verbose > 3:
                console.print(f"Module '{module}' lacks attr '{class_name}'")
              if not already_loaded:
                # unregister this module, as it's not a job
                del sys.modules[module_name]

        except Exception as e:
          if not already_loaded:
            del sys.modules[module_name]
          raise Exception(f"Error Loading Job {module_name}: {str(e)}")

    return jobs

  @staticmethod
  def _to_camel_case(snake_str: str) -> str:
    components = re.split(r"[_-]", snake_str)
    return components[0].title() + "".join(x.title() for x in components[1:])


@dataclass(frozen=True)
class QueueMessage(IQueueMessage):
  """A default implementation of the IQueueMessage interface."""

  body: str
  type: str
  context: str
  created: str = field(default_factory=lambda: datetime.now().isoformat())
  message_id: str = field(default_factory=lambda: str(uuid4()))
  ack_id: Optional[str] = None
  reply_to: Optional[str] = None
  dest_queue: Optional[str] = None
  src_queue: Optional[str] = None
  origin_host_id: Optional[str] = None


@dataclass(frozen=True)
class JobRequest(IJobRequest):
  """A default JobRequest Implementation."""

  origin: str
  job_name: str
  job_playbook: dict
  message_id: str = field(default_factory=lambda: str(uuid4()))
  ack_id: Optional[str] = None
  response_dest: Optional[str] = None


@dataclass(frozen=True)
class JobResult(IJobResult):
  """A default job result implementation."""

  type: str = "result"
  value: Optional[str] = None
  error: Optional[str] = None


@dataclass(frozen=True)
class JobResponse(IJobResponse):
  """A default JobResponse Implementation."""

  request_message_id: str
  job_name: str
  request_origin: str
  response_origin: str
  result: list[IJobResult]
  response_dest: Optional[str]
  message_id: str = field(default_factory=lambda: str(uuid4()))
  ack_id: Optional[str] = None


class JobConsumer(IJobConsumer, IResponseSeeder):
  """Default JobConsumer implementation"""

  _supported_jobs: list[str]
  _queue: IQueue
  _request_callback: JobConsumerCallback
  _host_id: str

  def __init__(
    self,
    supported_jobs: list[str],
    queue: IQueue,
    request_callback: JobConsumerCallback,
    host_id: str,
    body_format: str = "pickle",
  ):
    self._host_id = host_id
    self._supported_jobs = supported_jobs
    self._queue = queue
    self._request_callback = request_callback
    self._body_format = body_format
    self._queue.consume_queues(
      queue_names=self._get_queue_names(), message_callback=self._handle_consume_callback
    )

  def _serialize_obj(self, obj: Any) -> Optional[str]:
    serialized_obj = None
    # this is all incredibly broken..
    # all serialization / deserialization here is broken..
    # it is working because pika is correctly handling the bytes type
    # and doing magic behind the scenes when using RabbitMQ..
    if self._body_format == "pickle":
      serialized_obj = pickle.dumps(obj)
    elif self._body_format == "json":
      serialized_obj = json.dumps(obj)
    else:
      raise Exception(f"Unsupported serialization format: {self._body_format}")
    return serialized_obj

  def _deserialize_obj(self, serialized_obj: str) -> Optional[Any]:
    deserialized_obj = None
    # all serialization / deserialization here is broken..
    # it is working because pika is correctly handling the bytes type
    # and doing magic behind the scenes when using RabbitMQ..
    if self._body_format == "pickle":
      deserialized_obj = pickle.loads(serialized_obj)
    elif self._body_format == "json":
      deserialized_obj = json.loads(serialized_obj)
    else:
      raise Exception(f"Unsupported deserialization format: {self._body_format}")
    return deserialized_obj

  def _get_queue_names(self) -> list[str]:
    queue_names = []
    for job_name in self._supported_jobs:
      queue_names.append(f"ai-cli.job.{job_name}")
    return queue_names

  def _handle_consume_callback(self, message: IQueueMessage):
    # this should de-serialize the message body..
    # when we get messages, create JobRequests from them, and call the consumer request callback.
    new_request = self._get_request(message=message)
    # print( f"JobConsumer._handle_consume_callback -> {new_request}" )
    self._request_callback(request=new_request)

  def _get_request(self, message: IQueueMessage) -> JobRequest:
    decoded_message_body = self._deserialize_obj(serialized_obj=message.body)
    return JobRequest(
      job_name=message.context,
      origin=message.origin_host_id if message.origin_host_id else "",
      job_playbook=decoded_message_body if decoded_message_body else {},
      message_id=message.reply_to
      if message.reply_to and message.reply_to != "None"
      else message.message_id,
      ack_id=message.ack_id,
    )

  def ack_request(self, request: IJobRequest):
    # turn the request into a QueueMessage and ack it.?
    # print( f"JobConsumer -> ack_request {request}" )
    self._queue.ack_message(ack_id=request.ack_id)

  def nack_request(self, request: IJobRequest):
    self._queue.ack_message(ack_id=request.ack_id)

  def respond_to_request(self, request: IJobRequest, result: list[IJobResult]):
    new_response = self.create_response(request=request, result=result)
    # print( f"JobConsumer.respond_to_request -> Request: {request}" )
    self.send_response(response=new_response)
    self.ack_request(request=request)

  def create_response(self, request: IJobRequest, result: list[IJobResult]) -> IJobResponse:
    if isinstance(result, IJobResult):
      result = [result]

    if not isinstance(result, list):
      raise TypeError("'result' is expected to be a list of IJobResult objects.")

    for item in result:
      if not isinstance(item, IJobResult):
        raise TypeError(f"All items in result must be IJobResult objects, found {type(item)}")

    return JobResponse(
      request_message_id=request.message_id,
      job_name=request.job_name,
      request_origin=request.origin,
      response_origin=self._host_id,
      response_dest=request.origin,
      result=result,
    )

  def send_request_result(self, request: IJobRequest, result: IJobResult):
    # response = JobResponse()
    pass

  def send_response(self, response: IJobResponse):
    """Send a JobResponse as a QueueMessage"""
    response_dest = f"ai-cli.response.{response.job_name}.{response.request_origin}"

    encoded_message_body = self._serialize_obj(obj=response.result)
    message = QueueMessage(
      type="response",
      context=response.job_name,
      reply_to=response.request_message_id,
      origin_host_id=response.response_origin,
      dest_queue=response_dest,
      body=encoded_message_body if encoded_message_body else "",
    )
    # print( f"JobConsumer.send_response -> Response: {response}" )
    # print( f"JobConsumer.send_response -> message: {message}" )
    self._queue.send_message(message=message)

  def start_consuming(self):
    self._queue.start_consuming()

  def stop_consuming(self):
    self._queue.start_consuming()


class JobSeeder(IJobSeeder):
  """Default JobSeeder Implementation"""

  def __init__(self, queue: IQueue, body_format: str = "pickle"):
    self._queue = queue
    self._body_format = body_format

  def _serialize_obj(self, obj: Any) -> Optional[str]:
    # all serialization / deserialization here is broken..
    # it is working because pika is correctly handling the bytes type
    # and doing magic behind the scenes when using RabbitMQ..
    serialized_obj = None
    if self._body_format == "pickle":
      serialized_obj = pickle.dumps(obj)
    elif self._body_format == "json":
      serialized_obj = json.dumps(obj)
    else:
      raise Exception(f"Unsupported serialization format: {self._body_format}")
    return serialized_obj

  def send_request(self, request: IJobRequest):
    """Send an IJobRequest via the IQueue as a QueueMessage"""
    # print( f"JobSeeder.send_request -> IJobRequest {request}" )
    encoded_message_body = self._serialize_obj(obj=request.job_playbook)
    message = QueueMessage(
      message_id=request.message_id,
      type="job",
      context=request.job_name,
      dest_queue=f"ai-cli.job.{request.job_name}",
      origin_host_id=request.origin,
      body=encoded_message_body if encoded_message_body else "",
    )
    # print( f"JobSeeder.send_request -> QueueMessage {message}" )
    self._queue.send_message(message=message)


class ResponseConsumer(IResponseConsumer):
  """Default ResponseConsumer implementation"""

  _supported_jobs: list[str]
  _queue: IQueue
  _response_callback: ResponseConsumerCallback
  _host_id: str
  _body_format: str

  def __init__(
    self,
    supported_jobs: list[str],
    queue: IQueue,
    response_callback: ResponseConsumerCallback,
    host_id: str,
    body_format: str = "pickle",
  ):
    self._host_id = host_id
    self._body_format = body_format
    self._supported_jobs = supported_jobs
    self._queue = queue
    self._response_callback = response_callback
    self._queue.consume_queues(
      queue_names=self._get_queue_names(), message_callback=self._handle_consume_callback
    )
    # calculate the list of queue names we need to listen to
    # and register them with our internal callback..
    # print( f"Created ResponseConsumer: {supported_jobs}" )

  def _deserialize_obj(self, serialized_obj: str) -> Optional[Any]:
    # all serialization / deserialization here is broken..
    # it is working because pika is correctly handling the bytes type
    # and doing magic behind the scenes when using RabbitMQ..
    deserialized_obj = None
    if self._body_format == "pickle":
      deserialized_obj = pickle.loads(serialized_obj)
    elif self._body_format == "json":
      deserialized_obj = json.loads(serialized_obj)
    else:
      raise Exception(f"Unsupported deserialization format: {self._body_format}")
    return deserialized_obj

  def _get_queue_names(self) -> list[str]:
    queue_names = []
    for job_name in self._supported_jobs:
      queue_names.append(f"ai-cli.response.{job_name}.{self._host_id}")
    return queue_names

  def _handle_consume_callback(self, message: IQueueMessage):
    # this should de-serialize the message body..
    new_response = self._get_response(message=message)
    # print( f"ResultConsumer._handle_consume_callback -> {new_response}" )
    # when we get messages, create JobResponses from them, and call the consumer request callback.
    self._response_callback(response=new_response)

  def _get_response(self, message: IQueueMessage) -> JobResponse:

    deserialized_body = self._deserialize_obj(serialized_obj=message.body)

    # all serialization / deserialization here is broken..
    # it is working because pika is correctly handling the bytes type
    # and doing magic behind the scenes when using RabbitMQ..

    return JobResponse(
      job_name=message.context,
      message_id=message.message_id,
      ack_id=message.ack_id,
      response_origin=message.origin_host_id if message.origin_host_id else "",
      result=deserialized_body if deserialized_body else [],
      request_message_id=message.reply_to if message.reply_to else "",
      response_dest=self._host_id,
      request_origin=message.origin_host_id if message.origin_host_id else "",
    )

  def ack_response(self, response: IJobResponse):
    # turn the request into a QueueMessage and ack it.?
    # print( f"ResponseConsumer.ack_request -> {response}" )
    self._queue.ack_message(ack_id=response.ack_id)

  def nack_response(self, response: IJobResponse):
    self._queue.ack_message(ack_id=response.ack_id)

  def start_consuming(self):
    self._queue.start_consuming()

  def stop_consuming(self):
    self._queue.start_consuming()


class ResponseSeeder(IResponseSeeder):
  def __init__(self, queue: IQueue):
    self._queue = queue


class JobQueueFactory:
  """Factory for creating instances of job queues"""

  @staticmethod
  def create_queue(queue_type: str, init_args: Optional[dict] = None) -> IQueue:
    if queue_type == "none":
      from ai_cli.local_job_queue import LocalJobQueue

      return LocalJobQueue()
    elif queue_type == "rabbitmq":
      from ai_cli.rabbitmq_job_queue import RabbitMqJobQueue

      return RabbitMqJobQueue(init_args=init_args if init_args else {})
    raise ValueError(f"Unknown queue type: {queue_type}")
