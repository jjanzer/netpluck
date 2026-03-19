import os

class VirtualFileBuffer():

	def __init__(self, start, end, data: bytes):
		self.start = start
		self.end = end
		self.length = end - start
		self.data = data


class VirtualFile():

	def __init__(self, path, size = -1):
		'''
		VirtualFile is an abstract class that represents a file that can be read from.
		The handler will be an object that you can read from like so:
		vh = VirtualFile("path/to/file")
		data = vh[0:100] # read the first 100 bytes of the file

		Args:
			path: the path to the file, this can be a local file path or a remote file path depending on the implementation
			size: the size of the file in bytes, if not provided it will be determined by the implementation
		'''
		self.path = path

		self.size = size

		self.uncached_reads = 0
		self.cached_reads = 0
		# how many bytes have we fetched?
		self.cached_read_bytes = 0
		self.uncached_read_bytes = 0

		self.buffers = []

	def _read_uncached_range(self, start, end) -> bytes:
		'''
		This method should be implemented by the subclass to read a range of bytes.
		It should not be called directly by the user.

		Args:
			start: the starting byte index to read from
			end: the ending byte index to read to

		Returns:
			A bytes object containing the data read from the file in the specified range
		'''
		raise NotImplementedError()

	def _read_range(self, start, end) -> bytes:
		'''
		Reads a range of bytes from the file without using the cache

		Args:
			start: the starting byte index to read from
			end: the ending byte index to read to

		Returns:
			A bytes object containing the data read from the file in the specified range
		'''
		self.uncached_reads += 1
		self.uncached_read_bytes += (end - start)
		return self._read_uncached_range(start, end)

	def get_bytes(self, start, end=None, length=None) -> bytes:
		'''
		Reads the specified range of bytes from the file, using the cache if possible

		Args:
			start: the starting byte index to read from
			end: the ending byte index to read to, if not provided it will be determined by the length parameter
			length: the number of bytes to read if end is not provided

		Returns:
			A bytes object containing the data read from the file in the specified range
		'''

		if start < 0:
			start = 0

		if end == None and length != None:
			end = start + length
		elif end == None and length == None:
			raise Exception("Either end or length must be provided")
		elif end != None and end < start:
			raise Exception("End must be greater than start")

		# do we already have a chunk in this range?
		for buffer in self.buffers:
			if buffer.start <= start and buffer.end >= end:
				self.cached_reads += 1
				self.cached_read_bytes += (end - start)
				return buffer.data[start - buffer.start:end - buffer.start]

		# we don't so fetch it, add it to the cache and return it
		bytes = self._read_range(start, end)
		if bytes:
			self.buffers.append(VirtualFileBuffer(start, end, bytes))
			return self.buffers[-1].data

		return b''

	def __getitem__(self,key) -> bytes:
		'''
		Allows us to use the bracket notation to read from the file
		eg: data = vf[0:100] to read the first 100 bytes of the file

		Args:
			key: can be a slice object like 0:100 or an int like 5

		Returns:
			A bytes object containing the data read from the file in the specified range or at the specified index
		'''
		if isinstance(key, slice):
			start = key.start if key.start is not None else 0
			end = key.stop if key.stop is not None else self.size
			return self.get_bytes(start, end)
		elif isinstance(key, int):
			if key < 0:
				key += self.size
			if key < 0 or key >= self.size:
				raise IndexError("Index out of range")
			return self.get_bytes(key, key + 1)
		else:
			raise TypeError("Invalid argument type")
