import zlib
import os
from typing import List
import re
from pprint import pprint
from .base import VirtualArchive

def find_eocd_offset(bytes):
	# Search for the end of central directory signature
	signature = b"\x50\x4b\x05\x06"
	offset = bytes.rfind(signature)
	if offset == -1:
		raise ValueError("End of central directory signature not found")
	return offset

def find_eocd64_offset(bytes):
	# Search for the ZIP64 end of central directory locator signature
	signature = b"\x50\x4b\x06\x07"
	offset = bytes.rfind(signature)
	if offset == -1:
		raise ValueError("ZIP64 end of central directory locator signature not found")
	return offset

def read_zip64_end_of_central_directory_locator(bytes):
	# ZIP64 end of central directory locator signature
	signature = b"\x50\x4b\x06\x07"
	if bytes[:4] != signature:
		raise ValueError("Not a valid ZIP64 end of central directory locator")

	# Read the ZIP64 end of central directory locator fields

	'''
	disk_with_zip64_eocd = int.from_bytes(bytes[4:8], "little")
	disk_number_of_zip64_eocd = int.from_bytes(bytes[8:12], "little")
	offset_of_zip64_eocd = int.from_bytes(bytes[12:20], "little", signed=False)
	total_number_of_disks = int.from_bytes(bytes[20:24], "little")
	'''
	disk_with_zip64_eocd = int.from_bytes(bytes[4:8], "little")
	offset_of_zip64_eocd = int.from_bytes(bytes[8:16], "little", signed=False)
	total_number_of_disks = int.from_bytes(bytes[16:24], "little", signed=False)

	return {
		"disk_with_zip64_eocd": disk_with_zip64_eocd,
		"offset_of_zip64_eocd": offset_of_zip64_eocd,
		"total_number_of_disks": total_number_of_disks
	}

def read_zip_end_of_central_directory(bytes):
	# End of central directory signature
	signature = b"\x50\x4b\x05\x06"
	if bytes[:4] != signature:
		raise ValueError("Not a valid end of central directory record")

	# Read the end of central directory record fields
	disk_number = int.from_bytes(bytes[4:6], "little")
	disk_start = int.from_bytes(bytes[6:8], "little")
	num_entries = int.from_bytes(bytes[8:10], "little")
	total_entries = int.from_bytes(bytes[10:12], "little")
	central_directory_size = int.from_bytes(bytes[12:16], "little")
	central_directory_offset = int.from_bytes(bytes[16:20], "little")
	comment_length = int.from_bytes(bytes[20:22], "little")
	comment = bytes[22:22 + comment_length].decode("utf-8")

	return {
		"disk_number": disk_number,
		"disk_start": disk_start,
		"num_entries": num_entries,
		"total_entries": total_entries,
		"central_directory_size": central_directory_size,
		"central_directory_offset": central_directory_offset,
		"comment": comment
	}

def read_zip64_end_of_central_directory(bytes):
	# ZIP64 end of central directory signature
	signature = b"\x50\x4b\x06\x06"
	if bytes[:4] != signature:
		raise ValueError("Not a valid ZIP64 end of central directory record")

	# Read the ZIP64 end of central directory record fields
	size_of_zip64_eocd = int.from_bytes(bytes[4:12], "little")
	version_made_by = int.from_bytes(bytes[12:14], "little")
	version_needed = int.from_bytes(bytes[14:16], "little")
	disk_number = int.from_bytes(bytes[16:20], "little")
	disk_start = int.from_bytes(bytes[20:24], "little")
	num_entries_on_disk = int.from_bytes(bytes[24:32], "little")
	total_entries = int.from_bytes(bytes[32:40], "little")
	central_directory_size = int.from_bytes(bytes[40:48], "little")
	central_directory_offset = int.from_bytes(bytes[48:56], "little")

	return {
		"size_of_zip64_eocd": size_of_zip64_eocd,
		"version_made_by": version_made_by,
		"version_needed": version_needed,

		# these are the same as the normal EOCD but 4 bytes vs 2 or 8 bytes vs 4
		"disk_number": disk_number,
		"disk_start": disk_start,
		"num_entries_on_disk": num_entries_on_disk,
		"total_entries": total_entries,
		"central_directory_size": central_directory_size,
		"central_directory_offset": central_directory_offset
	}

def read_zip_central_directory_file_header(bytes):
	# Central directory file header signature
	signature = b"\x50\x4b\x01\x02"
	if bytes[:4] != signature:
		print(f"Signature not found: {bytes[0:4].hex()}")
		raise ValueError("Not a valid central directory file header")

	# Read the central directory file header fields
	version_made_by = int.from_bytes(bytes[4:6], "little")
	version_needed = int.from_bytes(bytes[6:8], "little")
	flags = int.from_bytes(bytes[8:10], "little")
	compression = int.from_bytes(bytes[10:12], "little")
	mod_time = int.from_bytes(bytes[12:14], "little")
	mod_date = int.from_bytes(bytes[14:16], "little")
	crc32 = int.from_bytes(bytes[16:20], "little")
	compressed_size = int.from_bytes(bytes[20:24], "little")
	uncompressed_size = int.from_bytes(bytes[24:28], "little")
	filename_length = int.from_bytes(bytes[28:30], "little")
	extra_field_length = int.from_bytes(bytes[30:32], "little")
	file_comment_length = int.from_bytes(bytes[32:34], "little")
	disk_number_start = int.from_bytes(bytes[34:36], "little")
	internal_file_attributes = int.from_bytes(bytes[36:38], "little")
	external_file_attributes = int.from_bytes(bytes[38:42], "little")
	offset = int.from_bytes(bytes[42:46], "little")
	header_size = 46 + filename_length + extra_field_length + file_comment_length

	# Read the filename, extra field, and file comment
	filename = bytes[46:46 + filename_length].decode("utf-8")
	extra_field = bytes[46 + filename_length:46 + filename_length + extra_field_length]
	file_comment = bytes[46 + filename_length + extra_field_length:46 + filename_length + extra_field_length + file_comment_length]

	is_zip64 = False
	if compressed_size == 0xFFFFFFFF or uncompressed_size == 0xFFFFFFFF or offset == 0xFFFFFFFF:
		is_zip64 = True
		# we need to parse the extra field
		extra_field_offset = 0
		while extra_field_offset < len(extra_field):
			header_id = int.from_bytes(extra_field[extra_field_offset:extra_field_offset + 2], "little")
			data_size = int.from_bytes(extra_field[extra_field_offset + 2:extra_field_offset + 4], "little")
			data = extra_field[extra_field_offset + 4:extra_field_offset + 4 + data_size]

			if header_id == 0x0001:
				# zip64 extra field
				data_offset = 0
				if uncompressed_size == 0xFFFFFFFF:
					uncompressed_size = int.from_bytes(data[data_offset:data_offset + 8], "little")
					data_offset += 8
				if compressed_size == 0xFFFFFFFF:
					compressed_size = int.from_bytes(data[data_offset:data_offset + 8], "little")
					data_offset += 8
				if offset == 0xFFFFFFFF:
					offset = int.from_bytes(data[data_offset:data_offset + 8], "little")
					data_offset += 8
				break

			extra_field_offset += 4 + data_size

	result = {
		"version_made_by": version_made_by,
		"version_needed": version_needed,
		"flags": flags,
		"compression": compression,
		"mod_time": mod_time,
		"mod_date": mod_date,
		"crc32": crc32,
		"compressed_size": compressed_size,
		"uncompressed_size": uncompressed_size,
		"filename": filename,
		"extra_field": extra_field,
		"file_comment": file_comment,
		"disk_number_start": disk_number_start,
		"internal_file_attributes": internal_file_attributes,
		"external_file_attributes": external_file_attributes,
		"offset": offset,
		"header_size": header_size,
		"is_zip64": is_zip64
	}

	# for 64bit we will have 0xFFFFFFFF in the compressed or uncompressed size or offset

	return result

def read_zip_data_descriptor(bytes,is_zip_64=False):
	# Data descriptor present
	data_descriptor_signature = b"\x50\x4b\x07\x08"
	if bytes[:4] != data_descriptor_signature:
		print(f"Data descriptor signature not found")
		return None

	data_descriptor_start = 0
	data_descriptor_crc32 = int.from_bytes(bytes[data_descriptor_start:data_descriptor_start + 4], "little")

	data_descriptor_compressed_size = 0
	data_descriptor_uncompressed_size = 0

	if is_zip_64:
		data_descriptor_compressed_size = int.from_bytes(bytes[data_descriptor_start + 4:data_descriptor_start + 12], "little")
		data_descriptor_uncompressed_size = int.from_bytes(bytes[data_descriptor_start + 12:data_descriptor_start + 20], "little")
	else:
		data_descriptor_compressed_size = int.from_bytes(bytes[data_descriptor_start + 4:data_descriptor_start + 8], "little")
		data_descriptor_uncompressed_size = int.from_bytes(bytes[data_descriptor_start + 8:data_descriptor_start + 12], "little")

	print(f" compressed size: {data_descriptor_compressed_size} uncompressed size: {data_descriptor_uncompressed_size}")

	file_start = data_descriptor_start + 12
	file_end = file_start + data_descriptor_compressed_size

	return {
		"crc32": data_descriptor_crc32,
		"compressed_size": data_descriptor_compressed_size,
		"uncompressed_size": data_descriptor_uncompressed_size,
		"file_start": file_start,
		"file_end": file_end,
	}


def read_zip_local_file_header(bytes):
	# Local file header signature
	signature = b"\x50\x4b\x03\x04"
	if bytes[:4] != signature:
		raise ValueError("Not a valid local file header")

	# Read the local file header fields
	version = int.from_bytes(bytes[4:6], "little")
	flags = int.from_bytes(bytes[6:8], "little")
	compression = int.from_bytes(bytes[8:10], "little")
	mod_time = int.from_bytes(bytes[10:12], "little")
	mod_date = int.from_bytes(bytes[12:14], "little")
	crc32 = int.from_bytes(bytes[14:18], "little")
	compressed_size = int.from_bytes(bytes[18:22], "little")
	uncompressed_size = int.from_bytes(bytes[22:26], "little")
	filename_length = int.from_bytes(bytes[26:28], "little")
	extra_field_length = int.from_bytes(bytes[28:30], "little")

	# Read the filename and extra field
	filename = bytes[30:30 + filename_length].decode("utf-8")
	extra_field = bytes[30 + filename_length:30 + filename_length + extra_field_length]

	# calculate the end of the LH
	lh_end = 30 + filename_length + extra_field_length

	file_start = lh_end
	file_end = file_start + compressed_size

	return {
		"version": version,
		"flags": flags,
		"compression": compression,
		"mod_time": mod_time,
		"mod_date": mod_date,
		"crc32": crc32,
		"compressed_size": compressed_size,
		"uncompressed_size": uncompressed_size,
		"filename": filename,
		"extra_field": extra_field,
		"lh_end": lh_end,
		"file_start": file_start,
		"file_end": file_end,
		"has_data_descriptor": flags & 0x08 != 0,
		"is_zip_64": compressed_size == 0xFFFFFFFF
	}

class VirtualArchiveZip(VirtualArchive):
	def __init__(self, virtual_file):
		self.vf = virtual_file

		self.cdfh_objects = []
		self.filename_to_cdfh_map = {}
		self.toc = []
		self._performed_toc = False
		self.quiet = False # If true, suppress non-error output

	def get_file(self, filename: str) -> bytes:
		#if len(self.filename_to_cdfh_map
		#if self.filename_to_cdfh_map.get(filename) is None:
		#	raise Exception(f"File not found in zip: {filename}")
		if self._performed_toc == False:
			self.get_file_list()

		if self.filename_to_cdfh_map.get(filename) is None:
			raise Exception(f"File not found in zip: {filename}")

		cdfh = self.filename_to_cdfh_map[filename]
		#pprint.pprint(cdfh)
		lfh_buffer = self.vf[cdfh['offset']:cdfh['lfh_end']]

		lfh = read_zip_local_file_header(lfh_buffer)
		#pprint(lfh)

		#compressed_data = self.vf[lfh['offset']:lfh['offset'] + lfh['compressed_size']]

		offset = cdfh['offset']

		file_start = offset + lfh['file_start']
		file_end = file_start + cdfh['compressed_size']
		compressed_data = self.vf[file_start:file_end]

		#print(f"compressed data len: {len(compressed_data)} bytes start: {file_start} end: {file_end}")

		#print(f"compressed data: {compressed_data[0:32].hex()}")

		if len(compressed_data) != cdfh['compressed_size']:
			raise Exception(f"Compressed data size mismatch for file {filename}, expected {cdfh['compressed_size']} bytes but got {len(compressed_data)} bytes")

		if len(compressed_data) == 0:
			# The file is actually empty
			return b''

		# the data may also not be compressed...
		if cdfh['compression'] == 0:
			return compressed_data

		uncompressed = zlib.decompress(compressed_data,-15)
		#print(f"uncompressed data: {uncompressed[0:32]}")

		return uncompressed

	def get_file_list(self) -> List[str]:
		if self._performed_toc:
			return self.toc

		self.toc = []
		self.filename_to_cdfh_map = {}
		self._performed_toc = True

		# 64kb should be enough to find all the EOCD, EOCD64 and CDFH
		kb_64 = 64 * 1024
		file_size_bytes = self.vf.size

		tail_offset = file_size_bytes - kb_64

		tail_data = self.vf[tail_offset:file_size_bytes]
		tail_length = len(tail_data)
		#print(f"Tail data length: {tail_length} bytes for file: {self.vf.filename} size: {file_size_bytes} bytes")
		eocd_offset = find_eocd_offset(tail_data)

		eocd_offset_relative_to_full_file = eocd_offset + (file_size_bytes - tail_length)
		eocd = read_zip_end_of_central_directory(tail_data[eocd_offset:])

		# are we zip64?
		is_zip64 = eocd["central_directory_offset"] == 0xFFFFFFFF or eocd["central_directory_size"] == 0xFFFFFFFF or eocd["total_entries"] == 0xFFFF

		# the EOCD64 locator is 20 bytes before the EOCD
		if is_zip64:

			# it's always 20 bytes behind the EOCD
			eocd64_locator_offset = eocd_offset - 20
			if eocd64_locator_offset < 0:
				raise Exception("Not enough data to read the zip64 locator")

			eocd64_locator = read_zip64_end_of_central_directory_locator(tail_data[eocd64_locator_offset:eocd_offset])

			# now we need to read the EOCD64 itself
			eocd64_offset = eocd64_locator["offset_of_zip64_eocd"]

			eocd64_buffer = self.vf[eocd64_offset:eocd64_offset + 56]
			eocd = read_zip64_end_of_central_directory(eocd64_buffer)


		#pprint.pprint(eocd)

		# get the bytes of the entire CDFH (all of them)
		cdfh_start = eocd["central_directory_offset"]
		cdfh_end = cdfh_start + eocd["central_directory_size"]

		# get only the bytes needed for the CDFH
		# TODO: be smart if we already have these bytes don't refetch
		#all_cdfh_bytes = fetch_file_byte_range(in_file, cdfh_start, cdfh_end)

		# get all the cfdh objects
		self.cdfh_objects = []
		cdfh_offset = cdfh_start
		while cdfh_offset < cdfh_end:
			#print(f"Fetching CDFH at offset {cdfh_offset} to {cdfh_end}")
			bytes = self.vf[cdfh_offset:cdfh_end]
			#print(f"Fetched {len(bytes)} bytes hex: {bytes[0:32].hex()}")
			cdfh = read_zip_central_directory_file_header(bytes)
			self.cdfh_objects.append(cdfh)
			cdfh_offset += cdfh["header_size"]

		for idx in range(len(self.cdfh_objects)):
			if idx < len(self.cdfh_objects)-1:
				self.cdfh_objects[idx]["lfh_end"] = self.cdfh_objects[idx+1]["offset"]
			else:
				self.cdfh_objects[idx]["lfh_end"] = eocd_offset_relative_to_full_file

		result = []

		for cdfh in self.cdfh_objects:
			#print(f"File: {cdfh['filename']}, Offset: {cdfh['offset']}, Size: {cdfh['compressed_size']}")
			self.filename_to_cdfh_map[cdfh['filename']] = cdfh
			result.append(cdfh['filename'])

		self.toc = result
		return result
