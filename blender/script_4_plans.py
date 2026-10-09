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
             (S3, 15), (S4 - 1, 22),        # plan 3 : léger 3/4 pour voir le câble
             (S4, 22), (END, 50)]:          # plan 4 : tourne doucement
    key(pivot, "rotation_euler", f, R(a), 2)
ease(pivot)

# ---------- on tire le câble Solid76 (plan 3) ----------
# Solid76 = câble plat existant ; Solid78 + Solid84 = fiche USB-C rangée dans sa rainure.
s.frame_set(S2); bpy.context.view_layer.update()      # rotation 0 = pose de repos
import bmesh
mm = lambda x, y, z: Vector((x / 1000, y / 1000, z / 1000))
cab = bpy.data.objects['Solid76']
orig = cab.data; orig.use_fake_user = True; orig.name = "Solid76_forme_origine"   # géométrie d'origine gardée
mat = orig.materials[0]

# trajet (repos = forme en L d'origine de Solid76)
A, B, C, D = mm(-5.4, -20.9, -7.8), mm(-17.0, -20.9, -7.1), mm(-20.3, -20.9, -4.6), mm(-20.3, -20.9, -1.7)
cd = bpy.data.curves.new("Trajet_Solid76", 'CURVE'); cd.dimensions = '3D'
cd.use_path = True; cd.use_stretch = True; cd.use_deform_bounds = True; cd.twist_mode = 'Z_UP'
sp = cd.splines.new('BEZIER'); sp.bezier_points.add(3)
for bp, p in zip(sp.bezier_points, (A, B, C, D)):
    bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
path = bpy.data.objects.new("Trajet_Solid76", cd); coll.objects.link(path); path.hide_render = True
path.parent = pivot; path.matrix_parent_inverse = pivot.matrix_world.inverted()

# Solid76 devient une bande droite (même section 5 x 1,2 mm, même matériau) déformée le long du trajet
W, T, NS = 0.0050, 0.0012, 300
me = bpy.data.meshes.new("Solid76"); bm = bmesh.new()
rows = []
for i in range(NS + 1):
    x = i / NS
    rows.append([bm.verts.new((x, y, z)) for y, z in ((-W/2, -T/2), (W/2, -T/2), (W/2, T/2), (-W/2, T/2))])
for i in range(NS):
    for k in range(4):
        bm.faces.new((rows[i][k], rows[i][(k+1) % 4], rows[i+1][(k+1) % 4], rows[i+1][k]))
bm.faces.new(rows[0][::-1]); bm.faces.new(rows[-1])
bm.to_mesh(me); bm.free()
for poly in me.polygons: poly.use_smooth = True
me.materials.append(mat)
cab.data = me
cab.matrix_world = path.matrix_world.copy()
md = cab.modifiers.new("Tirer_Cable", 'CURVE'); md.object = path; md.deform_axis = 'POS_X'
bev = cab.modifiers.new("Bevel", 'BEVEL'); bev.width = 0.0004; bev.segments = 2

# fiche : Solid78 + Solid84 sur un Empty à la base de la fiche (axe +Z)
plug = bpy.data.objects.new("Fiche_Solid78", None); plug.empty_display_size = 0.01; coll.objects.link(plug)
plug.location = D; plug.parent = pivot; plug.matrix_parent_inverse = pivot.matrix_world.inverted()
bpy.context.view_layer.update()
for n in ("Solid78", "Solid84"):
    o = bpy.data.objects[n]; mw = o.matrix_world.copy()
    o.parent = plug; o.matrix_parent_inverse = plug.matrix_world.inverted(); o.matrix_world = mw

O0, O1 = S3 + 6, S3 + 50
D1 = mm(-40.0, -22.0, -1.7)                  # fiche sortie de sa rainure (vers -X)
DF = mm(-62.0, -36.0, 58.0)                  # position finale, en haut à gauche
M0, MF = C, mm(-62.0, -32.0, -6.0)          # milieu du câble : forme un arc
AX0, AXF = Vector((0, 0, 1)), Vector((-0.35, -0.15, 1)).normalized()
def smooth(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def bez(p0, p1, p2, u): return (1-u)**2 * p0 + 2*(1-u)*u * p1 + u*u * p2
prev = None
for f in range(S1, END + 1):
    u = smooth((f - O0) / (O1 - O0))
    if u < 0.25:
        v = u / 0.25; d = D.lerp(D1, smooth(v)); m = C.lerp(C + (D1 - D) * 0.6, smooth(v)); ax = AX0
    else:
        v = smooth((u - 0.25) / 0.75)
        d = bez(D1, mm(-75.0, -32.0, 5.0), DF, v)
        m = (C + (D1 - D) * 0.6).lerp(MF, v)
        ax = AX0.slerp(AXF, v) if hasattr(AX0, "slerp") else AX0.lerp(AXF, v).normalized()
    pts = sp.bezier_points
    P = [A, B, m, d]
    tg = [(B - A).normalized(), (m - A).normalized(), (d - B).normalized(), ax]
    for i, bp in enumerate(pts):
        bp.handle_left_type = bp.handle_right_type = 'FREE'
        bp.co = P[i]
        ll = (P[i] - P[i-1]).length / 3 if i > 0 else 0.002
        lr = (P[i+1] - P[i]).length / 3 if i < 3 else 0.002
        bp.handle_left = P[i] - tg[i] * ll; bp.handle_right = P[i] + tg[i] * lr
        for prop in ("co", "handle_left", "handle_right"): bp.keyframe_insert(prop, frame=f)
    plug.location = d; plug.keyframe_insert("location", frame=f)
    e = AX0.rotation_difference(ax).to_euler('XYZ', prev) if prev else AX0.rotation_difference(ax).to_euler()
    plug.rotation_euler = e; prev = e.copy(); plug.keyframe_insert("rotation_euler", frame=f)
for idb in (cd, plug):
    for fc in fcurves(idb):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'

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

CAB = Vector((-0.022, -0.02, 0.012))
c3 = cam("Cam3_Cable", 85)
aim(c3, S3, orbit(CAB, 0.55, -24, 10), CAB)
aim(c3, S4 - 1, orbit(CAB, 0.62, -14, 8), CAB)

MID = Vector((-0.03, -0.010, -0.045))
c4 = cam("Cam4_Final", 85)
aim(c4, S4, orbit(MID, 0.70, 0, 10), MID)
aim(c4, END, orbit(MID, 1.00, -8, 12), MID)
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
