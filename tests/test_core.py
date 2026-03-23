import pytest
import hashlib
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from RangeHTTPServer import RangeRequestHandler
import threading
import requests
from netpluck import netpluck

'''
Required packages
pip install rangehttpserver requests pytest
'''

@pytest.fixture(scope="module")
def local_mini_zip_path():
	return "tests/fixtures/mini.zip"

@pytest.fixture(scope="module")
def mini_files():
	return [
		# relative file path, md5 sum
		("mini/empty.txt","d41d8cd98f00b204e9800998ecf8427e"),
		("mini/lava.png","df51fdae12958ce4f1c4a8cca3c46bc7"),
		("mini/message.txt","abb1893b8010858291b3111f1c956a35"),
		("mini/nova.bmp","f4c4af4d604ee6ca35e8ca3ca83823bd"),
		("mini/triangles.png","0ecf34c5c1ca90112fd8c29f9bbad8c8"),
	]

@pytest.fixture(scope="module")
def http_server():
	# Note, we are using the RangeRequestHandler which adds support for byte-range requests
	class Handler(RangeRequestHandler):
		def log_message(self, format, *args):
			return

	# note if we use localhost, it uses AF_INET6 and some http clients have issues with that, so we will use IPV4
	#httpd = HTTPServer(('localhost', 0), Handler)
	httpd = HTTPServer(('127.0.0.1', 0), Handler)
	port = httpd.server_port

	thread = threading.Thread(target=httpd.serve_forever)
	thread.daemon = True
	thread.start()

	yield f"http://127.0.0.1:{port}/tests/fixtures/mini.zip"

	httpd.shutdown()
	thread.join()

def helper_check_toc(np, mini_files):
	toc = np.get_file_list()

	# make sure every file in mini_files is in the toc
	for file_path,checksum in mini_files:
		assert file_path in toc

def test_local_zip_toc(local_mini_zip_path, mini_files):
	np = netpluck.NetPluck(local_mini_zip_path)
	helper_check_toc(np, mini_files)

def test_http_zip_toc(http_server, mini_files):
	url = str(http_server)
	np = netpluck.NetPluck(url)
	helper_check_toc(np, mini_files)

def helper_check_for_file(np, mini_files):
	# make sure every file in mini_files is in the toc
	for file_path,checksum in mini_files:
		file_bytes = np.get_file(file_path)
		file_checksum = hashlib.md5(file_bytes).hexdigest()
		assert file_checksum == checksum

def test_local_zip_extract_to_memory(local_mini_zip_path, mini_files):
	np = netpluck.NetPluck(local_mini_zip_path)
	helper_check_for_file(np, mini_files)

def test_http_zip_extract_to_memory(http_server, mini_files):
	url = str(http_server)
	np = netpluck.NetPluck(url)
	helper_check_for_file(np, mini_files)

def helper_check_for_extraction(np, mini_files, tmp_path):
	output_dir = tmp_path / "output"
	output_dir.mkdir()

	for file_path,checksum in mini_files:
		extracted_path = np.extract(file_path, str(output_dir))

		# the extracted path should be output_dir / file_path
		expected_path = output_dir / file_path

		assert extracted_path == str(expected_path)

		with open(extracted_path, "rb") as f:
			file_bytes = f.read()
			file_checksum = hashlib.md5(file_bytes).hexdigest()
			assert file_checksum == checksum

def test_local_zip_extract_to_disk(tmp_path, local_mini_zip_path, mini_files):
	np = netpluck.NetPluck(local_mini_zip_path)
	helper_check_for_extraction(np, mini_files, tmp_path)

def test_http_zip_extract_to_disk(tmp_path, http_server, mini_files):
	url = str(http_server)
	np = netpluck.NetPluck(url)

	helper_check_for_extraction(np, mini_files, tmp_path)
