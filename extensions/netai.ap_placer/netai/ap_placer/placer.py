import json

import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom

from .config import AP_LOCATIONS_JSON, FLOOR_CONFIG


def get_floor_bbox(stage, usd_path: str):
    prim = stage.GetPrimAtPath(usd_path)
    if not prim.IsValid():
        return None
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_],
        useExtentsHint=True,
    )
    rng = cache.ComputeWorldBound(prim).GetRange()
    if rng.IsEmpty():
        return None
    return rng.GetMin(), rng.GetMax()


def world_to_px(
    world_x: float, world_y: float,
    bbox, img_w: float, img_h: float
) -> tuple[float, float]:
    bmin, bmax = bbox
    px = (world_x - bmin[0]) / (bmax[0] - bmin[0]) * img_w
    py = (world_y - bmin[1]) / (bmax[1] - bmin[1]) * img_h
    return round(px, 1), round(py, 1)


def get_prim_world_position(stage, prim_path: str) -> tuple[float, float, float] | None:
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        return None
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    t = cache.GetLocalToWorldTransform(prim).ExtractTranslation()
    return t[0], t[1], t[2]


def world_to_local(
    stage, prim_path: str,
    wx: float, wy: float, wz: float
) -> tuple[float, float, float]:
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        return wx, wy, wz
    parent = prim.GetParent()
    if not parent.IsValid():
        return wx, wy, wz
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    parent_inv = cache.GetLocalToWorldTransform(parent).GetInverse()
    local = parent_inv.Transform(Gf.Vec3d(wx, wy, wz))
    return local[0], local[1], local[2]


def get_ap_prim_path(ap_id: str, folder: str) -> str:
    prim_name = ap_id.replace("-", "_")
    return f"/World/APs/{folder}/{prim_name}"


def move_ap(
    stage,
    ap_id: str,
    folder: str,
    wx: float, wy: float,
    ceiling_z: float,
) -> tuple[str, tuple | None]:
    ap_path = get_ap_prim_path(ap_id, folder)
    ap_prim = stage.GetPrimAtPath(ap_path)
    if not ap_prim.IsValid():
        raise ValueError(f"AP prim not found: {ap_path}")

    old_pos = get_prim_world_position(stage, ap_path)

    lx, ly, lz = world_to_local(stage, ap_path, wx, wy, ceiling_z)
    UsdGeom.XformCommonAPI(ap_prim).SetTranslate(Gf.Vec3d(lx, ly, lz))

    body_prim = stage.GetPrimAtPath(f"{ap_path}/Body")
    if body_prim.IsValid():
        UsdGeom.Imageable(body_prim).MakeVisible()

    return ap_path, old_pos


def undo_move(stage, ap_path: str, old_world: tuple) -> None:
    prim = stage.GetPrimAtPath(ap_path)
    if not prim.IsValid():
        return
    lx, ly, lz = world_to_local(stage, ap_path, *old_world)
    UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(lx, ly, lz))


def save_json(floor_json_id: str, assigned: dict[str, tuple]) -> int:
    with open(AP_LOCATIONS_JSON, encoding="utf-8") as f:
        data = json.load(f)

    updated = 0
    for floor in data["floors"]:
        if floor["id"] != floor_json_id:
            continue
        for ap in floor["aps"]:
            if ap["id"] in assigned:
                ap["px"], ap["py"] = assigned[ap["id"]]
                updated += 1

    with open(AP_LOCATIONS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return updated


def update_floor_centers(stage) -> None:
    for cfg in FLOOR_CONFIG.values():
        bbox = get_floor_bbox(stage, cfg["usd_path"])
        if bbox:
            bmin, bmax = bbox
            cfg["center_x"] = (bmin[0] + bmax[0]) / 2
            cfg["center_y"] = (bmin[1] + bmax[1]) / 2
