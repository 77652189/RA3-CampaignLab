"""Content keys for test-only caches. A module of its own: `from conftest import` reaches whichever conftest
was imported last, tests/modules' one included."""
import hashlib
import os
from pathlib import Path


def content_key(*paths):
    """Key test-only reuse on paths and bytes, including additions and removals in input trees."""
    digest = hashlib.sha256()
    for path in dict.fromkeys(map(Path, paths)):
        digest.update(os.fsencode(path) + b'\0')
        files = [path]
        if path.is_dir():
            files = sorted(p for p in path.rglob('*') if p.is_file() and p.suffix != '.pyc')
        for file in files:
            digest.update(os.fsencode(file) + b'\0')
            if file.is_file():
                with file.open('rb') as source:
                    digest.update(hashlib.file_digest(source, 'sha256').digest())
    return digest.digest()
