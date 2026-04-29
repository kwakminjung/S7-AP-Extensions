import omni.ui as ui
import omni.usd


class ApInfoPanel:

    def __init__(self):
        self._window = None
        self._selection_sub = None

    def setup(self, get_ap_data_fn):
        self._get_ap_data = get_ap_data_fn
        self._selection_sub = omni.usd.get_context().get_stage_event_stream().create_subscription_to_pop(
            self._on_selection_changed,
            name="ap_info_selection"
        )

    def _on_selection_changed(self, event):
        if event.type != int(omni.usd.StageEventType.SELECTION_CHANGED):
            return

        ctx = omni.usd.get_context()
        selected = ctx.get_selection().get_selected_prim_paths()

        if not selected:
            self._hide()
            return

        path = selected[0]
        parts = path.split("/")

        if len(parts) < 5 or parts[1] != "World" or parts[2] != "APs":
            self._hide()
            return

        ap_prim_name = parts[4]
        ap_id = ap_prim_name.replace("_", "-")  # GIST-AP-03-1F-Hall-Left-Top
        self._show(ap_id)
        self._show(ap_id)

    def _show(self, ap_id: str):
        ap_data, template = self._get_ap_data(ap_id)

        name         = ap_data.get("Name", ap_id)
        status       = ap_data.get("Status", "Unknown")
        users        = ap_data.get("# of Users", "-")
        tx_power     = template.get("tx_power", "-")
        template_num = ap_data.get("Template", "-")
        ip           = ap_data.get("IP", "-")

        is_on = "online" in status.lower()
        status_color = 0xFF44DD44 if is_on else 0xFFDD4444

        if not self._window:
            self._window = ui.Window(
                "AP Info", width=280, height=240,
                flags= ui.WINDOW_FLAGS_NO_SCROLLBAR
            )

        self._window.visible = True
        with self._window.frame:
            with ui.VStack(spacing=0):
                # 헤더
                with ui.ZStack(height=48):
                    ui.Rectangle(style={"background_color": 0xFF2A2A3A})
                    with ui.HStack(style={"margin_width": 12, "margin_height": 12}):
                        ui.Label(
                            name,
                            style={"font_size": 15, "color": 0xFFEEEEEE, "font_weight": 700}
                        )
                        ui.Spacer()
                        ui.Label(
                            "Online" if is_on else "Offline",
                            style={"font_size": 12, "color": status_color}
                        )

                ui.Spacer(height=2)

                # 내용
                with ui.VStack(spacing=4, style={"margin_width": 12, "margin_height": 8}):
                    for label, value, val_color in [
                        ("IP",       ip,           0xFFCCCCCC),
                        ("Users",    str(users),   0xFFCCCCCC),
                        ("TX Power", str(tx_power),0xFFAADDFF),
                        ("Template", str(template_num), 0xFFCCCCCC),
                    ]:
                        with ui.HStack(height=24):
                            ui.Label(label, width=80,
                                    style={"font_size": 12, "color": 0xFF888888})
                            ui.Label(value,
                                    style={"font_size": 12, "color": val_color})

    def _hide(self):
        if self._window:
            self._window.visible = False

    def teardown(self):
        self._selection_sub = None
        if self._window:
            self._window.visible = False
            self._window = None