import asyncio
import os

import aiohttp
import omni.ext
import omni.kit.app
import omni.usd
from pxr import Gf, UsdGeom

from .ap_loader import load_ap_positions
from .config import DEFAULT_BAND, DEFAULT_TX_DBM, UPDATE_INTERVAL
from .coverage import update_coverage
from .env_loader import load_env
from .usd_utils import (
    ensure_body_visible,
    is_online,
    make_ap_body,
    parse_tx_power,
    power_to_color,
    safe_prim_name,
    tx_power_to_radius,
)

_env = load_env()
API_BASE_URL = _env.get("S7_AP_API_URL",    "http://localhost:8001")
API_PREFIX   = _env.get("S7_AP_API_PREFIX", "/ews")

ANIM_FPS      = 24
ANIM_DURATION = 3.0

TEMPLATE_UPDATE_INTERVAL = 60.0   # 1분
COVERAGE_COLOR_OFFLINE   = Gf.Vec3f(0.35, 0.35, 0.45)


class NetaiS7ApTwinExtension(omni.ext.IExt):

    def on_startup(self, _ext_id: str) -> None:
        print("[netai.s7_ap_twin] startup")
        self._stage          = None
        self._running        = True
        self._timeline       = None
        self._ap_positions   = {}
        self._template_cache = {}   # template_num → template dict
        self._task           = asyncio.ensure_future(self._wait_for_stage())

    async def _wait_for_stage(self) -> None:
        import carb
        ctx = omni.usd.get_context()
        app = omni.kit.app.get_app()
        for _ in range(10):
            await app.next_update_async()

        settings = carb.settings.get_settings()
        usd_path = (settings.get_as_string("/app/auto_load_usd") or "").strip()
        if usd_path and ctx.get_stage() is None:
            print(f"[netai.s7_ap_twin] opening stage: {usd_path}")
            await ctx.open_stage_async(usd_path)

        while self._running:
            stage = ctx.get_stage()
            if stage is not None:
                self._stage        = stage
                self._ap_positions = load_ap_positions(stage)
                print("[netai.s7_ap_twin] stage ready")
                await self._update_loop()
                return
            await asyncio.sleep(1.0)

    def _start_timeline(self) -> None:
        import omni.timeline
        self._timeline = omni.timeline.get_timeline_interface()
        self._timeline.set_looping(True)
        self._timeline.set_start_time(0.0)
        self._timeline.set_end_time(ANIM_DURATION)
        self._timeline.set_time_codes_per_second(ANIM_FPS)
        if not self._timeline.is_playing():
            self._timeline.play()
            print(f"[netai.s7_ap_twin] timeline play (loop {ANIM_DURATION}s @ {ANIM_FPS}fps)")

    async def _update_loop(self) -> None:
        first = True
        last_template_fetch = 0.0

        async with aiohttp.ClientSession() as session:
            while self._running:
                try:
                    now = asyncio.get_event_loop().time()

                    if now - last_template_fetch >= TEMPLATE_UPDATE_INTERVAL:
                        await self._fetch_templates(session)
                        last_template_fetch = now

                    await self._fetch_and_render(session)

                    if first:
                        self._start_timeline()
                        first = False

                except Exception as exc:
                    print(f"[netai.s7_ap_twin] loop error: {exc}")

                await asyncio.sleep(UPDATE_INTERVAL)

    async def _fetch_templates(self, session: aiohttp.ClientSession) -> None:
        url = f"{API_BASE_URL}{API_PREFIX}/template"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    print(f"[netai.s7_ap_twin] /template HTTP {resp.status}")
                    return
                body = await resp.json()
        except Exception as exc:
            print(f"[netai.s7_ap_twin] /template error: {type(exc).__name__}: {exc}")
            return

        if body.get("status") != "success":
            return

        for item in body.get("data", []):
            t_num = item.get("template_number")
            if t_num:
                self._template_cache[t_num] = item

        print(f"[netai.s7_ap_twin] template cache updated: {len(self._template_cache)} templates")

    async def _fetch_and_render(self, session: aiohttp.ClientSession) -> None:
        url = f"{API_BASE_URL}{API_PREFIX}/aplist"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    print(f"[netai.s7_ap_twin] /aplist HTTP {resp.status}")
                    return
                body = await resp.json()
        except Exception as exc:
            print(f"[netai.s7_ap_twin] /aplist error: {type(exc).__name__}: {exc}")
            return

        if body.get("status") != "success":
            return

        ap_list = body.get("data", [])
        ap_map  = {item["Name"]: item for item in ap_list if "Name" in item}

        for ap_id in self._ap_positions:
            ap_data     = ap_map.get(ap_id, {})
            online      = is_online(ap_data) if ap_data else False
            template_num = ap_data.get("Template", "")
            template    = self._template_cache.get(str(template_num), {})
            self._render_ap(ap_id, online=online, template=template)

    def _render_ap(self, ap_id: str, online: bool, template: dict) -> None:
        x, y, z, folder = self._ap_positions[ap_id]
        prim_name   = safe_prim_name(ap_id)
        folder_path = f"/World/APs/{folder}"
        base_path   = f"{folder_path}/{prim_name}"

        if not self._stage.GetPrimAtPath(folder_path).IsValid():
            UsdGeom.Xform.Define(self._stage, folder_path)

        if not self._stage.GetPrimAtPath(base_path).IsValid():
            xform = UsdGeom.Xform.Define(self._stage, base_path)
            xform.AddTranslateOp().Set(Gf.Vec3d(x, y, z))
            make_ap_body(self._stage, base_path)

        ensure_body_visible(self._stage, base_path)

        body_prim = self._stage.GetPrimAtPath(f"{base_path}/Body")
        cov_path  = f"{base_path}/Coverage"
        cov_prim  = self._stage.GetPrimAtPath(cov_path)

        if online:
            tx_dbm     = parse_tx_power(template.get("tx_power", DEFAULT_TX_DBM))
            band       = template.get("band", DEFAULT_BAND)
            color      = power_to_color(tx_dbm)
            radius     = tx_power_to_radius(tx_dbm, band)
            body_color = Gf.Vec3f(0.88, 0.88, 0.88)

            update_coverage(self._stage, base_path, radius, color, opacity=0.35)

            if body_prim.IsValid():
                UsdGeom.Gprim(body_prim).GetDisplayColorAttr().Set([body_color])
        else:
            if cov_prim.IsValid():
                UsdGeom.Imageable(cov_prim).MakeInvisible()
            if body_prim.IsValid():
                UsdGeom.Gprim(body_prim).GetDisplayColorAttr().Set(
                    [Gf.Vec3f(0.40, 0.40, 0.40)])

        print(f"[netai.s7_ap_twin] {ap_id} ({folder}) → "
              f"{'on ' if online else 'off'} "
              f"tx={parse_tx_power(template.get('tx_power', DEFAULT_TX_DBM)):.0f}dBm")

    def on_shutdown(self) -> None:
        print("[netai.s7_ap_twin] shutdown")
        self._running = False
        if self._timeline and self._timeline.is_playing():
            self._timeline.stop()
        if self._task:
            self._task.cancel()
            self._task = None