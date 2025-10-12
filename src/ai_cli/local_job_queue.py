
from ai_cli.job_queue import IQueue, IQueueMessage, QueueConsumeCallback, QueueMessage
from typing import Optional
from uuid import uuid4
from time import sleep
from warnings import warn


class LocalJobQueue( IQueue ):
  """Local in-memory unshared implementation of the job queue provider."""

  def __init__( self ):
    self._queue = {}
    self._callbacks = {}
    self._deadletter = {}
    self.consuming = False

  def consume_queues( self, queue_names: list[ str ], message_callback: QueueConsumeCallback ):
    """Register a list of queues from which to consume messages."""
    for queue_name in queue_names:
      if queue_name not in self._queue:
        self._queue[ queue_name ] = []
      if queue_name not in self._callbacks:
        self._callbacks[ queue_name ] = [ message_callback ]
      else:
        self._callbacks[ queue_name ].append( message_callback )

  def _has_messages( self ) -> bool:
    for queue_name in self._queue.keys():
      if len( self._queue[ queue_name ] ):
        return True
    return False

  def start_consuming( self ):
    """Start consuming messages from the registered queues."""
    self.consuming = True
    while self.consuming and self._has_messages():
      for queue_name in list( self._queue.keys() ):
        # print( f"Processing queue: {queue_name}" )
        for message in list( self._queue[ queue_name ] ):
          # print( f"Processing message: {message}" )
          if queue_name in self._callbacks:
            for callback in self._callbacks[ queue_name ]:
              # print( f"Calling callback: {callback}" )
              new_properties = message.__dict__
              new_properties["ack_id"] = str(uuid4())
              new_message = QueueMessage( **new_properties )
              callback.__call__( message=new_message )
          else:
            # print( f"Have message with no active callbacks (currently undeliverable) {queue_name} {message}" )
            warn(f"Have message with no active callbacks (currently undeliverable) {queue_name} {message}")
            # self.ack
            if queue_name not in self._deadletter:
              self._deadletter[ queue_name ] = []
            self._deadletter[ queue_name ].append( message )
            self.ack_message( message=message )

  def stop_consuming( self ):
    """Stop consuming messages."""
    self.consuming = False

  def ack_message( self, message: Optional[ IQueueMessage ] = None, ack_id: Optional[ str ] = None ):
    # print(f"Ack Request: {message} : {ack_id}")
    if ack_id:
      # print( f"Ack'ing message: {ack_id}" )
      for queue_name in list( self._queue.keys() ):
        self._queue[ queue_name ] = [ msg for msg in list( self._queue[ queue_name ] ) if msg.ack_id != ack_id ]
    elif message:
      # print( f"Ack'ing message: {message}" )
      self._queue[ message.dest_queue ] = [ msg for msg in list( self._queue[ message.dest_queue ] ) if msg.ack_id != message.ack_id ]

  def nack_message( self, message: Optional[ IQueueMessage ] = None, ack_id: Optional[ str ] = None):
    """In this implementation nack is just do nothing.."""
    # print(f"NAck Request: {message} : {message_id}")
    if ack_id:
      # print( f"NAck'ing message: {message_id}" )
      return
    elif message:
      # print( f"NAck'ing message: {message}" )
      return

  def send_message( self, message: IQueueMessage ):
    # print( f"LocalJobQueue.send_message -> {message}" )
    if message.dest_queue not in self._queue:
      self._queue[ message.dest_queue ] = []

    self._queue[ message.dest_queue ].append( message )
