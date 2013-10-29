from twisted.trial import unittest
from twisted.internet.defer import returnValue, inlineCallbacks, Deferred
from src.pull_protocol import PullProtocolTypes
from twisted.test import proto_helpers
import struct

class TestReadData(unittest.TestCase):
  
  def setUp(self):
    self.p = PullProtocolTypes()
  
  @inlineCallbacks
  def test_buffer(self):
    self.p.dataReceived("foo")
    assert (yield self.p.get_char()) == "f"
    assert (yield self.p.get_char()) == "o"
    assert (yield self.p.get_char()) == "o"
  
  @inlineCallbacks
  def test_wait(self):
    d = self.p.get_char()
    self.p.dataReceived("f")
    assert (yield d) == "f"
    
    d = self.p.get_char()
    self.p.dataReceived("o")
    assert (yield d) == "o"
  
  @inlineCallbacks
  def test_get_byte(self):
    self.p.dataReceived(chr(42))
    assert (yield self.p.get_byte()) == 42
  
  @inlineCallbacks
  def test_get_struct_fmt(self):
    self.p.dataReceived(struct.pack('hhl', 1,2,3))
    assert (yield self.p.get_struct_fmt('hhl')) == (1,2,3)
  
  @inlineCallbacks
  def test_get_integer(self):
    self.p.dataReceived("\x01\x00")
    self.assertEqual((yield self.p.get_integer()), 1)
    self.p.dataReceived("\xff\xff")
    self.assertEqual((yield self.p.get_integer()), -1)
    
  @inlineCallbacks
  def test_get_string(self):
    self.p.dataReceived("foo\0")
    self.assertEqual((yield self.p.get_string()), "foo")
    self.p.dataReceived("bar\0")
    self.assertEqual((yield self.p.get_string()), "bar")
  
  @inlineCallbacks
  def test_get_void(self):
    self.assertEqual((yield self.p.get_void()), None)
  
  @inlineCallbacks
  def test_get_type(self):
    self.p.dataReceived("\x00")
    self.assertEqual((yield self.p.get_type()).name, "void")
    self.p.dataReceived("\x01")
    self.assertEqual((yield self.p.get_type()).name, "integer")
    self.p.dataReceived("\x02")
    self.assertEqual((yield self.p.get_type()).name, "string")


class TestConvertData(unittest.TestCase):
  
  def setUp(self):
    self.p = PullProtocolTypes()
    self.t = proto_helpers.StringTransport()
    self.p.makeConnection(self.t)
  
  def test_convert_void(self):
  	self.assertEqual(self.p.convert_void(), "")
  
  def test_convert_byte(self):
  	self.assertEqual(self.p.convert_byte(42), chr(42))
  
  def test_convert_integer(self):
  	self.assertEqual(self.p.convert_integer(1), "\x01\x00")
  	self.assertEqual(self.p.convert_integer(-1), "\xff\xff")
  
  def test_convert_string(self):
  	self.assertEqual(self.p.convert_string("foo"), "foo\0")
  	
  def test_convert_type(self):
  	self.assertEqual(self.p.convert_type(PullProtocolTypes.TYPE_VOID), "\x00")
  	self.assertEqual(self.p.convert_type(PullProtocolTypes.TYPE_INTEGER), "\x01")
  	self.assertEqual(self.p.convert_type(PullProtocolTypes.TYPE_STRING), "\x02")


if __name__ == "__main__":
  unittest.main()
