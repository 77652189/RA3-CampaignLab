"""Write a read-only map review from a design, the build's answers and its renders."""

from collections import defaultdict
from html import escape
from pathlib import Path
from shutil import copyfile
from string import Template

import numpy as np
from PIL import Image

from experimental.campaign import maprender, mapstudy
from experimental.campaign.platmap import CONTAINER
from experimental.campaign.terrain_rules import CELL, WORLD_PER_OURS


PAGE = Template("""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>$title · 地图查看</title>
<style>
  :root { color-scheme: dark; font: 15px/1.5 system-ui, "Microsoft YaHei", sans-serif;
          color: #f4f3ea; background: #151c20; }
  * { box-sizing: border-box; }
  body { margin: 0; }
  main { max-width: 1800px; margin: auto; padding: clamp(14px, 2.5vw, 40px); }
  header { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between;
           gap: 6px 24px; margin-bottom: 18px; }
  h1, h2, p, figure { margin: 0; }
  h1 { font-size: clamp(26px, 3vw, 42px); line-height: 1.1; }
  h2 { font-size: 18px; margin-bottom: 10px; }
  a { color: #b3e6ef; }
  .layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(245px, 20%); gap: 20px; }
  .comparison { overflow-x: auto; }
  .pair, .gallery { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
  .pair { min-width: 530px; }
  .pair.single { grid-template-columns: 1fr; min-width: 0; }
  figcaption { margin: 6px 0 0; color: #dce2df; overflow-wrap: anywhere; }
  .map { position: relative; background: #0b1012; }
  .map img, .gallery img { display: block; width: 100%; height: auto; }
  .map svg { display: block; position: absolute; inset: 0; width: 100%; height: 100%; }
  .scale { position: absolute; bottom: 10px; left: 10px; color: white; font-size: 12px;
           text-shadow: 0 1px 3px black, 0 1px 5px black; pointer-events: none; white-space: nowrap; }
  .scale::after { content: ""; display: block; border: solid currentColor; border-width: 0 1px 2px;
                  height: 5px; filter: drop-shadow(0 1px 2px black); }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: center; margin-bottom: 10px; }
  .legend label, summary { cursor: pointer; }
  .key { border-left: 8px solid; padding-left: 5px; }
  .land-key { border-color: #94db9c; } .water-key { border-color: #67e0ff; }
  .ice-key { border-color: #cedcf5; }
  .road-key { border-color: #ffe197; } .border-key { border-color: #fbad84; }
  .passage-key { border-color: #edb3ff; } .point-key { border-color: #f5f8ff; }
  main:has(#design-toggle:not(:checked)) .design-layer { display: none; }
  .face { fill: #94db9c; fill-opacity: .14; stroke: #94db9c; stroke-opacity: .5; }
  .water { fill: #67e0ff; stroke: #67e0ff; }
  .ice { fill: #cedcf5; stroke: #cedcf5; }
  .road, .border, .passage { fill: none; stroke-width: 2; }
  .road { stroke: #ffe197; } .border { stroke: #fbad84; stroke-dasharray: 4 3; }
  .passage { stroke: #edb3ff; stroke-width: 3; }
  .point { fill: #f5f8ff; stroke: #182325; stroke-width: 1.5; }
  .building { fill: #e4c49a; stroke: #29251f; stroke-width: 2; }
  .protagonist { fill: #ffd680; }
  .highlight { fill: currentColor; fill-opacity: .19; stroke: currentColor; stroke-width: 4;
               pointer-events: none; filter: drop-shadow(0 1px 2px #080d10); }
  .witness { fill: none; stroke: #ff7777; }
  [hidden] { display: none; }
  .pass { --state: #a6ecc1; } .fail { --state: #ffac97; }
  .pending { --state: #ffe197; }
  .highlight, .verdict { color: var(--state); }
  aside { position: relative; }
  .relations { position: absolute; inset: 35px 0 0; overflow-y: auto; border-top: 1px solid #425058; }
  details { border-bottom: 1px solid #425058; padding: 8px; }
  details[open] { background: #26343a; }
  summary { display: grid; grid-template-columns: 3em 1fr .6em; gap: 8px; }
  summary::-webkit-details-marker { display: none; }
  summary::after { content: "›"; color: #b2c3c7; line-height: 1.5; }
  details[open] summary::after { transform: rotate(90deg); }
  .verdict { font-weight: 700; }
  .detail { margin-top: 8px; padding-left: 8px; border-left: 2px solid var(--state); overflow-wrap: anywhere; }
  .detail p + p { margin-top: 5px; }
  .id { color: #b2c3c7; font: 13px/1.5 ui-monospace, monospace; }
  section { margin-top: 24px; }
  @media (max-width: 910px) { .layout { grid-template-columns: minmax(0, 1fr); } .relations { position: static; } }
</style>
</head>
<body>
<main>
  <header><h1>$title</h1><a href="summary.md">关系诊断文本</a></header>
  <div class="layout">
    <div>
      <div class="legend">
        <label><input type="checkbox" id="design-toggle" checked> 设计层</label>
        <span class="key land-key">陆地</span><span class="key water-key">水面</span>
        $ice_key
        <span class="key road-key">路</span><span class="key border-key">界</span>
        <span class="key passage-key">过口</span><span class="key point-key">点</span>
      </div>
      <div class="comparison">
        <div class="pair$pair_class">
          <figure>
            <div class="map" id="built-map">
              <img src="built.png" alt="生成图俯视">
              <svg viewBox="0 0 $width $height" stroke-linecap="round" stroke-linejoin="round"
                   aria-label="设计和关系位置">
                <defs>$definitions</defs>$buildings<g class="design-layer">$design_layer</g>$highlights
              </svg>
              <span class="scale" style="width:$scale_percent%">↑ 北 · $scale 世界单位</span>
            </div>
            <figcaption>$built_label</figcaption>
          </figure>
          $retail_panel
        </div>
      </div>
    </div>
    <aside>
      <h2>离线关系检查</h2>
      <div class="relations">$relations</div>
    </aside>
  </div>
  $bench
</main>
<script>
  const rows = [...document.querySelectorAll('details[data-relation]')];
  for (const row of rows) {
    row.addEventListener('toggle', () => {
      if (row.open) {
        for (const other of rows) {
          if (other !== row) other.open = false;
        }
      }
      document.querySelector('[data-highlight="' + row.dataset.relation + '"]')
        .toggleAttribute('hidden', !row.open);
    });
  }
</script>
</body>
</html>
""")


def render_overhead(map_file, output, bounds):
    """Render one world rectangle at four pixels per ten world units."""
    water = mapstudy.water_height(map_file)
    return maprender.render(map_file, output, bounds=bounds, px=4, plain=True, models=True,
                            water=water / WORLD_PER_OURS if water is not None else -float('inf'))


def _overlay(sketch, bounds):
    west, south, east, north = bounds
    radius = (east - west) / 130

    def xy(point):
        x, y = maprender.north_up(*map(float, point), north)
        return f'{x - west:g},{y:g}'

    def line(points):
        return f'M{" L".join(map(xy, points))}'

    def path(d, style):
        return f'<path d="{d}" {style} vector-effect="non-scaling-stroke"/>'

    children = defaultdict(list)
    for name, block in sketch.blocks.items():
        children[block.get('parent')].append(name)
    shapes = {}
    layer = []

    def add(name, kind, geometry, tooltip):
        shapes[name] = geometry
        layer.append(f'<use class="{kind}" href="#place-{escape(name)}"><title>'
                     f'{escape(tooltip)}</title></use>')

    for name, ring in sketch.rings.items():
        block = sketch.blocks[name]
        outline = ' '.join(line(r) + ' Z' for r in (ring, *(sketch.rings[n] for n in children[name])))
        kind = 'water' if block.get('kind') == 'water' else 'ice' if block['use'] == 'ice' else 'land'
        add(name, f'face {kind}', path(outline, 'fill-rule="evenodd"'),
            f'{name} · {block["use"]} · 高度档 {block["height"]}')
    for name in sketch.roads:
        add(name, 'road', path(line(sketch.lines[name]), 'fill="none"'), name)
    for name in sketch.borders:
        add(name, 'border', path(line(sketch.lines[name]), 'fill="none"'), name)
        sections = defaultdict(list)
        for a, b, _, _, section in sketch.border_sections(name):
            if section != name:
                sections[section].append(line((a, b)))
        for section, segments in sections.items():
            add(section, 'passage', path(' '.join(segments), 'fill="none"'), section)
    for name, point in sketch.points.items():
        x, y = xy(point['at']).split(',')
        caption = f'{name} · {point["use"]}' if point.get('use') else name
        add(name, 'point', f'<circle cx="{x}" cy="{y}" r="{radius:g}" vector-effect="non-scaling-stroke"/>', caption)

    definitions = ''.join(f'<g id="place-{escape(name)}">{shape}</g>' for name, shape in shapes.items())
    return definitions, ''.join(layer)


def write_preview(directory, built, *, title):
    """Write a review from the live terrain grid and layout, without a native map."""
    if built.sketch is None:
        raise ValueError('Map preview requires a design')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    border = CONTAINER[2]
    x0, y0, x1, y1 = built.frame.map_borders(border)[-1]
    area = np.s_[y0 + border:y1 + border, x0 + border:x1 + border]
    ground = built.ground
    depth = ground.waterline[area] - ground.raw[area]
    height = np.minimum(ground.raw[area] / 80, 100)[..., None]
    land = np.array([45, 67, 37]) + height
    water = np.array([67, 134, 160]) - np.clip(depth / 45, 0, 47)[..., None]
    pixels = np.where(depth[..., None] >= 0, water, land)
    pixels[ground.blocked[area]] *= .68
    if built.roadbed is not None:
        pixels[built.roadbed.paved[area]] = (139, 133, 120)
        y, x = np.ogrid[y0:y1, x0:x1]
        for bridge in built.roadbed.bridges:
            pixels[bridge.mask(x * CELL, y * CELL)] = (139, 133, 120)
    Image.fromarray(pixels[::-1].astype(np.uint8)).save(directory / 'built.png')
    bounds = tuple(n * CELL for n in (x0, y0, x1, y1))
    _write_viewer(directory, title, built.sketch, built.check_relations(), bounds, built=built)


def write_viewer(directory, *, title, sketch, answers, bounds, retail_label, screenshots=()):
    """Write index.html and summary.md next to built.png and retail.png of equal world extent."""
    _write_viewer(directory, title, sketch, answers, bounds, retail_label, screenshots)


def _write_viewer(directory, title, sketch, answers, bounds, retail_label=None, screenshots=(), *, built=None):
    directory = Path(directory)
    west, south, east, north = bounds
    width, height = east - west, north - south
    definitions, layer = _overlay(sketch, bounds)
    ordered = sorted(answers.items(), key=lambda item: item[1].status != 'fail')
    rows, highlights = [], []
    report = [f'# {title}', '']
    if retail_label is not None:
        report += [f'原厂对照：{retail_label}', '']
    for index, (name, answer) in enumerate(ordered):
        active = index == 0
        verdict = {'fail': '未通过', 'pending': '待展开', 'pass': '通过'}[answer.status]
        places = '、'.join(answer.place)
        rows.append(
            f'<details data-relation="{index}" class="{answer.status}"{" open" if active else ""}>'
            f'<summary><span class="verdict">{verdict}</span><span>{escape(answer.sentence)}</span></summary>'
            f'<div class="detail"><p class="id">{escape(name)}</p><p>位置　{escape(places)}</p>'
            + (f'<p>建议　{escape(answer.decision)}</p>' if answer.decision else '') + '</div></details>'
        )
        marks = ''.join(f'<use href="#place-{escape(place)}"/>' for place in answer.place)
        witness_text = ''
        if answer.witness:
            witness = answer.witness
            x, y = witness.at
            witness_text = f'{witness.place} ({x:g}, {y:g}) {witness.reason}'
            sx, sy = maprender.north_up(x, y, north)
            marks += (f'<circle class="witness" cx="{sx - west:g}" cy="{sy:g}" '
                      f'r="{max(6, width / 100):g}" vector-effect="non-scaling-stroke">'
                      f'<title>{escape(witness_text)}</title></circle>')
        highlights.append(f'<g class="highlight {answer.status}" data-highlight="{index}"'
                          f'{"" if active else " hidden"}>{marks}</g>')
        report.append(f'- {answer.status.upper()} `{name}` · {answer.sentence}')
        if answer.status == 'fail':
            locations = []
            for place in answer.place:
                point = sketch.points.get(place, sketch.blocks.get(place))
                at = f' ({point["at"][0]:g}, {point["at"][1]:g})' if point else ''
                locations.append(f'`{place}`{at}')
            report.append(f'  - 位置：{"、".join(locations)}。建议：{answer.decision}')
        elif answer.status == 'pending':
            report.append(f'  - {answer.decision}')
        if witness_text:
            report.append(f'  - 证据　{witness_text}')

    gallery = []
    for index, (caption, source) in enumerate(screenshots, start=1):
        dest = f'bench-{index}{source.suffix.lower()}'
        copyfile(source, directory / dest)
        gallery.append(f'<figure><a href="{dest}"><img src="{dest}" alt="{escape(caption)}" loading="lazy"></a>'
                       f'<figcaption>{escape(caption)}</figcaption></figure>')

    scale = 100 if width < 2000 else 500
    scale_percent = 100 * scale / width
    retail_panel = ''
    if retail_label is not None:
        retail_panel = (
            '<figure><div class="map"><img src="retail.png" alt="原厂地图俯视">'
            f'<span class="scale" style="width:{scale_percent:g}%">↑ 北 · {scale} 世界单位</span></div>'
            f'<figcaption>原厂对照 · {escape(retail_label)}</figcaption></figure>'
        )
    buildings = []
    diagnostics = []
    built_label = '生成图'
    if built is not None:
        built_label = {'sketch': '地形草图', 'layout': '布局', 'full': '成图布局'}[built.level]
        for title_text, messages, role in (('地形错误', built.ground.errors, 'alert'),
                                            ('地形提示', built.ground.issues, 'status')):
            if messages:
                report.extend(['', f'## {title_text}', '', *(f'- {msg}' for msg in messages)])
                items = ''.join(f'<li>{escape(msg)}</li>' for msg in messages)
                diagnostics.append(f'<section role="{role}"><h3>{title_text}</h3><ul>{items}</ul></section>')
        for _, group in built.layout.blocks:
            for b in group:
                x, y = maprender.north_up(b.x, b.y, north)
                kind = 'building protagonist' if b.protagonist else 'building'
                buildings.append(f'<circle class="{kind}" cx="{x - west:g}" cy="{y:g}" r="{CELL}">'
                                 f'<title>{escape(b.template)}</title></circle>')
    page = PAGE.substitute(
        title=escape(title), built_label=built_label, retail_panel=retail_panel,
        pair_class='' if retail_panel else ' single', buildings=''.join(buildings),
        ice_key='<span class="key ice-key">河冰</span>' if any(b['use'] == 'ice' for b in sketch.blocks.values()) else '',
        width=f'{width:g}', height=f'{height:g}', scale=scale, scale_percent=f'{scale_percent:g}',
        definitions=definitions, design_layer=layer, highlights=''.join(highlights),
        relations=''.join(diagnostics) + (''.join(rows) or '<p>这张设计没有声明关系。</p>'),
        bench=('<section><h2>实机截图</h2><div class="gallery">' + ''.join(gallery) + '</div></section>')
        if gallery else '',
    )
    (directory / 'summary.md').write_text('\n'.join(report) + '\n', encoding='utf-8', newline='\n')
    (directory / 'index.html').write_text(page, encoding='utf-8', newline='\n')
