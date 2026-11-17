"""For probe builds on a map whose `start` site is too near the edge (K5, contract.start_camera_inside_the_view): the
first picture would show black beyond the border. open_in_view(m, tag) publishes a view point -- the start pulled inside
the rect where the screen's centre stays on the map (the map's first border, as the contract reads it) -- and a script
with no condition that moves the camera there. A probe's own checks may move the camera later as they please."""
import model


def open_in_view(m, tag):
    borders = getattr(m.map, 'BORDERS', None) or {}
    start = (getattr(m.map, 'SITES', None) or {}).get('start')
    if not borders or start is None:
        return m
    x0, y0, x1, y1 = rect = model.view_rect([next(iter(borders.values()))])
    x, y = min(max(start.x, x0), x1), min(max(start.y, y0), y1)
    name = f'CNV {tag} Opening'
    m.waypoint('opening view', name, 'start', x - start.x, y - start.y)
    m.views[name] = rect
    m.scripts.append(model.Script(f'CNV {tag} - opening view', [], [('MOVE_CAMERA_TO', name, 0.1, 0.0, 0.0, 0.0)]))
    return m
