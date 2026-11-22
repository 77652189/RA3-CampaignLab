"""SimAI.unpack: a structure's UnpackTime in frames, read by the shared duration parser (templates.secs) -- '500ms'
is a legal SAGE duration (review rr #3: after core step 4 every AI placement asks it, and '500ms' threw)."""
from types import SimpleNamespace as NS

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.ai.core as simai  # noqa: E402


def frames(value):
    module = NS(attrs={} if value is None else {'UnpackTime': value})
    host = NS(lib=NS(template=lambda t: NS(first=lambda name: module)))
    return simai.SimAI.unpack(host, 'AlliedPowerPlant')


def test_unpack_time_in_seconds_or_milliseconds_is_frames():
    assert [frames(v) for v in ('500ms', '0.5s', '2s', None)] == [8, 8, 30, 0]


def test_the_template_readers_read_milliseconds_the_same_way():
    """Review ss #5: simunits' own parser (UnpackTime, PackTime, TimePerPassenger, weapon timers ...) read '500ms' as 0."""
    import engine.data.units as simunits
    assert [simunits._frames(simunits._secs(v)) for v in ('500ms', '0.5s', '2s', None)] == [8, 8, 30, 0]
