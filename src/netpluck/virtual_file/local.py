import os

from importlib.resources import path

from .base import VirtualFile, VirtualFileBuffer



class VirtualFileLocal(VirtualFile):

	def __init__(self, path, size = -1):
		self.filename = path

		if size < 0:
			size = os.path.getsize(path)

		super().__init__(path, size)

	def _read_uncached_range(self, start, end) -> bytes:
		file_size = os.path.getsize(self.filename)

		if start < 0:
			start = 0

		if end > file_size:
			end = file_size

		with open(self.filename, "rb") as f:
			f.seek(start)
			return f.read(end - start)

