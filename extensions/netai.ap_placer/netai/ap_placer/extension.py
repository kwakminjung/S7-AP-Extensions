import asyncio
import json

import omni.ext
import omni.kit.app
import omni.usd
import omni.ui as ui
from pxr import UsdGeom

from .config import AP_LOCATIONS_JSON, FLOOR_CONFIG, FLOOR_LABEL, MARKER_PATH
from .marker import create_marker, delete_marker, get_marker_world_position
from .placer import (
    get_floor_bbox,
    move_ap,
    save_json,
    undo_move,
    update_floor_centers,
    world_to_px,
)


class ApPlacerExtension(omni.ext.IExt):

    def on_startup(self, _ext_id: str) -> None:
        print("[netai.ap_placer] startup")
        self._stage          = None
        self._current_floor  = 1
        self._assigned: dict[str, tuple] = {}
        self._undo_stack: list            = []
        self._selected_ap_id: str | None = None
        self._window = None
        asyncio.ensure_future(self._delayed_init())

    async def _delayed_init(self) -> None:
        app = omni.kit.app.get_app()
        for _ in range(10):
            await app.next_update_async()
        self._build_ui()
        await self._init_stage()

    async def _init_stage(self) -> None:
        app = omni.kit.app.get_app()
        for _ in range(5):
            await app.next_update_async()
        self._stage = omni.usd.get_context().get_stage()
        update_floor_centers(self._stage)

    def _build_ui(self) -> None:
        self._window = ui.Window("AP Placer", width=380)
        with self._window.frame:
            with ui.VStack(spacing=8, style={"margin": 8}):
                self._build_floor_buttons()
                ui.Separator()
                ui.Button("Load AP List", height=30,
                          clicked_fn=self._load_ap_list)
                with ui.ScrollingFrame(height=180):
                    self._list_stack = ui.VStack(spacing=2)
                ui.Separator()
                self._build_placement_section()
                ui.Separator()
                self._build_action_buttons()

    def _build_floor_buttons(self) -> None:
        with ui.HStack(height=28, spacing=4):
            ui.Label("Floor:", width=50)
            for num, label in FLOOR_LABEL.items():
                ui.Button(label, width=80,
                          clicked_fn=lambda n=num: self._switch_floor(n))
            ui.Button("All", width=60, clicked_fn=self._show_all)
        self._floor_label = ui.Label(
            "Current: Floor 1", style={"color": 0xFF88CCFF})

    def _build_placement_section(self) -> None:
        self._selected_label = ui.Label(
            "Selected AP: (none)", style={"color": 0xFFFFCC44})
        ui.Button(
            "1. Place Red Marker", height=36,
            clicked_fn=self._place_marker,
            style={"background_color": 0xFF993333},
        )
        ui.Label("   -> Drag the red sphere to AP position",
                 style={"color": 0xFF888888})
        self._move_btn = ui.Button(
            "2. Move AP Here", height=36,
            clicked_fn=self._move_ap_to_marker,
            enabled=False,
            style={"background_color": 0xFF336699},
        )
        self._status = ui.Label(
            "Load AP list to begin",
            style={"color": 0xFFAAAAAA},
            word_wrap=True,
        )

    def _build_action_buttons(self) -> None:
        with ui.HStack(height=28, spacing=6):
            ui.Button("Undo Last",       clicked_fn=self._undo)
            ui.Button("Save JSON + Stage", clicked_fn=self._save)

    def _switch_floor(self, floor_num: int) -> None:
        if not self._stage:
            self._status.text = "Stage not ready"
            return
        self._current_floor = floor_num

        show_all = floor_num == 3
        for fn, cfg in FLOOR_CONFIG.items():
            if fn == 3:
                continue
            prim = self._stage.GetPrimAtPath(cfg["usd_path"])
            if prim.IsValid():
                img = UsdGeom.Imageable(prim)
                if show_all or fn == floor_num:
                    img.MakeVisible()
                else:
                    img.MakeInvisible()

        self._floor_label.text = f"Current: {FLOOR_LABEL[floor_num]}"
        self._status.text      = f"Switched to {FLOOR_LABEL[floor_num]}."

    def _show_all(self) -> None:
        if not self._stage:
            return
        for fn, cfg in FLOOR_CONFIG.items():
            if fn == 3:
                continue
            prim = self._stage.GetPrimAtPath(cfg["usd_path"])
            if prim.IsValid():
                UsdGeom.Imageable(prim).MakeVisible()
        self._floor_label.text = "Current: All floors visible"

    def _load_ap_list(self) -> None:
        try:
            with open(AP_LOCATIONS_JSON, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self._status.text = f"Failed to read JSON: {e}"
            return

        floor_json_id = FLOOR_CONFIG[self._current_floor]["json_id"]
        floor_data    = next(
            (fl for fl in data["floors"] if fl["id"] == floor_json_id), None)
        if not floor_data:
            self._status.text = f"No data for {floor_json_id}"
            return

        self._list_stack.clear()
        with self._list_stack:
            for ap in floor_data["aps"]:
                ap_id  = ap["id"]
                px, py = ap["px"], ap["py"]
                placed = not (px % 500 == 0 and py % 500 == 0)
                color  = 0xFF88FF88 if placed else 0xFFAAAAAA
                mark   = "v" if placed else "o"

                def make_fn(aid):
                    return lambda: self._select_ap(aid)

                ui.Button(
                    f"{mark}  {ap_id}  ({px:.0f}, {py:.0f})",
                    height=24, clicked_fn=make_fn(ap_id),
                    style={"color": color},
                )

        self._status.text = f"Loaded {len(floor_data['aps'])} APs. Click one to select."

    def _select_ap(self, ap_id: str) -> None:
        self._selected_ap_id           = ap_id
        self._selected_label.text      = f"Selected AP: {ap_id}"
        self._move_btn.enabled         = True
        self._status.text = (
            f"[{ap_id}] selected.\n"
            f"Click '1. Place Red Marker' to start."
        )

    def _place_marker(self) -> None:
        if not self._selected_ap_id:
            self._status.text = "Select an AP from the list first!"
            return
        if not self._stage:
            self._status.text = "Stage not ready"
            return

        cfg = FLOOR_CONFIG[self._current_floor]
        create_marker(
            self._stage,
            cfg.get("center_x", 2420.1),
            cfg.get("center_y", -66.3),
            cfg["ceiling_z"],
        )
        self._status.text = (
            f"Red marker placed at center.\n"
            f"Drag it to [{self._selected_ap_id}] position,\n"
            f"then click '2. Move AP Here'."
        )

    def _move_ap_to_marker(self) -> None:
        if not self._selected_ap_id or not self._stage:
            return

        pos = get_marker_world_position(self._stage)
        if pos is None:
            self._status.text = "Red marker not found!\nClick '1. Place Red Marker' first."
            return

        wx, wy, _ = pos
        cfg       = FLOOR_CONFIG[self._current_floor]

        try:
            ap_path, old_pos = move_ap(
                self._stage,
                self._selected_ap_id,
                cfg["folder"],
                wx, wy,
                cfg["ceiling_z"],
            )
        except ValueError as e:
            self._status.text = str(e)
            return

        self._undo_stack.append((self._selected_ap_id, ap_path, old_pos))

        bbox = get_floor_bbox(self._stage, cfg["usd_path"])
        if bbox:
            px, py = world_to_px(wx, wy, bbox,
                                  cfg["image_width_px"], cfg["image_height_px"])
            self._assigned[self._selected_ap_id] = (px, py)

        delete_marker(self._stage)

        self._status.text = (
            f"Placed {self._selected_ap_id}\n"
            f"World X:{wx:.1f} Y:{wy:.1f}  ceiling Z:{cfg['ceiling_z']:.1f}\n"
            f"Select next AP from the list."
        )
        self._selected_ap_id      = None
        self._selected_label.text = "Selected AP: (none)"
        self._move_btn.enabled    = False

    def _undo(self) -> None:
        if not self._undo_stack:
            self._status.text = "Nothing to undo"
            return
        ap_id, ap_path, old_world = self._undo_stack.pop()
        if old_world:
            undo_move(self._stage, ap_path, old_world)
        self._assigned.pop(ap_id, None)
        self._status.text = f"Undid {ap_id}"

    def _save(self) -> None:
        if not self._assigned:
            self._status.text = "No placement data to save"
            return
        try:
            floor_json_id = FLOOR_CONFIG[self._current_floor]["json_id"]
            count         = save_json(floor_json_id, self._assigned)
            omni.usd.get_context().save_stage()
            self._status.text = f"Saved JSON + Stage! ({count} APs updated)"
        except Exception as e:
            self._status.text = f"Save failed: {e}"

    def on_shutdown(self) -> None:
        if self._stage:
            delete_marker(self._stage)
        self._window = None
