from .base import VirtualFile
from .http import VirtualFileHTTP
from .local import VirtualFileLocal
try:
	from .backblaze import VirtualFileBackblaze
except ImportError:
	pass
