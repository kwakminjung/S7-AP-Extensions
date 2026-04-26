import omni.usd
from pxr import Gf, Sdf, UsdGeom, Vt

from .config import MARKER_PATH


def create_marker(stage, x: float, y: float, z: float) -> None:
    if stage.GetPrimAtPath(MARKER_PATH).IsValid():
        stage.RemovePrim(Sdf.Path(MARKER_PATH))

    sphere = UsdGeom.Sphere.Define(stage, MARKER_PATH)
    sphere.GetRadiusAttr().Set(30.0)
    sphere.GetDisplayColorAttr().Set(Vt.Vec3fArray([Gf.Vec3f(1.0, 0.2, 0.2)]))
    UsdGeom.XformCommonAPI(sphere).SetTranslate(Gf.Vec3d(x, y, z))

    omni.usd.get_context().get_selection().set_selected_prim_paths(
        [MARKER_PATH], True
    )


def delete_marker(stage) -> None:
    if stage.GetPrimAtPath(MARKER_PATH).IsValid():
        stage.RemovePrim(Sdf.Path(MARKER_PATH))


def get_marker_world_position(stage) -> tuple[float, float, float] | None:
    prim = stage.GetPrimAtPath(MARKER_PATH)
    if not prim.IsValid():
        return None
    from pxr import Usd
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    t = cache.GetLocalToWorldTransform(prim).ExtractTranslation()
    return t[0], t[1], t[2]
