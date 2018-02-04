# -*- coding: utf-8 -*-
import functools
import io
import re


# ----------------------------------------------------------------------------
# ---------------------------  functools add-ons  ----------------------------
# ----------------------------------------------------------------------------
class bind(functools.partial):
	def __repr__(self):
		return '{}({}, ...)'.format(
			self.func,
			', '.join(map(str, self.args)),
		)


def bindmap(func, *argpacks):
	if not all(isinstance(ap, (tuple, list, dict)) for ap in argpacks):
		return ()
	for (i, ap) in zip(range(len(argpacks)), argpacks[:]):
		if isinstance(ap, dict):
			argpacks[i:i + 1] = zip(*ap.items())
	# return zip(*argpacks[:1], map(lambda *packs: lambda *args: func(*packs, *args), *argpacks))
	return zip(*argpacks[:1], map(bind, iter(lambda: func, None), *argpacks))


# ----------------------------------------------------------------------------
# ------------------------------  str add-ons  -------------------------------
# ----------------------------------------------------------------------------
def trim(s: str):
	return ' '.join(filter(None, s.split()))


def take(s: str, count: int=1):
	st = tuple(filter(None, s.split()))
	return (st[:count], ' '.join(st[count:]))


def take_match(s: str, pattern: str):
	m = re.match(pattern, s)
	if m:
		return (s[m.end():], m.groups())
	return (s, ())


# ----------------------------------------------------------------------------
# -----------------------------  open() add-ons  -----------------------------
# ----------------------------------------------------------------------------
class PopenWrapper(object):
	def __init__(self, fo):
		self.__fo__ = fo
		self.stdin = fo
		self.stdout = fo
		self.stderr = fo


# ----------------------------------------------------------------------------
# ------------------------------  tee() add-on  ------------------------------
# ----------------------------------------------------------------------------
def tee(fo, *tee, buffering: int=-1, closefd: bool=False):
	if isinstance(fo, io.TextIOBase):
		def wrap(fo, line_buffering):
			if isinstance(fo, io.TextIOBase):
				return fo
			# if hasattr(fo, 'buffer'):
			# 	fo = fo.buffer
			return io.TextIOWrapper(fo, line_buffering=line_buffering)
		line_buffering = False
		if hasattr(fo, 'line_buffering'):
			line_buffering = fo.line_buffering
		return TextIOTee(fo, *(wrap(fo, line_buffering) for fo in tee), closefd=closefd, line_buffering=line_buffering)
	else:
		def spill(fo):
			if isinstance(fo, io.TextIOBase) and hasattr(fo, 'buffer'):
				return fo.buffer
			return fo
		if buffering:
			return BufferedIOTee(fo, *(spill(fo) for fo in tee), closefd=closefd)
		else:
			return FileIOTee(fo, *(spill(fo) for fo in tee), closefd=closefd)


class TextIOTee(io.TextIOWrapper):
	def __init__(self, fo, *tee, closefd: bool=False, **kwargs):
		self.__fo__ = fo
		self.__tee__ = tee
		self.closefd = closefd
		if hasattr(fo, 'mode'):
			self.mode = fo.mode
		# if hasattr(fo, 'buffer'):
		# 	fo = fo.buffer
		super().__init__(fo, **kwargs)

	def write(self, s: str):
		return min(fo.write(s) for fo in (self.__fo__, *self.__tee__))

	def close(self):
		if self.closefd:
			self.__fo__.close()
		return any(fo.close() for fo in self.__tee__)


class BufferedIOTee(io.BufferedWriter):
	def __init__(self, fo, *tee, closefd: bool=False, **kwargs):
		self.__fo__ = fo
		self.__tee__ = tee
		self.closefd = closefd
		# if hasattr(fo, 'buffer'):
		# 	fo = fo.buffer
		super().__init__(fo, **kwargs)

	def write(self, b: bytes):
		return min(fo.write(b) for fo in (self.__fo__, *self.__tee__))

	def close(self):
		if self.closefd:
			self.__fo__.close()
		return any(fo.close() for fo in self.__tee__)


class FileIOTee(io.FileIO):
	def __init__(self, fo, *tee, mode='r', closefd: bool=False, **kwargs):
		self.__fo__ = fo
		self.__tee__ = tee
		if hasattr(fo, 'mode'):
			mode = fo.mode
		super().__init__(fo.fileno(), mode=mode, closefd=closefd, **kwargs)
		if hasattr(fo, 'name'):
			self.name = fo.name

	def write(self, b: bytes):
		return min(fo.write(b) for fo in (self.__fo__, *self.__tee__))

	def close(self):
		if self.closefd:
			self.__fo__.close()
		return any(fo.close() for fo in self.__tee__)


# ----------------------------------------------------------------------------
# -------------------------------  io add-ons  -------------------------------
# ----------------------------------------------------------------------------
class TextIOLoopback(io.TextIOWrapper):
	def __init__(self, fo, line_buffering: bool=False, closefd: bool=False, **kwargs):
		self.__loopback__ = []
		self.__fo__ = fo
		self.closefd = closefd
		if hasattr(fo, 'line_buffering'):
			line_buffering = fo.line_buffering
		if hasattr(fo, 'mode'):
			self.mode = fo.mode
		# if hasattr(fo, 'buffer'):
		# 	fo = fo.buffer
		super().__init__(fo, line_buffering=line_buffering, **kwargs)

	def fileno(self):
		if self.__loopback__:
			return 10000 + self.__fo__.fileno()
		return self.__fo__.fileno()

	def close(self):
		if self.closefd:
			self.__fo__.close()

	def readline(self, size: int=-1):
		if self.__loopback__:
			e = self.__loopback__[0]
			if 0 >= size or size >= len(e) >= 0:
				return self.__loopback__.pop(0)
			(s, self.__loopback__[0]) = (e[:size], e[size:])
			return s
		return self.__fo__.readline(size)

	def lwrite(self, *lines):
		for line in lines:
			self.__loopback__.extend(line.splitlines())
		return sum(map(len, lines))
