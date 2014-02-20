from twisted.trial import unittest
from twisted.test import proto_helpers
from twisted.internet.defer import returnValue, inlineCallbacks, Deferred
from src.protocol import ShetSourceProtocol
import mock
from mock import Mock


class TestProtocol(unittest.TestCase):
  
  def setUp(self):
    pass
  
  def get_protocol(self, mock_shet):
    transport = proto_helpers.StringTransport()
    proto = ShetSourceProtocol(mock_shet)
    proto.makeConnection(transport)
    proto.dataReceived("\x00\xff\x2a\x2a/foo\0")
    return (transport, proto)
  
  def test_reset(self):
    t, p = self.get_protocol(None)
    
    self.assertEqual(p.connection_id, 10794)
    self.assertEqual(p.base_path, "/foo")
  
  @inlineCallbacks
  def test_action(self):
    mock_shet = Mock()
    t, p = self.get_protocol(mock_shet)
    
    p.dataReceived("\x03""\x01\x00""action\0""\x01""\x01\x00")
    [(call, (path, f), kwargs)] = mock_shet.add_action.mock_calls
    
    self.assertEqual(path, "/foo/action")
    self.assertEqual(p._actions[1], mock_shet.add_action.return_value)
    self.assertEqual(t.value(), "")
    
    d = f(5)
    
    self.assertEqual(t.value(), "\x0a\x01\x00\x05\x00")
    p.dataReceived("\x0d\x07\x00")
    self.assertEqual((yield d), 7)
  
  def test_event(self):
    mock_shet = Mock()
    t, p = self.get_protocol(mock_shet)
    
    p.dataReceived("\x04" "\x02\x00" "event\0")
    mock_shet.add_event.assert_called_once_with("/foo/event")
    event = mock_shet.add_event.return_value
    self.assertEqual(p._events[2], event)
    self.assertEqual(t.value(), "")
    
    p.dataReceived("\x09" "\x02\x00" "\x00")
    event.assert_called_once_with()
    self.assertEqual(t.value(), "")
    event.reset_mock()
    
    p.dataReceived("\x09" "\x02\x00" "\x01" "\x0a\x00" "\x00")
    event.assert_called_once_with(10)
    self.assertEqual(t.value(), "")
    event.reset_mock()
  
  @inlineCallbacks
  def test_property(self):
    mock_shet = Mock()
    t, p = self.get_protocol(mock_shet)
    
    p.dataReceived("\x05" "\x03\x00" "prop\0" "\x01")
    
    [(call, (path, on_get, on_set), kwargs)] = mock_shet.add_property.mock_calls
    self.assertEqual(path, "/foo/prop")
    self.assertEqual(p._properties[3], mock_shet.add_property.return_value)
    self.assertEqual(t.value(), "")
    
    d = on_get()
    self.assertEqual(t.value(), "\x0c" "\x03\x00")
    p.dataReceived("\x0d\x06\x00")
    self.assertEqual((yield d), 6)
    t.clear()
    
    d = on_set(5)
    self.assertEqual(t.value(), "\x0b" "\x03\x00\x05\x00")

    

if __name__ == "__main__":
  unittest.main()
