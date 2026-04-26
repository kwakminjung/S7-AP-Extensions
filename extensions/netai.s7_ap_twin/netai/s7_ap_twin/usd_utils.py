import csv
import os
import re

from pxr import Gf, UsdGeom

from .config import (
    AP_BODY_SCALE,
    COVERAGE_COLOR_MEDIUM,
    COVERAGE_COLOR_OFFLINE,
    COVERAGE_COLOR_STRONG,
    COVERAGE_COLOR_WEAK,
    DEFAULT_BAND,
    DEFAULT_TX_DBM,
    ONLINE_STATUSES,
)


def safe_prim_name(ap_id: str) -> str:
    return ap_id.replace("-", "_")


def is_online(ap_data: dict) -> bool:
    status   = str(ap_data.get("Status", "")).strip()
    template = str(ap_data.get("Template", "")).strip()
    return status in ONLINE_STATUSES and template.lstrip("-").isdigit()


def parse_tx_power(raw) -> float:
    match = re.search(r"[-\d.]+", str(raw))
    return float(match.group()) if match else 20.0


def load_template_csv(csv_path: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    if not os.path.exists(csv_path):
        return result
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = row.get("Name", "").strip()
                if name:
                    result[name] = dict(row)
    except Exception as exc:
        print(f"[usd_utils] CSV read error: {exc}")
    return result


def tx_power_to_radius(tx_dbm: float, band: str = "5GHz") -> float:
    radius = 200.0 + (tx_dbm - 23.0) * 8.0
    if "2.4" in band:
        radius *= 1.1
    return max(120.0, min(radius, 320.0))


def power_to_color(tx_dbm: float) -> Gf.Vec3f:
    if tx_dbm >= 24:
        return COVERAGE_COLOR_STRONG
    if tx_dbm >= 18:
        return COVERAGE_COLOR_MEDIUM
    return COVERAGE_COLOR_WEAK


def make_ap_body(stage, base_path: str, color: Gf.Vec3f = None) -> None:
    if color is None:
        color = Gf.Vec3f(0.88, 0.88, 0.88)

    body = UsdGeom.Cube.Define(stage, f"{base_path}/Body")
    UsdGeom.XformCommonAPI(body).SetScale(AP_BODY_SCALE)
    body.GetDisplayColorAttr().Set([color])
    UsdGeom.Imageable(body).MakeVisible()


def ensure_body_visible(stage, base_path: str) -> None:
    body_prim = stage.GetPrimAtPath(f"{base_path}/Body")
    if not body_prim.IsValid():
        return
    if UsdGeom.Imageable(body_prim).GetVisibilityAttr().Get() == UsdGeom.Tokens.invisible:
        UsdGeom.Imageable(body_prim).MakeVisible()
