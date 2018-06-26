""" 
Simple socket client thread sample.

Eli Bendersky (eliben@gmail.com)
This code is in the public domain
"""
import socket
import struct
import threading
import Queue
import re


class ClientCommand(object):
	""" A command to the client thread.
		Each command type has its associated data:
	
		CONNECT:    (host, port) tuple
		SEND:       Data string
		RECEIVE:    None
		CLOSE:      None
	"""
	CONNECT, SEND, RECEIVE, CLOSE = range(4)
	
	def __init__(self, type, data=None):
		self.type = type
		self.data = data


class ClientReply(object):
	""" A reply from the client thread.
		Each reply type has its associated data:
		
		ERROR:      The error string
		SUCCESS:    Depends on the command - for RECEIVE it's the received
					data string, for others None.
	"""
	ERROR, SUCCESS = range(2)
	
	def __init__(self, type, data=None):
		self.type = type
		self.data = data


class SocketClientThread(threading.Thread):
	""" Implements the threading.Thread interface (start, join, etc.) and
		can be controlled via the cmd_q Queue attribute. Replies are placed in
		the reply_q Queue attribute.
	"""
	def __init__(self, cmd_q=Queue.Queue(), reply_q=Queue.Queue()):
		super(SocketClientThread, self).__init__()
		self.cmd_q = cmd_q
		self.reply_q = reply_q
		self.reply_lines = 0
		self.alive = threading.Event()
		self.alive.set()
		self.socket = None
		
		self.handlers = {
			ClientCommand.CONNECT: self._handle_CONNECT,
			ClientCommand.CLOSE: self._handle_CLOSE,
			ClientCommand.SEND: self._handle_SEND,
			ClientCommand.RECEIVE: self._handle_RECEIVE,
		}
	
	def run(self):
		while self.alive.isSet():
			try:
				# Queue.get with timeout to allow checking self.alive
				cmd = self.cmd_q.get(True, 1)
				self.handlers[cmd.type](cmd)
			except Queue.Empty as e:
				continue
				
	def join(self, timeout=None):
		self.alive.clear()
		threading.Thread.join(self, timeout)
	
	def _handle_CONNECT(self, cmd):
		try:
			self.socket = socket.socket(
				socket.AF_INET, socket.SOCK_STREAM)
			self.socket.connect((cmd.data[0], cmd.data[1]))
			self.reply_q.put(self._success_reply())
		except IOError as e:
			self.reply_q.put(self._error_reply(str(e)))
	
	def _handle_CLOSE(self, cmd):
		self.socket.close()
		reply = ClientReply(ClientReply.SUCCESS)
		self.reply_q.put(reply)
		
	def _handle_SEND(self, cmd):
		try:
			self.socket.sendall(cmd.data + '\r')
			self.reply_q.put(self._success_reply())
		except IOError as e:
			self.reply_q.put(self._error_reply(str(e)))
	
	def _handle_RECEIVE(self, cmd):
		try:
			lines = self.socket.recv(1024).splitlines()
			for line in lines:
				self.reply_q.put(self._success_reply(line))
			self.reply_lines = len(lines)
		except IOError as e:
			self.reply_q.put(self._error_reply(str(e)))

	def _error_reply(self, errstr):
		return ClientReply(ClientReply.ERROR, errstr)
	
	def _success_reply(self, data=None):
		return ClientReply(ClientReply.SUCCESS, data)


#------------------------------------------------------------------------------
if __name__ == "__main__":
	sct = SocketClientThread()
	sct.start()
	sct.cmd_q.put(ClientCommand(ClientCommand.CONNECT, ('192.168.0.110', 4992)))
	sct.cmd_q.put(ClientCommand(ClientCommand.SEND, "C1|sub slice all"))
	while True:
		sct.cmd_q.put(ClientCommand(ClientCommand.RECEIVE))
		try:
			reply = sct.reply_q.get(True, 0.1)
			print(reply.type, reply.data)
		except Queue.Empty as e:
			continue
