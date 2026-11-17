"""Regenerate display LOD meshes: blender -b --factory-startup --python <this-file>.

Uses Blender 4.2's Collada importer/exporter and Decimate, preserving UV/material boundaries.
Original source assets stay untouched. Blender is needed only to regenerate assets, not to run Gazebo.
"""
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import bpy

root = Path(__file__).resolve().parent / 'x500/meshes'
out = root / 'lod'
out.mkdir(exist_ok=True)
counts = {}
for name, ratio in [('NXP-HGD-CF.dae', .12), ('5010Base.dae', .2), ('5010Bell.dae', .2),
                    ('1345_prop_cw.stl', .2), ('1345_prop_ccw.stl', .2)]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if name.endswith('.stl'):
        bpy.ops.wm.stl_import(filepath=str(root / name))
    else:
        bpy.ops.wm.collada_import(filepath=str(root / name), import_units=False)
    before = after = 0
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH':
            continue
        bpy.context.view_layer.objects.active = obj
        before += sum(len(p.vertices) - 2 for p in obj.data.polygons)
        modifier = obj.modifiers.new('Display LOD', 'DECIMATE')
        modifier.ratio, modifier.use_collapse_triangulate = ratio, True
        if name.endswith('.dae'):
            modifier.delimit = {'UV', 'MATERIAL'}
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        after += sum(len(p.vertices) - 2 for p in obj.data.polygons)
    dest = out / (Path(name).stem + '.dae')
    bpy.ops.wm.collada_export(filepath=str(dest), apply_modifiers=True, selected=False,
                             include_animations=False, triangulate=True, use_texture_copies=False)
    # Collada export writes absolute image paths; make them portable without rewriting the mesh XML.
    ns = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
    tree = ET.parse(dest)
    content = dest.read_text()
    for image in tree.findall('.//c:library_images/c:image/c:init_from', ns):
        if image.text and Path(image.text).is_absolute():
            content = content.replace(image.text, os.path.relpath(image.text, out))
    dest.write_text(content)
    counts[name] = {'original_triangles': before, 'lod_triangles': after}
    print(name, counts[name], flush=True)
(out / 'stats.json').write_text(json.dumps(counts, indent=2) + '\n')
