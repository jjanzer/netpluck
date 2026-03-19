from .base import VirtualFile
try:
	from buckethandler import BackblazeB2Handler
except ImportError:
	raise ImportError("To use backblaze b2 support you need to install the bucket handler package, you can do this via: pip install netpluck[bucket]")

class VirtualFileBackblaze(VirtualFile):

	def __init__(self, handler:BackblazeB2Handler, filename):
		self.handler = handler
		self.filename = filename

		self.b2_file_id = None
		self.b2_file_size = -1

		records = handler.search(filename,recurse=False,include_dirs=False,include_files=True)
		for record in records['files']:
			if record['action'] == 'upload' and record['fileName'] == filename:
				self.b2_file_size = record['contentLength']
				self.b2_file_id = record['fileId']

				print(f"Found file: {self.filename}, Size: {self.b2_file_size}, B2 File ID: {self.b2_file_id}")
				break

		if self.b2_file_id is None:
			raise Exception("File not found on backblaze")

		super().__init__(filename, self.b2_file_size)



	def _read_uncached_range(self, start, end) -> bytes:
		result = self.handler.download_by_key(key=self.b2_file_id,start=start,end=end,write_to_disk=False)

		return result['content']
