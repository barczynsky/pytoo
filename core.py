# -*- coding: utf-8 -*-
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
	def __contains__(self, key):
		if not isinstance(key, str):
			return super().__contains__(key)
		return 1 == sum(c.startswith(key) for c in self if isinstance(c, str))

	def __setitem__(self, key, value):
		if not isinstance(key, str):
			raise KeyError('key must be a string, not \'{}\''.format(type(key).__name__))
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

	def getkey(self, key):
		if not isinstance(key, str):
			return None
		return next((c for c in self if isinstance(c, str) and c.startswith(key)), None)

	def __call__(self, *args):
		if args:
			arg0 = args[0]
			if arg0 in self:
				if isinstance(self[arg0], self.__class__):
					return self[arg0](*args[1:])
				elif callable(self[arg0]):
					self[arg0](*args[1:])  # leaf
					return True
				elif self[arg0] is None:
					raise NotImplementedError(arg0)
		if callable(self[None]):
			self[None]()  # leaf
			return True
		return False
