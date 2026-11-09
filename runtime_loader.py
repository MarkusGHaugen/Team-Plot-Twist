"""Refresh imported game modules after a live deployment, including warm workers."""
from pathlib import Path
import hashlib
import importlib
import sys
import threading

_lock = threading.RLock()
_revision = None
_NAMES = ('content', 'logic', 'escort', 'voyage', 'feast', 'shiplife', 'db', 'action_transport')

def load_backend(root: Path) -> str:
    global _revision
    sources = [(name, (root / (name + '.py')).read_bytes()) for name in _NAMES]
    revision = hashlib.sha256(b''.join(name.encode()+b'\0'+source for name,source in sources)).hexdigest()
    with _lock:
        if revision != _revision:
            importlib.invalidate_caches()
            for name,source in sources:
                module = sys.modules.get(name)
                if module is None:
                    importlib.import_module(name)
                else:
                    # Compile the checked bytes directly: a same-second update
                    # must not reuse timestamp-based Python bytecode.
                    exec(compile(source, str(root / (name+'.py')), 'exec'), module.__dict__)
            _revision = revision
    return revision
