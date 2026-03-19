from importlib.resources import path

from .base import VirtualFile

import requests

# Handles generic reading of files over HTTP or HTTPS
class VirtualFileHTTP(VirtualFile):

	def __init__(self, url, follow_redirects=True):
		self.file_size = -1
		self.filename = url
		self.follow_redirects = follow_redirects

		# Get the headers of the file only
		response = requests.head(url, allow_redirects=follow_redirects)
		if follow_redirects and response.url != url:
			# prevent having to do future requests with the wrong url if there are redirects
			url = response.url

		if response.status_code == 200:
			self.file_size = int(response.headers.get('Content-Length', -1))
		else:
			raise Exception(f"Failed to get file headers for {url}, status code: {response.status_code}")

		if self.file_size < 0:
			# do we have Transfer-Encoding: chunked? if so let's try grabbing the first byte and see if there is a Content-Range header that gives us the file size
			if response.headers.get('Transfer-Encoding', '').lower() == 'chunked':
				response = requests.get(url, headers={'Range': 'bytes=0-0'}, allow_redirects=follow_redirects) #grab the first byte
				self.file_size = int(response.headers.get('Content-Range', 'bytes 0-0/*').split('/')[-1])

		if self.file_size < 0:
			raise Exception(f"Failed to determine file size for {url}")

		super().__init__(url, self.file_size)


	def _read_uncached_range(self, start, end) -> bytes:
		headers = {'Range': f'bytes={start}-{end-1}'}
		response = requests.get(self.path, headers=headers, allow_redirects=self.follow_redirects)
		if response.status_code in (200, 206):
			return response.content
		else:
			raise Exception(f"Failed to read file range {start}-{end} for {self.path}, status code: {response.status_code}")
