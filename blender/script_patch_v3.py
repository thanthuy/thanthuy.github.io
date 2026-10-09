# Patch du fichier de l'utilisateur : torsion du câble + câble rangé au plan 4.
import bpy, sys
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=sys.argv[1])
s = bpy.context.scene
S1, S2, S3, S4, END = 1, 73, 145, 217, 264
mm = lambda x, y, z: Vector((x / 1000, y / 1000, z / 1000))
path = bpy.data.objects['Trajet_Solid76']; cd = path.data; sp = cd.splines[0]
plug = bpy.data.objects['Fiche_Solid78']

cd.twist_mode = 'MINIMUM'                  # Z_UP tordait la partie verticale de 90°
for bp in sp.bezier_points: bp.tilt = 0.0

for idb in (cd, plug):                     # on refait uniquement ces clés-là
    if idb.animation_data: idb.animation_data_clear()

A, B, C, D = mm(-5.4, -20.9, -7.8), mm(-17.0, -20.9, -7.1), mm(-20.3, -20.9, -4.6), mm(-20.3, -20.9, -1.7)
D1, DF = mm(-40.0, -22.0, -1.7), mm(-62.0, -36.0, 58.0)
MF = mm(-62.0, -32.0, -6.0)
AX0, AXF = Vector((0, 0, 1)), Vector((-0.35, -0.15, 1)).normalized()
O0, O1 = S3 + 6, S3 + 50                   # sortie (plan 3)
R0, R1 = S4 + 2, S4 + 38                   # rentrée (plan 4)
def smooth(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def bez(p0, p1, p2, u): return (1-u)**2 * p0 + 2*(1-u)*u * p1 + u*u * p2
def amount(f):
    if f < S4: return smooth((f - O0) / (O1 - O0))
    return 1.0 - smooth((f - R0) / (R1 - R0))
prev = None
for f in range(S1, END + 1):
    u = amount(f)
    if u < 0.25:
        v = smooth(u / 0.25); d = D.lerp(D1, v); m = C.lerp(C + (D1 - D) * 0.6, v); ax = AX0
    else:
        v = smooth((u - 0.25) / 0.75)
        d = bez(D1, mm(-75.0, -32.0, 5.0), DF, v); m = (C + (D1 - D) * 0.6).lerp(MF, v)
        ax = AX0.slerp(AXF, v)
    P = [A, B, m, d]
    tg = [(B - A).normalized(), (m - A).normalized(), (d - B).normalized(), ax]
    for i, bp in enumerate(sp.bezier_points):
        bp.handle_left_type = bp.handle_right_type = 'FREE'
        bp.co = P[i]
        ll = (P[i] - P[i-1]).length / 3 if i > 0 else 0.002
        lr = (P[i+1] - P[i]).length / 3 if i < 3 else 0.002
        bp.handle_left = P[i] - tg[i] * ll; bp.handle_right = P[i] + tg[i] * lr
        for prop in ("co", "handle_left", "handle_right"): bp.keyframe_insert(prop, frame=f)
    plug.location = d; plug.keyframe_insert("location", frame=f)
    e = AX0.rotation_difference(ax).to_euler('XYZ', prev) if prev else AX0.rotation_difference(ax).to_euler()
    plug.rotation_euler = e; prev = e.copy(); plug.keyframe_insert("rotation_euler", frame=f)
def fcurves(idb):
    a = idb.animation_data.action
    if hasattr(a, "fcurves"): return list(a.fcurves)
    return [fc for l in a.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]
for idb in (cd, plug):
    for fc in fcurves(idb):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
s.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[2], compress=True, relative_remap=False)
print("saved", sys.argv[2])
