from pxr import Gf

# API
UPDATE_INTERVAL = 10.0

ONLINE_STATUSES = {"Online"}
DEFAULT_TX_DBM  = 23.0
DEFAULT_BAND    = "5GHz"

COVERAGE_COLOR_STRONG  = Gf.Vec3f(0.10, 0.45, 1.00)   # >= 24 dBm
COVERAGE_COLOR_MEDIUM  = Gf.Vec3f(0.20, 0.65, 1.00)   # 18–23 dBm
COVERAGE_COLOR_WEAK    = Gf.Vec3f(0.45, 0.80, 1.00)   # < 18 dBm
COVERAGE_COLOR_OFFLINE = Gf.Vec3f(0.35, 0.35, 0.45)

AP_BODY_SCALE = Gf.Vec3f(9.75, 1.99, 10.05)

FLOOR_FOLDERS = {
    "Floor_1": "Floor_1",
    "Floor_2": "Floor_2",
    "Outdoor": "Outdoor",
}

ANIM_FPS          = 24
ANIM_DURATION     = 3.0
ANIM_RIPPLE_COUNT = 3
ANIM_TOTAL_FRAMES = int(ANIM_FPS * ANIM_DURATION)
