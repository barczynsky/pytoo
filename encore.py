# -*- coding: utf-8 -*-
import collections
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
class File:
	class Popen(object):
		def __init__(self, f):
			self.stdin = f
			self.stdout = f

	class Ptee(object):
		def __init__(self, *F):
			self.__F = F

		def write(self, b):
			if self.__F:
				count = set()
				for f in self.__F:
					count.add(f.write(b))
				return min(count)
			return 0

		def close(self):
			for f in self.__F:
				f.close()


# ----------------------------------------------------------------------------
# -------------------------------  io add-ons  -------------------------------
# ----------------------------------------------------------------------------
class TextIOLoopback(io.TextIOWrapper):
	def __init__(self, b, **kwargs):
		self.__file__ = b
		if hasattr(b, 'mode'):
			self.mode = b.mode
		self.__loopback__ = []
		super().__init__(b, **kwargs)

	def fileno(self):
		if self.__loopback__:
			return 10000 + self.__file__.fileno()
		return self.__file__.fileno()

	def readline(self, size=-1):
		if self.__loopback__:
			e = self.__loopback__[0]
			if 0 >= size or size >= len(e) >= 0:
				return self.__loopback__.pop(0)
			(b, self.__loopback__[0]) = (e[:size], e[size:])
			return b
		return self.__file__.readline(size)

	def lwrite(self, *lines):
		for line in lines:
			self.__loopback__.extend(line.splitlines())
		return sum(map(len, lines))
