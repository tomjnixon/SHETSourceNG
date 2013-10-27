from twisted.internet.defer import returnValue, inlineCallbacks, Deferred, succeed
from twisted.internet.task import LoopingCall
from pull_protocol import PullProtocolTypes
from shet.client import ShetClient
from commands import *
from collections import deque
import traceback

class ShetSourceProtocol(PullProtocolTypes):
  
  def __init__(self, shet):
    PullProtocolTypes.__init__(self)
    self.shet = shet
    
    self.base_path = None
    self._deferred_returns = []
    
    self.connection_id = None
    
    self._properties = {}
    self._events     = {}
    self._actions    = {}
    
    self.run()
  
  def connectionLost(self, reason):
    print "connectionLost called"
    PullProtocolTypes.connectionLost(self, reason)
    self._clear_shet()
  
  def path(self, address):
    """Convert an address into a full SHET path for this device."""
    if not address.startswith("/"):
      return "/".join((self.base_path, address))
    else:
      return address
  
  def _clear_shet(self):
    """Clear all SHET records for this client."""
    for prop in self._properties.values(): self.shet.remove_property(prop)
    for event in self._events.values(): self.shet.remove_event(event)
    for action in self._actions.values(): self.shet.remove_action(action)
  
  @inlineCallbacks
  def process_reset(self):
    self.connection_id = (yield self.get_integer())
    self.base_path = (yield self.get_string())
  
  def deferred_return(self, type):
    d = Deferred()
    self._deferred_returns.append((type, d))
    return d
  
  def process_return(self):
    (type, d) = self._deferred_returns.pop(0)
    return type.get(self).chainDeferred(d)
  
  @inlineCallbacks
  def process_add_event(self):
    event_id = (yield self.get_integer())
    address  = (yield self.get_string())
    
    self._events[event_id] = self.shet.add_event(self.path(address))
    
  @inlineCallbacks
  def process_add_action(self):
    action_id     = (yield self.get_integer())
    address       = (yield self.get_string())
    return_type   = (yield self.get_type())
    argument_type = (yield self.get_type())
    
    def on_call(argument=None):
      self.transport.write(
          self.convert_byte(COMMAND_CALL_ACTION) + 
          self.convert_integer(action_id) +
          argument_type.convert(self, argument))
      return self.deferred_return(return_type)
    
    self._actions[action_id] = self.shet.add_action(self.path(address),
                                                    on_call)
  
  @inlineCallbacks
  def process_add_property(self):
    prop_id       = (yield self.get_integer())
    address       = (yield self.get_string())
    type = (yield self.get_type())
    
    def on_get():
      d = self.deferred_return(type)
      self.transport.write(
          self.convert_byte(COMMAND_GET_PROPERTY) +
          self.convert_integer(prop_id))
      return d
    
    def on_set(value):
      self.transport.write(
          self.convert_byte(COMMAND_SET_PROPERTY) +
          self.convert_integer(prop_id) +
          type.convert(self, value))
    
    self._properties[prop_id] = self.shet.add_property(self.path(address),
                                                       on_get, on_set)
  
  @inlineCallbacks
  def process_raise_event(self):
    event_id = (yield self.get_integer())
    type     = (yield self.get_type())
    
    if type.name == "void":
      self._events[event_id]()
    else:
      value = (yield type.get(self))
      self._events[event_id](value)
  
  def send_reset(self):
    self.transport.write(
        self.convert_byte(COMMAND_RESET))
  
  @inlineCallbacks
  def wait_for_reset(self):
    last_two_chars = ""
    reset_signal = chr(COMMAND_RESET) + chr(COMMAND_RESET ^ 0b11111111)
    reset_loop = LoopingCall(self.send_reset)
    reset_loop.start(2, now=False)
    try:
      while last_two_chars != reset_signal:
        print "wait"
        char = (yield self.get_char())
        last_two_chars = (last_two_chars + char)[-2:]
    except:
      raise
    finally:
      reset_loop.stop()
  
  @inlineCallbacks
  def process_ping(self):
    connection_id = (yield self.get_integer())
    if self.connection_id != connection_id:
      raise Exception("Invalid command")
  
  @inlineCallbacks
  def process_command(self):
    command = (yield self.get_byte())
    
    if command == COMMAND_RETURN:            yield self.process_return()
    elif command == COMMAND_PING:            yield self.process_ping()
    elif command == COMMAND_ADD_ACTION:      yield self.process_add_action()
    elif command == COMMAND_ADD_EVENT:       yield self.process_add_event()
    elif command == COMMAND_ADD_PROPERTY:    yield self.process_add_property()
    # elif command == COMMAND_REMOVE_ACTION:   yield self.process_remove_action()
    # elif command == COMMAND_REMOVE_EVENT:    yield self.process_remove_event()
    # elif command == COMMAND_REMOVE_PROPERTY: yield self.process_remove_property()
    elif command == COMMAND_RAISE_EVENT:     yield self.process_raise_event()
    else:
      raise Exception("Invalid command")
  
  @inlineCallbacks
  def run(self):
    try:
      yield self.wait_for_reset()
      yield self.process_reset()
      while True:
        yield self.process_command()
    except Exception, e:
      print traceback.format_exc()
      self.transport.loseConnection()
