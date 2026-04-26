import json
import os

from pxr import Usd, UsdGeom

from .config import FLOOR_FOLDERS

AP_LOCATIONS_JSON = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "ap_locations.json"
)


def get_floor_bbox(stage, usd_path: str):
    prim = stage.GetPrimAtPath(usd_path)
    if not prim.IsValid():
        print(f"[ap_loader] Floor prim not found: {usd_path}")
        return None

    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        includedPurposes=[UsdGeom.Tokens.default_],
        useExtentsHint=True,
    )
    rng = cache.ComputeWorldBound(prim).GetRange()
    if rng.IsEmpty():
        print(f"[ap_loader] Floor bbox empty: {usd_path}")
        return None

    return rng.GetMin(), rng.GetMax()


def load_ap_positions(stage) -> dict[str, tuple[float, float, float, str]]:
    try:
        with open(AP_LOCATIONS_JSON, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"[ap_loader] ap_locations.json load error: {exc}")
        return {}

    positions: dict[str, tuple[float, float, float, str]] = {}

    for floor in data.get("floors", []):
        usd_path   = floor["usd_path"]
        img_w      = float(floor["image_width_px"])
        img_h      = float(floor["image_height_px"])
        fallback_y = float(floor.get("fallback_ceiling_y", 300.0))
        floor_id   = floor["id"]
        folder     = FLOOR_FOLDERS.get(floor_id, "Floor_1")
        bbox       = get_floor_bbox(stage, usd_path)

        for ap in floor.get("aps", []):
            ap_id = ap["id"]
            px    = float(ap["px"])
            py    = float(ap["py"])

            if bbox:
                bmin, bmax = bbox
                x = bmin[0] + (px / img_w) * (bmax[0] - bmin[0])
                y = float(bmax[1])
                z = bmin[2] + (py / img_h) * (bmax[2] - bmin[2])
            else:
                x, y, z = px, fallback_y, py

            positions[ap_id] = (x, y, z, folder)
            print(f"[ap_loader] {ap_id} ({folder}) → ({x:.1f}, {y:.1f}, {z:.1f})")

    print(f"[ap_loader] loaded {len(positions)} AP positions")
    return positions
