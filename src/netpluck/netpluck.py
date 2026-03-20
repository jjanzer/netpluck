from enum import Enum
import re
import math
import os
from typing import List

from netpluck.virtual_archive.va_zip import VirtualArchiveZip
from netpluck.virtual_archive.va_tar import VirtualArchiveTar
from netpluck.virtual_file import VirtualFile, VirtualFileHTTP, VirtualFileLocal
from netpluck.virtual_archive.base import VirtualArchive

class ArchiveType(Enum):
	'''
	The list of archive types NetPluck supports
	'''
	ZIP = 1
	TAR = 2
	UNKNOWN = 99

class ProtocolType(Enum):
	'''
	The list of protocol types NetPluck supports
	'''
	LOCAL = 1 # Local file system
	HTTP = 2 # Both HTTP AND HTTPS are covered by this
	B2 = 3 # Backblaze B2
	UNKNOWN = 99


class NetPluck:

	def __init__(self, path, config=None, archive_type:ArchiveType=ArchiveType.UNKNOWN):
		'''
		Returns:
			An instance of NetPluck bound to the archive type

		Args:
			path: this should be a path to a local file, url, or a backblaze b2 file path, or similar
			config: can be a path to a json file or a key/value pair,
				it is used with VirtualFile handlers, so check the specifics of each one
			archive_type: if you know the type of archive you are working with you can specify it here, otherwise NetPluck will attempt to determine it by the file extension or magic bytes
		'''

		self.quiet = False
		self.ah:VirtualArchive
		self.at:ArchiveType = archive_type
		self.protocol:ProtocolType = ProtocolType.UNKNOWN
		self.vf:VirtualFile
		self.path = path

		self.protocol = self._guess_protocol(path)

		if self.protocol == ProtocolType.B2:
			# B2 support is only available if you install buckethandler

			try:
				from netpluck.virtual_file.backblaze import VirtualFileBackblaze
				from buckethandler import BackblazeB2Handler
			except ImportError:
				raise ImportError("To use backblaze b2 support you need to install the bucket handler package, you can do this via: pip install netpluck[bucket]")

			protocol_prefix_b2 = "b2://"
			path = path[len(protocol_prefix_b2):]
			handler = BackblazeB2Handler(config)
			self.vf = VirtualFileBackblaze(handler, path)
		elif self.protocol == ProtocolType.HTTP:
			self.vf = VirtualFileHTTP(path)
		elif self.protocol == ProtocolType.LOCAL:
			if path.startswith("file://"):
				path = path[len("file://"):]
			self.vf = VirtualFileLocal(path)
		else:
			raise Exception("Unsupported protocol type")

		if archive_type == ArchiveType.UNKNOWN:
			archive_type = self._guess_archive_type()
		self.at = archive_type

		# Finally let's instantiate the archive handler based on the archive type
		if self.at == ArchiveType.ZIP:
			self.ah = VirtualArchiveZip(self.vf)
		elif self.at == ArchiveType.TAR:
			self.ah = VirtualArchiveTar(self.vf)


	# Private Methods

	def _guess_protocol(self,path) -> ProtocolType:
		protocol_prefix_b2 = "b2://"
		protocol_prefix_http = "http://"
		protocol_prefix_https = "https://"
		if path.startswith(protocol_prefix_b2):
			return ProtocolType.B2
		elif path.startswith(protocol_prefix_http) or path.startswith(protocol_prefix_https):
			return ProtocolType.HTTP
		else:
			return ProtocolType.LOCAL

	def _guess_archive_type(self) -> ArchiveType:
		if self.path.endswith(".zip"):
			return ArchiveType.ZIP
		elif self.path.endswith(".tar"):
			return ArchiveType.TAR
		else:
			# Try fetching the magic bytes of the file to determine the type
			magic_bytes = self.vf[0:4]
			if magic_bytes == b'PK\x03\x04':
				return ArchiveType.ZIP

			# Try other types
			if self.vf[257:262] == b"ustar":
				return ArchiveType.TAR

			raise Exception("Could not determine archive type")



	# Public Methods


	def get_file_list(self) -> List[str]:
		'''
		Returns the list of all files in the archive
		Returns:
			A list of file paths in the archive
		'''
		return self.ah.get_file_list()

	def get_file(self, filename) -> bytes:
		'''
		Returns the contents of a file in the archive
		Args:
			filename: the path to the file within the archive
		Returns:
			The contents of the file as bytes
		'''
		return self.ah.get_file(filename)

	def extract(self,internal_path:str, output_dir:str, flatten:bool=False, replace:bool=True) -> str:
		'''
		Extracts a single file from the archive to an output directory, it will maintain the relative path of the file in the archive unless flatten is set to True
		Args:
			internal_path: the path to the file within the archive
			output_dir: the directory to extract the file to
			flatten: if true the extracted file will not be placed in child directories
			replace: if true, existing files will be replaced
		Returns:
			The path to the extracted file
		'''
		return self.ah.extract(internal_path, output_dir, flatten=flatten, replace=replace)

	def extract_from_filter(self, pattern, output_dir, flatten=False, replace=True) -> List[str]:
		'''
		Extracts files that match a regex pattern or list of regex patterns to an output directory, it will maintain the relative paths of the files in the archive unless flatten is set to True
		Args:
			pattern: a regex pattern or list of regex patterns to match against the file list of the archive
			output_dir: the directory to extract the matched files to
			flatten: if true the extracted files will not be placed in child directories, they will lay directly in the output folder (they may clobber over each other if named the same)
			replace: if true, existing files will be replaced
		Returns:
			A list of the paths to the extracted files
		'''
		if os.path.isdir(output_dir) == False:
			os.makedirs(output_dir,exist_ok=True)

		matched_files = self.filter(pattern)
		i = 0
		count = len(matched_files)
		result = []
		for file in matched_files:
			dst = self.extract(file, output_dir, flatten=flatten, replace=replace)
			result.append(dst)
			i += 1
			percent = (i / count) * 100.0

			if not self.quiet:
				print(f"[{i}/{count}] {percent:6.2f}% {file} => {dst}")

		return result

	def filter(self, patterns) -> List[str]:
		'''
		Finds all files in the TOC of an archive that match a regex pattern or list of regex patterns
		Args:
			patterns: a regex pattern or list of regex patterns to match against the file list of the archive
		Returns:
			A list of files that match the regex pattern(s)
		'''
		files = self.get_file_list()

		if isinstance(patterns, str):
			patterns = [patterns]

		result = []

		for pattern in patterns:
			matching_files = [filename for filename in files if re.search(pattern, filename)]

			for filename in matching_files:
				if filename not in result:
					result.append(filename)

		return result





	# misc helpers
	def pretty_file_size(self,bytes) -> str:
		'''
		Converts a number like 10 * 1024 * 1024 to 10MB

		Args:
			bytes: the number of bytes to convert to a human readable format
		Returns:
			A string representing the human readable file size, like 10MB or 5KB or 46B
		'''
		if bytes is None:
			return "0B"
		for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
			if bytes < 1024:
				return f"{bytes:.2f}{unit}"
			bytes /= 1024
		return f"{bytes:.2f}PB"

	def from_pretty_file_size(self,raw_str) -> int:
		'''
		Converts something like 10MB to 10*1024*1024 or 5*1024 to 5KB or 46 to 46B
		Args:
			raw_str: a string representing a human readable file size, like 10MB or 5KB or 46B
		Returns:
			The number of bytes represented by the input string, like 10*1024*1024 for 10MB or 5*1024 for 5KB or 46 for 46B
		'''
		raw_str = raw_str.strip().upper()
		match = re.match(r'([0-9\.]+)([KMGTP]?B)', raw_str)
		if not match:
			raise ValueError(f"Invalid file size format: {raw_str}")

		size = float(match.group(1))
		unit = match.group(2)

		if unit == 'KB':
			bytes = size * 1024
		elif unit == 'MB':
			bytes = size * 1024 * 1024
		elif unit == 'GB':
			bytes = size * 1024 * 1024 * 1024
		elif unit == 'TB':
			bytes = size * 1024 * 1024 * 1024 * 1024
		else:
			bytes = size

		return math.ceil(bytes)
