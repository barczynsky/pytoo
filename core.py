# -*- coding: utf-8 -*-
import builtins
import functools
import signal


# ----------------------------------------------------------------------------
# -----------------------  KeyboardInterrupt add-ons  ------------------------
# ----------------------------------------------------------------------------
class KeyboardInterruptGuard(object):
	def __enter__(self):
		self.__SIGINT = signal.getsignal(signal.SIGINT)
		signal.signal(signal.SIGINT, signal.SIG_IGN)

	def __exit__(self, t, v, bt):
		signal.signal(signal.SIGINT, self.__SIGINT)


class KeyboardInterruptForward(object):
	def __enter__(self):
		self.__SIGINT = signal.getsignal(signal.SIGINT)
		self.__FWD = []
		signal.signal(signal.SIGINT, lambda *sig: self.__FWD.append(sig))

	def __exit__(self, t, v, bt):
		signal.signal(signal.SIGINT, self.__SIGINT)
		for sig in self.__FWD:
			self.__SIGINT(*sig)


# ----------------------------------------------------------------------------
# -----------------------------  input() add-on  -----------------------------
# ----------------------------------------------------------------------------
def input(prompt: str='', timeout: int=0):
	print = builtins.print
	input = builtins.input
	timeout = max(int(timeout), 0)
	if timeout and hasattr(signal, 'alarm') and hasattr(signal, 'SIGALRM'):
		def raise_timeout_error(*sig):
			raise TimeoutError
		try:
			raise_KeyboardInterrupt = False
			raise_EOFError = False
			s = None
			handler = signal.signal(signal.SIGALRM, raise_timeout_error)
			signal.alarm(timeout)
			if prompt:
				s = input(prompt)
			else:
				s = input()
			signal.alarm(0)
		except TimeoutError:
			print()
		except EOFError:
			raise_EOFError = True
		except KeyboardInterrupt:
			raise_KeyboardInterrupt = True
		finally:
			signal.signal(signal.SIGALRM, handler)
			if raise_KeyboardInterrupt:
				raise KeyboardInterrupt
			if raise_EOFError:
				raise EOFError
			return s
	else:
		if prompt:
			return input(prompt)
		else:
			return input()


# ----------------------------------------------------------------------------
# -----------------------------  bind & bindmap  -----------------------------
# ----------------------------------------------------------------------------
class bind(functools.partial):
	def __repr__(self):
		return '{}({}...)'.format(
			self.func,
			', '.join(map(str, self.args + ('',))),
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
# --------------------------------  missdict  --------------------------------
# ----------------------------------------------------------------------------
class missdict(dict):
	def __init__(self, missing=None, *args, **kwargs):
		self.__miss__ = missing
		super().__init__(*args, **kwargs)

	def __missing__(self, key):
		if callable(self.__miss__):
			return self.__miss__()
		return self.__miss__


# ----------------------------------------------------------------------------
# ---------------------------------  cmdict  ---------------------------------
# ----------------------------------------------------------------------------
class cmdict(dict):
	def __init__(self, other=None, **kwargs):
		super().__init__()
		if other:
			self.update(other, **kwargs)

	def __contains__(self, key):
		if not isinstance(key, str):
			return super().__contains__(key)
		return 1 == sum(c.startswith(key) for c in self if isinstance(c, str))

	def __setitem__(self, key, value):
		if not isinstance(key, (str, type(None))):
			raise KeyError('key must be a string or None, not \'{}\''.format(type(key).__name__))
		return super().__setitem__(key, value)

	def __getitem__(self, key):
		if not isinstance(key, str):
			return super().__getitem__(key)
		m = [c for c in self if isinstance(c, str) and c.startswith(key)]
		return super().__getitem__(m[0] if 1 == len(m) else key)

	def __delitem__(self, key):
		if not isinstance(key, str):
			return super().__delitem__(key)
		m = [c for c in self if isinstance(c, str) and c.startswith(key)]
		return super().__delitem__(m[0] if 1 == len(m) else key)

	def __missing__(self, key):
		return None

	def update(self, other, **kwargs):
		if not isinstance(other, (list, tuple, dict)):
			raise TypeError('\'{}\' object is not iterable'.format(type(other).__name__))

		if isinstance(other, dict):
			other = other.items()
		for kvlist in other:
			if kvlist:
				self.extend(kvlist)
		for kvlist in kwargs:
			self.extend(kvlist)
		return None

	@staticmethod
	def fromargs(*args):
		d = cmdict()
		d.extend(args)
		return d

	def __add__(self, seq):
		return self.extend(seq)

	def extend(self, seq):
		if isinstance(seq, dict):
			self.update(seq)
			return self

		if not isinstance(seq, (list, tuple)):
			raise TypeError('\'{}\' object is not iterable'.format(type(seq).__name__))

		(k, *kvlist) = seq or [None]
		if not isinstance(k, (str, type(None))):
			raise ValueError('key must be a string or None, not \'{}\''.format(type(k).__name__))

		if kvlist:
			v = kvlist[0]
			if k not in self:
				if isinstance(v, dict):
					self[k] = cmdict(v)  # no kvlist
				elif callable(v):
					self[k] = bind(*kvlist)
				elif v is None:
					self[k] = v  # NotImplementedError
				elif kvlist[1:]:
					self[k] = cmdict().extend(kvlist)
			else:
				if isinstance(self[k], dict):
					if not isinstance(self[k], cmdict):
						self[k] = cmdict(self[k])  # promote
					if isinstance(v, dict):
						if not isinstance(v, cmdict):
							v = cmdict(v)  # promote
						self[k].update(v)  # no kvlist
					elif callable(v):
						self[k][None] = bind(*kvlist)
				elif callable(self[k]):
					if isinstance(v, dict):
						if k not in v or v[k] is None:
							(self[k], v) = (cmdict(v), self[k])  # no kvlist
							self[k][None] = v
						else:
							self[k] = cmdict(v)  # no kvlist
					elif callable(v):
						self[k] = bind(*kvlist)
				elif kvlist[1:]:
					self[k] = cmdict().extend(kvlist)
		return self

	def __call__(self, *args):
		if args:
			arg0 = args[0]
			if arg0 and arg0 in self:
				if isinstance(self[arg0], self.__class__):
					return self[arg0](*args[1:])
				elif callable(self[arg0]):
					self[arg0](*args[1:])  # leaf
					return True
				elif self[arg0] is None:
					raise NotImplementedError
		if callable(self[None]):
			self[None](*args)  # leaf
			return True
		return False
