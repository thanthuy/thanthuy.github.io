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

# ---------- câble plat rétractable (sort du chargeur, plan 3) ----------
s.frame_set(S2); bpy.context.view_layer.update()      # rotation 0 = pose de repos
import bmesh
def catmull(pts, n=24):
    P = [pts[0]] + pts + [pts[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i-1], P[i], P[i+1], P[i+2]
        for k in range(n):
            u = k / n
            out.append(0.5 * ((2*p1) + (-p0 + p2)*u + (2*p0 - 5*p1 + 4*p2 - p3)*u*u + (-p0 + 3*p1 - 3*p2 + p3)*u**3))
    out.append(pts[-1]); return out
ctrl = [Vector(v) for v in [(0.020,-0.008,-0.012),(0.020,-0.008,-0.035),(0.018,-0.012,-0.070),(0.035,-0.020,-0.108),
        (0.075,-0.022,-0.120),(0.110,-0.016,-0.092),(0.124,-0.010,-0.040),(0.125,-0.006,0.020),(0.121,-0.002,0.058)]]
dense = catmull(ctrl)
cum = [0.0]
for i in range(1, len(dense)): cum.append(cum[-1] + (dense[i] - dense[i-1]).length)
TOT = cum[-1]; N = 240
def at(L):
    L = max(0.0, min(TOT, L))
    for i in range(1, len(cum)):
        if cum[i] >= L:
            u = (L - cum[i-1]) / max(cum[i] - cum[i-1], 1e-9); return dense[i-1].lerp(dense[i], u)
    return dense[-1]
pts = [at(TOT * i / (N - 1)) for i in range(N)]       # points équidistants -> facteur = longueur

cd = bpy.data.curves.new("Cable_Plat", 'CURVE'); cd.dimensions = '3D'; cd.twist_mode = 'MINIMUM'
cd.extrude = 0.0019; cd.bevel_depth = 0.0006; cd.bevel_resolution = 3; cd.use_fill_caps = True
cd.bevel_factor_mapping_end = 'SPLINE'
sp = cd.splines.new('POLY'); sp.points.add(N - 1)
for i, p in enumerate(pts): sp.points[i].co = (p.x, p.y, p.z, 1); sp.points[i].tilt = 0.0
cable_obj = bpy.data.objects.new("Cable_Plat", cd); coll.objects.link(cable_obj)
m_cab = bpy.data.materials.new("Cable_Plat_Blanc"); m_cab.use_nodes = True
bs = m_cab.node_tree.nodes['Principled BSDF']; bs.inputs['Base Color'].default_value = (0.85, 0.85, 0.87, 1); bs.inputs['Roughness'].default_value = 0.3
cd.materials.append(m_cab)

# fiche USB-C (origine = jonction câble, longueur vers +Z local)
def box(bm, sx, sy, z0, z1):
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        if not v.tag:
            v.co = Vector((v.co.x * sx, v.co.y * sy, z0 + (v.co.z + 0.5) * (z1 - z0))); v.tag = True
def plug_part(name, sx, sy, z0, z1, mat, bev):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); box(bm, sx, sy, z0, z1); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); me.materials.append(mat)
    md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bev; md.segments = 4
    o.modifiers.new("Smooth", 'WEIGHTED_NORMAL'); return o
m_al = bpy.data.materials.new("USBC_Aluminium"); m_al.use_nodes = True
b2 = m_al.node_tree.nodes['Principled BSDF']; b2.inputs['Base Color'].default_value = (0.8, 0.8, 0.82, 1)
b2.inputs['Metallic'].default_value = 1.0; b2.inputs['Roughness'].default_value = 0.22
m_bl = bpy.data.materials.new("USBC_Interieur"); m_bl.use_nodes = True
m_bl.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.01, 0.01, 0.01, 1)
plug = bpy.data.objects.new("Fiche_USB_C", None); plug.empty_display_size = 0.01; coll.objects.link(plug)
for o in [plug_part("USBC_Gaine", 0.0062, 0.0026, 0.0, 0.007, m_cab, 0.0009),
          plug_part("USBC_Corps", 0.0078, 0.0034, 0.006, 0.019, m_al, 0.0012),
          plug_part("USBC_Embout", 0.0083, 0.0026, 0.019, 0.0275, m_al, 0.0011),
          plug_part("USBC_Languette", 0.0060, 0.0010, 0.0245, 0.0277, m_bl, 0.0003)]:
    o.parent = plug

for o in (cable_obj, plug):
    o.parent = pivot; o.matrix_parent_inverse = pivot.matrix_world.inverted()

O0, O1 = S3 + 8, S3 + 52                                 # sortie du câble
def smooth(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
prev = None
for f in range(S1, END + 1):
    u = smooth((f - O0) / (O1 - O0)); L = 0.004 + u * (TOT - 0.004)
    cd.bevel_factor_end = L / TOT; cd.keyframe_insert("bevel_factor_end", frame=f)
    p = at(L); tng = (at(L + 0.002) - at(L - 0.002)).normalized()
    plug.location = p; plug.keyframe_insert("location", frame=f)
    e = tng.to_track_quat('Z', 'Y').to_euler('XYZ', prev) if prev else tng.to_track_quat('Z', 'Y').to_euler()
    plug.rotation_euler = e; prev = e.copy(); plug.keyframe_insert("rotation_euler", frame=f)
for idb in (cd, plug):
    for fc in fcurves(idb):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
for o in [cable_obj, plug] + list(plug.children):                  # rangé = invisible avant le plan 3
    o.hide_render = True; o.keyframe_insert("hide_render", frame=S1)
    o.hide_render = False; o.keyframe_insert("hide_render", frame=O0)
print("cable length", TOT)

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

CAB = Vector((0.045, -0.012, -0.022))
c3 = cam("Cam3_Cable", 85)
aim(c3, S3, orbit(CAB, 0.74, 14, 10), CAB)
aim(c3, S4 - 1, orbit(CAB, 0.90, 4, 8), CAB)

MID = Vector((0.012, -0.010, -0.055))
c4 = cam("Cam4_Final", 85)
aim(c4, S4, orbit(MID, 0.80, 15, 10), MID)
aim(c4, END, orbit(MID, 1.08, 5, 12), MID)
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
