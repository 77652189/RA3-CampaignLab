"""L6 script conditions on what the player is shown (ADR 0029, docs/engine/sim-layers.md; L6 presentation): the camera
having been in an area, a sound or a movie finished.

Each condition is `fn(sim, name, a)`, moved verbatim out of Sim.cond's chain; simcond.cond looks them up in
CONDITIONS."""


def camera_entered_area(sim, name, a):
    # bench 11-14 engine_eyes all 镜头: holds for good once the camera's point (where it looks) has been in the
    # area -- A and M on from s1 to the end though the camera left; the player's own camera (a minimap click)
    # latches too; strips 110-1900 round the point never (not the eye, not the view)
    return a[0] in sim.camera_been


def has_finished_audio(sim, name, a):
    # never played: true (l2_scripts1 2.3; bench 11-08 cond)
    return sim.t >= sim.audio_end.get(a[0], 0.0)


def has_finished_video(sim, name, a):
    # never played: false (bench 11-08 cond); full screen: never (movie.py)
    end = sim.video_end.get(a[0])
    return end is not None and sim.t >= end


CONDITIONS = {
    'CAMERA_ENTERED_AREA': camera_entered_area,
    'HAS_FINISHED_AUDIO': has_finished_audio,
    'HAS_FINISHED_VIDEO': has_finished_video,
}
