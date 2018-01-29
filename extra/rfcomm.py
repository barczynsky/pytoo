#!/usr/bin/env python3
import bluetooth
import reforge
import socket
import struct
import sys


class RFCOMMsocket(object):
	def __init__(self, devsock=None, devmac='', devname=''):
		super(RFCOMMsocket, self).__init__()
		self.devsock = devsock
		self.devmac = devmac
		self.devname = devname
		self.devch = None

	def connect(self, devmac=None, devname=None, channel=1):
		rfsock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
		if devmac:
			rfaddr = devmac
		else:
			rfaddr = self.discover(devmac=devmac, devname=devname)
		try:
			rfsock.connect((rfaddr, channel))
			self.devsock = rfsock
			self.devmac = devmac
			self.devname = devname
			self.devch = channel
			return True
		except Exception:
			return False

	def bind(self, devmac=None, channel=1):
		rfsock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
		if devmac:
			rfaddr = devmac
		try:
			rfsock.bind((rfaddr, channel))
			self.devsock = rfsock
			self.devmac = devmac
			self.devname = devmac
			self.devch = channel
			return True
		except Exception:
			return False

	def close(self):
		if self.devsock:
			self.devsock.close()
			self.devsock = None
			self.devmac = ''
			self.devname = ''

	def recv(self, buffersize=1024):
		if self.devsock:
			data = self.devsock.recv(buffersize)
			# if data in (b''):
			# 	return b''
			datahex = ''.join(' {:02x}'.format(b) for b in data)[1:]
			reforge.Print.append(file=sys.stderr)
			print('{} => hex({})'.format(data, datahex))
			reforge.Print.clear()
			return data

	@staticmethod
	def parse_frame(frame):
		framap = {
			b'f': ['f', 4],
			b'd': ['d', 8],
			b'b': ['b', 1],
			b'B': ['B', 1],
			b's': ['h', 2],
			b'S': ['H', 2],
			b'l': ['l', 4],
			b'L': ['L', 4],
		}
		try:
			content = []
			while len(frame) > 0:
				tp = framap[frame[:1]]
				content += struct.unpack('<x' + tp[0], frame[:1 + tp[1]])
		except Exception:
			pass
		finally:
			return content

	def recv_frame(self, buffersize=1):
		if self.devsock:
			while True:
				frame = self.devsock.recv(buffersize)
				if frame in (b'\0'):
					continue
				elif frame in (b''):
					return None
			framelen = int(frame[0])
			frame = frame[1:]
			while len(frame) < framelen:
				frame += self.devsock.recv(framelen - len(frame))
			# framehex = ''.join(' {:02x}'.format(b) for b in frame)[1:]
			# reforge.Print.append(file=sys.stderr)
			# print('{} => hex({})'.format(frame, framehex))
			# reforge.Print.clear()
			return self.parse_frame(frame)

	@staticmethod
	def discover(devmac=None, devname=None):
		print('Running bluetooth discovery...')
		bt_devs = bluetooth.discover_devices(duration=4, lookup_names=True)
		bt_devs = [bd for bd in bt_devs if bd[0] == (devmac or bd[0]) and bd[1] == (devname or bd[1])]

		if len(bt_devs):
			if (devmac or devname) and len(bt_devs) == 1:
				return bt_devs[0][0]
			# else:
			print('Found bluetooth devices:')
			for (bd_i, bd) in enumerate(bt_devs):
				print('[{}] {}'.format(bd_i, bd))

			while True:
				if len(bt_devs) > 1:
					try:
						bd_i = int(input('Select device [{}-{}]: '.format(0, len(bt_devs) - 1)))
					except KeyboardInterrupt:
						print()
						break
					except Exception:
						continue
				else:
					bd_i = 0
				if bd_i in range(len(bt_devs)):
					try:
						bd_c = input('Confirm device {} [y/t]: '.format(bt_devs[bd_i]))
					except KeyboardInterrupt:
						print()
						break
					if bd_c in (str(bd_i), 'y', 'Y', 't', 'T'):
						return bt_devs[bd_i][0]
					elif bd_c in (''):
						continue
					else:
						break
		else:
			print('No devices found.')

	def listen(self, backlog=16):
		self.bind(devmac='00:00:00:00:00:00', channel=1)
		self.devsock.listen(backlog)
		print('bluetooth connected: {}'.format((self.devmac, self.devch)))
		try:
			while True:
				try:
					(csock, caddr) = self.devsock.accept()
					cdevsock = RFCOMMsocket(devsock=csock, devmac=caddr[0])
					print('new connection: {}'.format(caddr))
					while True:
						cdevsock.recv()
				except ConnectionResetError:
					print('connection reset: {}'.format(caddr))
					csock.close()
		except KeyboardInterrupt:
			pass
		print('bluetooth disconnected: {}'.format((self.devmac, self.devch)))
		self.close()


if __name__ == '__main__':
	try:
		s = RFCOMMsocket()
		s.listen()
		# while True:
		# 	reforge.Print.append(file=sys.stderr)
		# 	RFCOMMsocket.discover()
		# 	reforge.Print.clear()
	except KeyboardInterrupt:
		pass
