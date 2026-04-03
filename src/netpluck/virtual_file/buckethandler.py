from .base import VirtualFile
try:
	from buckethandler import BucketHandler
except ImportError:
	raise ImportError("To use backblaze b2 support you need to install the bucket handler package, you can do this via: pip install netpluck[bucket]")

class VirtualFileBucketHandler(VirtualFile):

	def __init__(self, handler:BucketHandler, filename):
		self.handler = handler
		self.filename = filename

		self.remote_file_id = None
		self.remote_file_size = -1

		records = handler.search(filename,recurse=False,include_dirs=False,include_files=True)
		for record in records['files']:
			if record['action'] == 'upload' and record['fileName'] == filename:
				self.remote_file_size = record['contentLength']
				if 'fileId' in record:
					self.remote_file_id = record['fileId']
				else:
					self.remote_file_path = record['fileName']

				print(f"Found file: {self.filename}, Size: {self.remote_file_size}, File ID: {self.remote_file_id}")
				break

		if self.remote_file_id is None and self.remote_file_path is None:
			raise Exception(f"File not found")

		super().__init__(filename, self.remote_file_size)



	def _read_uncached_range(self, start, end) -> bytes:
		if self.remote_file_id is not None:
			result = self.handler.handler.download_by_key(key=self.remote_file_id,start=start,end=end,write_to_disk=False)
		else:
			result = self.handler.handler._download_by_path(path_src=self.remote_file_path,start=start,end=end,write_to_disk=False)

		return result['content']
