#!/usr/bin/env python3
import multiprocessing
import time
import os
import signal
multiprocessing.cpu_pool = lambda: len(os.sched_getaffinity(0))


class Worker(multiprocessing.Process):
	__mgr = multiprocessing.Manager()

	def __init__(self, *args, naptime=1.0, deadline=None, **kwargs):
		self.enabled = Worker.__mgr.Event()
		self.settings = Worker.__mgr.dict()
		self.settings['naptime'] = naptime
		self.settings['deadline'] = deadline
		super(Worker, self).__init__(target=self.work, args=args, kwargs=kwargs)
		self.start()

	def __enter__(self):
		self.onEnter()

	def __exit__(self, exc_type, exc_value, traceback):
		self.onExit()

	def onEnter(self):
		pass

	def doExit(self):
		pass

	def onDo(self):
		pass

	def work(self, *args, **kwargs):
		self.onEnter()
		try:
			while self.enabled.wait(timeout=self.settings['deadline']):
				self.onDo()
				time.sleep(self.settings['naptime'])
		except KeyboardInterrupt:
			pass
		self.doExit()

	def kill(self):
		self.settings['deadline'] = 0.0
		self.enabled.clear()
		if self.pid:
			os.kill(self.pid, signal.SIGINT)

	def enable(self):
		self.enabled.set()

	def disable(self):
		self.enabled.clear()


if __name__ == '__main__':
	try:
		pool = [Worker() for i in range(4)]
		# for p in pool:
		# 	p.start()
		for p in pool:
			p.enable()
		while True:
			time.sleep(.1)
	except KeyboardInterrupt:
		pass
	else:
		for p in pool:
			p.kill()
	finally:
		for p in pool:
			p.join()
