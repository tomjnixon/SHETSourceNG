from twisted.internet.protocol import Protocol
from twisted.internet.defer import returnValue, inlineCallbacks, Deferred, succeed
from collections import deque, namedtuple
import struct

class PullProtocol(Protocol):

  def __init__(self):
    self.char_reciever = None
    self.buffer = deque()

  def dataReceived(self, data):
    self.buffer.extend(data)
    self._process_chars()

  def _process_chars(self):
    """Take a char from the buffer and pass it to the current char_reciever if
    possible."""
    if self.char_reciever is not None and self.buffer:
      char_reciever = self.char_reciever
      self.char_reciever = None
      char_reciever.callback(self.buffer.popleft())

  def recieve_char(self, d):
    """Register a deferred to recieve a char."""
    assert self.char_reciever is None, "char reciever already registered"
    self.char_reciever = d
    self._process_chars()

  def get_char(self):
    """Get a character from the stream as a deferred."""
    d = Deferred()
    self.recieve_char(d)
    return d


DataType = namedtuple("DataType", "id name get convert")


class TypesMixin(object):
  
  def get_byte(self):
    return self.get_char().addCallback(ord)
  
  def convert_byte(self, byte):
    return chr(byte)
  
  def get_void(self):
    return succeed(None)
  
  def convert_void(self, value=None):
    return ""
  
  @inlineCallbacks
  def get_struct_fmt(self, fmt):
    """Recieve the struct specified by fmt."""
    size = struct.calcsize(fmt)
    data = []
    for i in range(size):
      data += (yield self.get_char())
    returnValue(struct.unpack(fmt, ''.join(data)))
  
  def get_integer(self):
    return self.get_struct_fmt("<h").addCallback(lambda x: x[0])
  
  def convert_integer(self, value):
    return struct.pack("<h", value)
  
  @inlineCallbacks
  def get_string(self):
    """Get a null-terminated string."""
    chars = []
    while True:
      char = (yield self.get_char())
      if char == '\0':
        returnValue(''.join(chars))
      chars.append(char)
  
  def convert_string(self, value):
    return value + '\0'
  
  TYPE_VOID = DataType(0, "void", get_void, convert_void)
  TYPE_INTEGER = DataType(1, "integer", get_integer, convert_integer)
  TYPE_STRING = DataType(2, "string", get_string, convert_string)
  types = dict((t.id, t) for t in [TYPE_VOID, TYPE_INTEGER, TYPE_STRING])
  
  def get_type(self):
    return self.get_byte().addCallback(lambda x: self.types[x])
  
  def convert_type(self, type):
    return chr(type.id)

class PullProtocolTypes(PullProtocol, TypesMixin):
  pass
