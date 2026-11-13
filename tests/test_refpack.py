"""ra3voice.refpack.unpack: a whole RefPack stream is decompressed, anything else is returned as it is."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ra3voice import refpack  # noqa: E402


def test_a_refpack_stream_is_decompressed():
    d = bytes(range(256)) * 50
    assert refpack.unpack(refpack.compress_literal(d)) == d


def test_an_uncompressed_stream_whose_hash_looks_like_the_signature_is_kept():
    """CampAISkMT20Mt's compiled map.relo began d1 fb 9e 48 (the stream's hash): is_refpack true, but no RefPack
    stream -- the build fell over decompressing it (B round 158)."""
    d = bytes.fromhex('d1fb9e48100000000800000040000000') + bytes(range(200))
    assert refpack.is_refpack(d)
    assert refpack.unpack(d) == d
