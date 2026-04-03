from .base import VirtualFile
from .http import VirtualFileHTTP
from .local import VirtualFileLocal
try:
	from .buckethandler import VirtualFileBucketHandler
except ImportError:
	pass
