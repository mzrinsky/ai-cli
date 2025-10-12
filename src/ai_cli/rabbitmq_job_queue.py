from ai_cli.job_queue import IQueue, IQueueMessage, QueueMessage, QueueConsumeCallback
from typing import Optional
import pika


class RabbitMqJobQueue( IQueue ):
  """RabbitMQ implementation of the IQueue interface."""

  _callbacks = {}
  _queue_def = {}

  def __init__( self, init_args: dict ):
    self.connection = pika.BlockingConnection( pika.URLParameters( **init_args ) )
    self.channel = self.connection.channel()

  def _handle_on_message_callback( self, channel, method_frame, header_frame, body ):
    """Handle the pika on_message callback and dispatch any registered QueueMessage callbacks"""
    #print( f"RabbitMqJobQueue._handle_on_message_callback -> channel: {channel}" )
    #print( method_frame )
    #print( header_frame )
    if method_frame.routing_key in self._callbacks:
      # create a QueueMessage from the rabbitmq message details
      message = QueueMessage(
        ack_id=method_frame.delivery_tag,
        body=body,
        reply_to=header_frame.reply_to,
        message_id=header_frame.message_id,
        type=header_frame.headers[ 'type' ],
        context=header_frame.headers[ 'context' ],
        src_queue=method_frame.routing_key,
        origin_host_id=header_frame.headers[ 'origin' ]
      )
      #print( f"RabbitMqJobQueue._handle_on_message_callback -> message: {message}" )
      for callback in self._callbacks[ method_frame.routing_key ]:
        # print( f"RabbitMqJobQueue._handle_on_message_callback -> Running callback: {callback}" )
        callback( message=message )

  def ack_message( self, message: Optional[ IQueueMessage ] = None, ack_id: Optional[ str ] = None ):
    """Ack a message to remove it from the queue."""
    # print(f"RabbitMqJobQueue.ack_message -> message: {message}, ack_id: {ack_id}")
    if ack_id:
      self.channel.basic_ack( delivery_tag=ack_id )
    elif message:
      self.channel.basic_ack( delivery_tag=message.ack_id )

  def consume_queues( self, queue_names: list[ str ], message_callback: QueueConsumeCallback ):
    """Begin consuming registered queues and calling callbacks when messages are received."""
    self._message_receive_callback = message_callback
    for queue_name in queue_names:
      if queue_name in self._callbacks:
        self._callbacks[ queue_name ].append( message_callback )
      else:
        self._callbacks[ queue_name ] = [ message_callback ]
      self._queue_def[ queue_name ] = self.channel.queue_declare( queue=queue_name, durable=True, exclusive=False, auto_delete=False )
      self.channel.basic_consume( queue_name, on_message_callback=self._handle_on_message_callback )

  def nack_message( self, message: Optional[ IQueueMessage ] = None, ack_id: Optional[ str ] = None ):
    """Nack a message, this normally informs the message broker the message was NOT handled."""
    if ack_id:
      self.channel.basic_nack( delivery_tag=ack_id )
    elif message:
      self.channel.basic_nack( delivery_tag=message )

  def send_message( self, message: IQueueMessage ):
    """Send a message that implements the IQueueMessage interface."""
    properties = pika.BasicProperties(
      message_id=str( message.message_id ),
      reply_to=str( message.reply_to ),
      headers={
      "type": message.type,
      "context": message.context,
      "origin": message.origin_host_id
      }
    )
    #print( f"RabbitMqJobQueue.send_message -> Message {message}" )
    #print( f"RabbitMqJobQueue.send_message -> Properties {properties}" )
    self.channel.basic_publish( exchange='', routing_key=message.dest_queue, body=message.body, properties=properties )

  def start_consuming( self ):
    """Start consuming messages on registered queues"""
    try:
      self.channel.start_consuming()
    finally:
      self.channel.stop_consuming()

  def stop_consuming( self ):
    """Stop consuming messages"""
    self.channel.stop_consuming()
