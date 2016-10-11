#!/usr/bin/env python3
import builtins


class Print(object):
	__true_print = builtins.print
	__sham_print_args = ()
	__sham_print_kwargs = {}

	@staticmethod
	def __sham_print(*args, **kwargs):
		return Print.__true_print(*(*Print.__sham_print_args, *args), **{**Print.__sham_print_kwargs, **kwargs})

	@staticmethod
	def __call__(*args, **kwargs):
		return builtins.print(*args, *kwargs)

	@staticmethod
	def append(*args, **kwargs):
		Print.__sham_print_args = (*Print.__sham_print_args, *args)
		Print.__sham_print_kwargs = {**Print.__sham_print_kwargs, **kwargs}
		builtins.print = Print.__sham_print
		return Print

	@staticmethod
	def clear():
		Print.__sham_print_args = ()
		Print.__sham_print_kwargs = {}
		builtins.print = Print.__true_print
		return Print
