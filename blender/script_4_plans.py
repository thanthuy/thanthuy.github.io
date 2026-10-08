import bpy, sys, math
from mathutils import Vector
src, dst = sys.argv[1], sys.argv[2]
bpy.ops.wm.open_mainfile(filepath=src)
s = bpy.context.scene
FPS = 24
S1, S2, S3, S4 = 1, 73, 145, 217      # 3s / 3s / 3s / 2s
END = 264
s.render.fps = FPS; s.frame_start, s.frame_end = S1, END
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1080, 1920, 100

def fcurves(idb):
    a = idb.animation_data.action
    if hasattr(a, "fcurves"): return list(a.fcurves)
    return [fc for l in a.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]
def ease(idb, kind='BEZIER'):
    for fc in fcurves(idb):
        for m in list(fc.modifiers): fc.modifiers.remove(m)
        for kp in fc.keyframe_points: kp.interpolation = kind; kp.easing = 'AUTO'
def key(obj, path, frame, value, index=-1):
    setattr(obj, path, value) if index < 0 else getattr(obj, path).__setitem__(index, value)
    obj.keyframe_insert(path, index=index, frame=frame)

C = Vector((0.005, -0.008, 0.007))           # centre du chargeur
pivot = bpy.data.objects['Chargeur_Rotation']
cable = bpy.data.objects['T29二代五金快充线(3):1']
coll = pivot.users_collection[0]

# ---------- rotation du chargeur ----------
pivot.animation_data_clear()
R = math.radians
for f, a in [(S1, -200), (S2 - 1, 0),       # plan 1 : tourne (fini face logo)
             (S2, 0), (S3 - 1, 0),          # plan 2 : fixe, logo face caméra
             (S3, 25), (S4 - 1, 35),        # plan 3 : léger 3/4 pour voir le câble
             (S4, 35), (END, 58)]:          # plan 4 : tourne doucement
    key(pivot, "rotation_euler", f, R(a), 2)
ease(pivot)

# ---------- câble qui sort ----------
bpy.context.view_layer.update()
top = None
for o in cable.children_recursive:
    if o.type == 'MESH':
        for v in o.data.vertices:
            p = o.matrix_world @ v.co
            if top is None or p.z > top.z: top = p
print("cable attach", top)
reel = bpy.data.objects.new("Cable_Sortie", None); reel.empty_display_size = 0.02
coll.objects.link(reel)
reel.location = top; reel.parent = pivot
reel.matrix_parent_inverse = pivot.matrix_world.inverted()
bpy.context.view_layer.update()
mw = cable.matrix_world.copy()
cable.parent = reel; cable.matrix_parent_inverse = reel.matrix_world.inverted()
cable.matrix_world = mw
TINY = 0.001
key(reel, "scale", S1, (TINY,) * 3)
key(reel, "scale", S3 + 6, (TINY,) * 3)
key(reel, "scale", S3 + 36, (1.04, 1.04, 1.04))
key(reel, "scale", S3 + 46, (1, 1, 1))
ease(reel)
for o in [cable] + list(cable.children_recursive):   # invisible tant que rentré
    o.hide_render = True; o.keyframe_insert("hide_render", frame=S1)
    o.hide_render = False; o.keyframe_insert("hide_render", frame=S3 + 6)
    o.hide_viewport = True; o.keyframe_insert("hide_viewport", frame=S1)
    o.hide_viewport = False; o.keyframe_insert("hide_viewport", frame=S3 + 6)

# ---------- 4 caméras ----------
def cam(name, lens):
    d = bpy.data.cameras.new(name); d.lens = lens; d.sensor_fit = 'AUTO'; d.sensor_width = 36
    d.clip_start = 0.005; d.dof.use_dof = True; d.dof.aperture_fstop = 4.0
    o = bpy.data.objects.new(name, d); coll.objects.link(o); return o
def aim(o, frame, pos, target, fdist=None):
    o.location = Vector(pos); o.keyframe_insert("location", frame=frame)
    o.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    o.keyframe_insert("rotation_euler", frame=frame)
    o.data.dof.focus_distance = (Vector(target) - Vector(pos)).length
    o.data.dof.keyframe_insert("focus_distance", frame=frame)

def orbit(target, dist, azim, elev):   # azim 0 = devant (-Y)
    a, e = math.radians(azim), math.radians(elev)
    return Vector(target) + dist * Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))

c1 = cam("Cam1_Plan_Large", 85)
aim(c1, S1, orbit(C, 0.62, 10, 12), C)
aim(c1, S2 - 1, orbit(C, 0.56, -5, 10), C)

LOGO = Vector((0.007, -0.030, 0.0065))
c2 = cam("Cam2_Logo_BONNE", 85)
aim(c2, S2, orbit(LOGO, 0.40, 6, 4), LOGO)
aim(c2, S2 + 40, orbit(LOGO, 0.36, 0, 1), LOGO)
aim(c2, S3 - 1, orbit(C, 0.62, -6, 8), C)            # dézoom

CAB = Vector((-0.03, -0.015, -0.055))
c3 = cam("Cam3_Cable", 85)
aim(c3, S3, orbit(CAB, 0.60, 18, 8), CAB)
aim(c3, S4 - 1, orbit(CAB, 0.66, 8, 10), CAB)

MID = Vector((-0.02, -0.008, -0.05))
c4 = cam("Cam4_Final", 85)
aim(c4, S4, orbit(MID, 0.70, 15, 10), MID)
aim(c4, END, orbit(MID, 0.88, 5, 12), MID)
for c in (c1, c2, c3, c4): ease(c)

# marqueurs = changement de caméra
s.timeline_markers.clear()
for f, c, n in [(S1, c1, "Plan1_Large"), (S2, c2, "Plan2_Logo"), (S3, c3, "Plan3_Cable"), (S4, c4, "Plan4_Final")]:
    m = s.timeline_markers.new(n, frame=f); m.camera = c
s.camera = c1

# ---------- lumière qui balaye le logo (plan 2) ----------
ld = bpy.data.lights.new("Lumiere_Balayage", 'AREA'); ld.shape = 'RECTANGLE'
ld.size, ld.size_y = 0.012, 0.25; ld.color = (1.0, 0.45, 0.85)
lo = bpy.data.objects.new("Lumiere_Balayage", ld); coll.objects.link(lo)
for f, x in [(S2, -0.16), (S3 - 20, 0.17)]:
    p = LOGO + Vector((x, -0.12, 0.02))
    lo.location = p; lo.keyframe_insert("location", frame=f)
    lo.rotation_euler = (LOGO - p).to_track_quat('-Z', 'Y').to_euler(); lo.keyframe_insert("rotation_euler", frame=f)
for f, e in [(S2 - 1, 0), (S2, 0), (S2 + 6, 1.2), (S3 - 22, 1.2), (S3 - 14, 0)]:
    ld.energy = e; ld.keyframe_insert("energy", frame=f)
ease(lo)

# l'ancienne caméra reste dans le fichier mais n'est plus utilisée
bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True, relative_remap=False)
print("saved", dst)
