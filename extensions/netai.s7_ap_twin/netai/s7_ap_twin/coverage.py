import math

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt

from .config import ANIM_FPS, ANIM_RIPPLE_COUNT, ANIM_TOTAL_FRAMES
from .materials import bind_material, make_coverage_material


def _build_ring_mesh(inner_r: float, outer_r: float, segments: int = 48):
    points, f_counts, f_indices = [], [], []
    for i in range(segments):
        theta = (2 * math.pi) * (i / segments)
        c, s = math.cos(theta), math.sin(theta)
        points.append(Gf.Vec3f(inner_r * c, 0.0, inner_r * s))
        points.append(Gf.Vec3f(outer_r * c, 0.0, outer_r * s))
    for i in range(segments):
        nxt = (i + 1) % segments
        i0, i1 = 2*i,   2*i+1
        i2, i3 = 2*nxt, 2*nxt+1
        f_counts.append(4)
        f_indices.extend([i0, i1, i3, i2])
    return Vt.Vec3fArray(points), Vt.IntArray(f_counts), Vt.IntArray(f_indices)


def _build_disk_mesh(radius: float, segments: int = 48):
    points = [Gf.Vec3f(0.0, 0.0, 0.0)]
    f_counts, f_indices = [], []
    for i in range(segments):
        theta = (2 * math.pi) * (i / segments)
        points.append(Gf.Vec3f(radius * math.cos(theta), 0.0, radius * math.sin(theta)))
    for i in range(segments):
        nxt = (i + 1) % segments
        f_counts.append(3)
        f_indices.extend([0, i+1, nxt+1])
    return Vt.Vec3fArray(points), Vt.IntArray(f_counts), Vt.IntArray(f_indices)


def make_flat_coverage(
    stage,
    base_path: str,
    radius: float,
    color: Gf.Vec3f,
    opacity: float = 0.30,
) -> None:
    cov_path = f"{base_path}/Coverage"
    UsdGeom.Xform.Define(stage, cov_path)

    SEGS   = 48
    RING_W = radius * 0.06

    core_r   = radius * 0.20
    core_pts, core_fc, core_fi = _build_disk_mesh(core_r, SEGS)
    core      = UsdGeom.Mesh.Define(stage, f"{cov_path}/CoreDisk")
    core.GetPointsAttr().Set(core_pts)
    core.GetFaceVertexCountsAttr().Set(core_fc)
    core.GetFaceVertexIndicesAttr().Set(core_fi)
    core.GetDoubleSidedAttr().Set(True)
    core.GetSubdivisionSchemeAttr().Set(UsdGeom.Tokens.none)
    core_mat = make_coverage_material(stage, f"{cov_path}/CoreMat", color, opacity)
    bind_material(core.GetPrim(), core_mat)

    for idx in range(ANIM_RIPPLE_COUNT):
        phase  = idx / ANIM_RIPPLE_COUNT
        init_r = radius * 0.01
        init_pts, init_fc, init_fi = _build_ring_mesh(
            max(0.0, init_r - RING_W*0.5), init_r + RING_W*0.5, SEGS)

        rp = UsdGeom.Mesh.Define(stage, f"{cov_path}/Ripple{idx}")
        rp.GetPointsAttr().Set(init_pts)
        rp.GetFaceVertexCountsAttr().Set(init_fc)
        rp.GetFaceVertexIndicesAttr().Set(init_fi)
        rp.GetDoubleSidedAttr().Set(True)
        rp.GetSubdivisionSchemeAttr().Set(UsdGeom.Tokens.none)

        rp_mat = make_coverage_material(
            stage, f"{cov_path}/RippleMat{idx}", color, 0.0)
        bind_material(rp.GetPrim(), rp_mat)

        shader     = UsdShade.Shader(stage.GetPrimAtPath(f"{cov_path}/RippleMat{idx}/Shader"))
        op_input   = shader.GetInput("opacity_constant")
        pts_attr   = rp.GetPointsAttr()
        fc_attr    = rp.GetFaceVertexCountsAttr()
        fi_attr    = rp.GetFaceVertexIndicesAttr()

        for frame in range(ANIM_TOTAL_FRAMES):
            t       = ((frame / ANIM_TOTAL_FRAMES) + phase) % 1.0
            ring_r  = radius * t
            inner   = max(0.0, ring_r - RING_W*0.5)
            outer   = ring_r + RING_W*0.5
            ring_op = opacity * (1.0 - t)

            pts, fc, fi = _build_ring_mesh(inner, outer, SEGS)
            time = Usd.TimeCode(frame)
            pts_attr.Set(pts, time)
            fc_attr.Set(fc, time)
            fi_attr.Set(fi, time)
            op_input.Set(ring_op, time)

    stage.SetFramesPerSecond(ANIM_FPS)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(ANIM_TOTAL_FRAMES - 1)
    print(f"[coverage] baked {ANIM_TOTAL_FRAMES} frames @ {ANIM_FPS}fps for {base_path}")


def update_coverage(
    stage,
    base_path: str,
    radius: float,
    color: Gf.Vec3f,
    opacity: float = 0.30,
) -> None:
    cov_path  = f"{base_path}/Coverage"
    core_prim = stage.GetPrimAtPath(f"{cov_path}/CoreDisk")

    if core_prim.IsValid():
        pts   = UsdGeom.Mesh(core_prim).GetPointsAttr().Get()
        cur_r = abs(pts[1][0]) if (pts and len(pts) > 1) else -1.0

        cur_col = None
        shader_prim = stage.GetPrimAtPath(f"{cov_path}/CoreMat/Shader")
        if shader_prim.IsValid():
            inp = UsdShade.Shader(shader_prim).GetInput("diffuse_color_constant")
            if inp:
                cur_col = inp.Get()

        radius_same = abs(cur_r - radius * 0.20) < 5.0
        color_same  = (
            cur_col is not None
            and abs(cur_col[0] - color[0]) < 0.01
            and abs(cur_col[1] - color[1]) < 0.01
            and abs(cur_col[2] - color[2]) < 0.01
        )
        if radius_same and color_same:
            return

        stage.RemovePrim(Sdf.Path(cov_path))

    make_flat_coverage(stage, base_path, radius, color, opacity)
