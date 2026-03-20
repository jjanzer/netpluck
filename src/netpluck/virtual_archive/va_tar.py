import zlib
import os
from typing import List
import re
from pprint import pprint
from .base import VirtualArchive
from netpluck.virtual_file import VirtualFile


def get_tar_header_info(bytes):

	is_ustar = False
	if len(bytes) > 262 and bytes[257:262] == b"ustar":
		is_ustar = True

	if bytes[0:512].rstrip(b'\x00') == b'':
		# this is an empty header, which indicates the end of the tar file
		return {
			'filename': "",
			'file_mode': "",
			'owner_id': "",
			'group_id': "",
			'file_size': 0,
			'modification_time': 0,
			'checksum': 0,
			'type_of_file': 0,
			'link_name': "",

			'is_ustar': is_ustar,
			'is_eof': True,
			'full_filename': "",
		}

	result = {
		'filename': bytes[0:100].rstrip(b'\x00').decode("utf-8"),
		'file_mode': bytes[100:108].rstrip(b'\x00').decode("utf-8"),
		'owner_id': bytes[108:116].rstrip(b'\x00').decode("utf-8"),
		'group_id': bytes[116:124].rstrip(b'\x00').decode("utf-8"),
		'file_size': int(bytes[124:136].rstrip(b'\x00').decode("utf-8"), 8),
		'modification_time': int(bytes[136:148].rstrip(b'\x00').decode("utf-8"), 8),
		'checksum': int(bytes[148:156].rstrip(b' ').rstrip(b'\x00').decode("utf-8"), 8),
		'type_of_file': int.from_bytes(bytes[156:157], "little"),
		'link_name': bytes[157:257].rstrip(b'\x00').decode("utf-8"),

		'is_ustar': is_ustar,
		'is_eof': False,
	}
	result['full_filename'] = result['filename']
	if not is_ustar:
		# this is a very old tar file
		return result

	result['ustar_indicator'] = bytes[257:263].rstrip(b'\x00').decode("utf-8")
	result['ustar_version'] = bytes[263:265].rstrip(b'\x00').decode("utf-8")
	result['owner_user_name'] = bytes[265:297].rstrip(b'\x00').decode("utf-8")
	result['owner_group_name'] = bytes[297:329].rstrip(b'\x00').decode("utf-8")
	result['device_major_number'] = bytes[329:337].rstrip(b'\x00').decode("utf-8")
	result['device_minor_number'] = bytes[337:345].rstrip(b'\x00').decode("utf-8")
	result['filename_prefix'] = bytes[345:500].rstrip(b'\x00').decode("utf-8")

	if result['filename_prefix'] != "":
		result['full_filename'] = result['filename_prefix'] + "/" + result['filename']

	return result


class VirtualArchiveTar(VirtualArchive):
	def __init__(self, vf:VirtualFile):
		super().__init__(vf)

		self._performed_toc = False
		self.toc = []
		self.map_filename_to_header = {}

	def get_file(self, filename):
		if not self._performed_toc:
			self.get_file_list()

		if filename not in self.map_filename_to_header:
			raise Exception(f"File {filename} not found in archive")

		header_info = self.map_filename_to_header[filename]
		file_start = header_info['file_start']
		file_end = header_info['file_end']
		return self.vf[file_start:file_end]

	def get_file_list(self):

		# unfortunately for tars we have to skip through the entire file to build the toc
		# TODO: we could optimize this by only reading the entire toc if the user tries to filter
		# if they are just looking for a file, we can scan until we found the match and then stop

		if self._performed_toc:
			return self.toc
		# modern posix tar files (we'll ignore ancient ones) are typically made up of 512 byte header blocks + series of 512 bye file blocks

		result = []
		offset = 0

		header_info = {}

		while offset < self.vf.size and (offset == 0 or header_info['filename'] != ""):
			header_bytes = self.vf[offset:offset+512]
			header_info = get_tar_header_info(header_bytes)
			if header_info['is_eof']:
				break


			next_offset = offset + 512 + ((header_info['file_size'] + 511) // 512) * 512
			chunk_size = next_offset - offset

			header_info['file_start'] = offset + 512
			header_info['file_end'] = offset + chunk_size

			self.map_filename_to_header[header_info['full_filename']] = header_info
			result.append(header_info['full_filename'])

			offset = next_offset

		self._performed_toc = True
		self.toc = result

		return self.toc
