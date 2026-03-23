import os
from netpluck.virtual_file import VirtualFile

class VirtualArchive:
	'''
	VirtualArchive is an interface that defines the methods that an archive handler should implement.
	'''
	def __init__(self, vf:VirtualFile):
		self.vf = vf
	def get_file(self, filename):
		'''
		Read a file into memory and return the bytes
		'''
		raise NotImplementedError()
	def get_file_list(self):
		'''
		Return a list of files in the archive
		'''
		raise NotImplementedError()
	def extract(self,internal_path:str, output_dir:str, flatten:bool=False, replace:bool=True, normalize_path:bool=True) -> str:
		'''
		Extract a file from the zip to the specified output directory

		Args:
			internal_path: is the path to the file within the zip, eg: foo/bar/car.png
			output_dir: is the directory to extract to, eg: output/
			flatten: is a boolean that indicates whether to flatten the output file structure, if true the output file will be output/car.png instead of output/foo/bar/car.png
				flatten is useful if you just want the files and don't care about the directory structure within the archive
			replace: if false, and the output file exists, skips it
			normalize_path: if true, this will cleanup and convert ..,./,// and slashes to the os specific separator

		Returns:
			The path to the extracted file

		Raises:
			Exception: if the file is not found in the archive or if there is an error during extraction
		'''
		if flatten:
			output_path = os.path.join(output_dir, os.path.basename(internal_path))
		else:
			output_path = os.path.join(output_dir, internal_path)

		if normalize_path:
			output_path = os.path.normpath(output_path)

		if replace == False and os.path.exists(output_path):
			return output_path

		# get the data only if it's new or we are replacing

		data = self.get_file(internal_path)

		output_dir_full = os.path.dirname(output_path)
		os.makedirs(output_dir_full, exist_ok=True)

		buffer_len = 1024 * 1024 # 1mb buffer

		with open(output_path, "wb", buffering=buffer_len) as f:
			f.write(data)

		return output_path
