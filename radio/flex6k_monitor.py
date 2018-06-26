#!/usr/bin/python

import os
import re
import sys
import Queue
import signal
import pickle
from lxml import etree

sys.path.append('/home/pi/bin/stationcontrol/lib')
from flex6k_socket_client_lib import SocketClientThread, ClientCommand, ClientReply

def signal_handler(signal, frame):
    print ''
    save_slices(False)
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler) #process killed
signal.signal(signal.SIGINT, signal_handler) #CTRL-C interrupt

CONFIGFILE = "/home/pi/bin/stationcontrol/radio/flex6k.xml"
SLICESFILE = "/home/pi/bin/stationcontrol/slices.bin"

class Slice:
	def __init__(self, num, freq=None, active=None, tx=None):
		self.slice_num = num
		self.freq = freq
		self.active = active
		self.tx = tx

class Flex6K:
	# first: define regular expressions to parse strings from radio
	freq_chg = re.compile(r'^.+\|slice (?P<slice>\d) RF_.+=(?P<freq>\d{1,2}[.]\d+)')
	slice_chg = re.compile(r'^.+\|slice (?P<slice>\d) active=(?P<active>\d)')
	tx_chg = re.compile(r'^.+\|slice (?P<slice>\d).+tx=(?P<tx>\d)')
	init_slice = re.compile(r'^.+\|slice (?P<slice>\d).+RF_.+=(?P<freq>\d{1,2}[.]\d+).+tx=(?P<tx>\d) active=(?P<active>\d)')
	remove_slice = re.compile(r'^.+\|slice (?P<slice>\d)')
	
	def __init__(self):
		configfile = os.path.expanduser(CONFIGFILE)
		if not os.path.exists(configfile):
			raise Exception("Please create %s" % (configfile))
		config = etree.parse(configfile).getroot()
		assert config.tag == "flex6k"
		self.ip=config.findtext("address/ip")
		self.port= int(config.findtext("address/port"))
		self.sct = SocketClientThread()
		self.sct.daemon = True
		self.sct.start()
		self.radioVer = ""
		self.myIdent = ""
		self.txFreq = None
		self.slices = dict()

	def connect_radio(self):
		self.sct.cmd_q.put(ClientCommand(ClientCommand.CONNECT, (self.ip, self.port)))
		reply = self.sct.reply_q.get()
		self.sct.cmd_q.put(ClientCommand(ClientCommand.SEND, "C1|sub slice all"))
		reply = self.sct.reply_q.get()
		self.sct.cmd_q.put(ClientCommand(ClientCommand.RECEIVE))
		reply = self.sct.reply_q.get()
		self.radioVer = reply.data.lstrip('V')
		print "RadioVer:", self.radioVer
		reply = self.sct.reply_q.get()
		self.myIdent = reply.data.lstrip('H')
		print "MyIdent:", self.myIdent

	def parse_reply(self, reply):
		if not reply.startswith('|slice', 9):
			return
		#print reply
		update = False
		if reply.startswith('RF_', 18): # freq change
			m = self.freq_chg.match(reply)
			self.tuneFreqSlice = m.group('slice')
			freq = m.group('freq')
			self.slices[self.tuneFreqSlice].freq = float(freq)
			update = True
		elif reply.startswith('active', 18): # change active slice
			m = self.slice_chg.match(reply)
			slice_num = m.group('slice')
			slice_active = m.group('active')
			update = True
			try: # when going to DIV - is sent before "in-use" statement
				self.slices[slice_num].active = slice_active
			except KeyError:
				update = False
				pass
			if slice_active == '1':
				self.activeSlice = slice_num
		elif reply.startswith('pan', 18): # TX active change
			m = self.tx_chg.match(reply)
			slice_num = m.group('slice')
			tx_active = m.group('tx')
			update = True
			try: # on radio start - this is sent before the "in-use" statement, causes error
				self.slices[slice_num].tx = tx_active
			except KeyError:
				update = False
				pass
			if tx_active=='1':
				self.txSlice = slice_num
		elif reply.startswith('in_use=1', 18): # slice created
			m = self.init_slice.match(reply)
			slice_num = m.group('slice')
			slice_freq = m.group('freq')
			tx_active = m.group('tx')
			if tx_active=='1':
				self.txSlice = slice_num
				self.txFreq = float(slice_freq)
			slice_active = m.group('active')
			if slice_active == '1':
				self.activeSlice = slice_num
			slice_class = Slice(slice_num, float(slice_freq), slice_active, tx_active)
			self.slices[slice_num] = slice_class
			update = True
		elif reply.startswith('in_use=0', 18): # slice removed
			m = self.remove_slice.match(reply)
			slice_num = m.group('slice')
			del self.slices[slice_num]
			update = True
		return update

	def monitor(self):
		while True:
			try:
				self.sct.cmd_q.put(ClientCommand(ClientCommand.RECEIVE))
				reply = self.sct.reply_q.get(True, 0.1)
				if self.parse_reply(reply.data): #if valid 'wanted' parse
					save_slices()
			except Queue.Empty as e:
				continue

def save_slices(save=True):
	filename = SLICESFILE
	if save:
		with open(filename, 'wb') as outfile:
				pickle.dump(flex6k.slices, outfile, 2)
		print "Updated slices.bin file"
	else:
		with open(filename, 'w'):
			os.utime(filename, None)
		print "Cleared slices.bin file"

if __name__ == "__main__":
	flex6k = Flex6K()
	flex6k.connect_radio()
	flex6k.monitor()
