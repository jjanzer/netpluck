from netpluck.virtual_file import VirtualFile

class VirtualArchive:
	'''
	VirtualArchive is an interface that defines the methods that an archive handler should implement.
	'''
	def __init__(self, vf:VirtualFile):
		self.vf = vf
	def get_file(self, filename):
		raise NotImplementedError()
	def get_file_list(self):
		raise NotImplementedError()
	def extract(self,internal_path:str, output_dir:str, flatten:bool=False, replace:bool=True) -> str:
		raise NotImplementedError()
	def extract_from_filter(self, pattern, output_dir, flatten=False, replace=True):
		raise NotImplementedError()
