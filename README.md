# s7-ap-twin

NVIDIA Omniverse Kit 기반의 Wi-Fi AP 디지털 트윈 시각화 시스템. 실제 건물의 AP 신호 상태를 3D 트윈 공간에 실시간으로 렌더링합니다.

## 시작

1. 레포 클론
```bash
git clone https://github.com/kwakminjung/S7-AP-Extensions
```

2. configs 파일 (전달) 복사
```bash
cp configs/.env S7-AP-Extensions/extensions/netai.s7_ap_twin/
cp configs/config.py S7-AP-Extensions/extensions/netai.ap_placer/netai/ap_placer/
cp configs/ap_locations.json S7-AP-Extensions/extensions/netai.s7_ap_twin/data/
```

3. extensions 폴더를 Kit 앱의 extension 검색 경로에 복사

```bash
# kit-app-template 기준
cp -r extensions/ {kit-app-template 경로}/source/extensions/

# 또는 앱의 exts/ 폴더가 있는 경우
cp -r extensions/ {앱 경로}/exts/
```

> 앱의 `.kit` 파일에서 `folders.'++' = [...]` 항목을 확인하여 올바른 경로에 복사하세요.

4. `.kit` 파일의 `[dependencies]`에 추가
```toml
"netai.s7_ap_twin" = {}
"netai.ap_placer" = {}
```

5. 빌드
```bash
./repo.sh build
```

## Extensions

### `netai.s7_ap_twin`

AP 신호 커버리지를 3D 트윈에 시각화하는 메인 Extension.

**동작 방식**
- `/ews/aplist` — 10초 주기로 폴링하여 AP 온/오프 상태 및 템플릿 번호 확인
- `/ews/template` — 1분 주기로 폴링하여 템플릿 정보 메모리 캐싱
- 온라인 AP → 파란색 파동 애니메이션 디스크 렌더링, tx_power 기반 반경/색상 적용
- 오프라인 AP → Coverage 숨김, 회색 본체 표시
- AP prim 클릭 시 Name, Status, IP, Users, TX Power, Template 번호 정보 패널 표시

**파일 구조**
```
netai.s7_ap_twin/
  netai/s7_ap_twin/
    extension.py   # 폴링 루프, 렌더 디스패치
    ap_loader.py   # ap_locations.json + Floor bbox 기반 좌표 변환
    ap_info.py     # AP prim 클릭 시 정보 패널 표시
    coverage.py    # 파동 애니메이션 메시 생성
    materials.py   # OmniPBR Material
    usd_utils.py   # Body 생성, tx_power 파싱, on/off 판단
    config.py      # 상수
    env_loader.py  # 환경변수 로드
  data/
    ap_locations.json  # 층별 AP ID + 도면 픽셀 좌표
```

**USD 구조**
```
/World/APs/
  Floor_1/   # 1층 AP
  Floor_2/   # 2층 AP
  Outdoor/   # 실외 AP
```


### `netai.ap_placer`

탑뷰에서 빨간 마커를 드래그해 AP 위치를 지정하는 배치 툴.

**동작 방식**
- Floor 1 / Floor 2 / Outdoor 층 전환 (건물 visibility 토글)
- 빨간 Sphere 마커 드래그 → AP prim 이동
- 월드 좌표 → Floor bbox 기준 픽셀 좌표 역변환 후 `ap_locations.json` 저장
- Save JSON + Stage로 `ap_locations.json` + USD 파일 동시 저장

**파일 구조**
```
netai.ap_placer/
  netai/ap_placer/
    extension.py  # UI, 이벤트
    placer.py     # 이동 로직, 좌표 변환, JSON 저장
    marker.py     # 마커 생성/삭제
    config.py     # 상수
```

**AP Placer 실행 방법**

자동 시작이 안 될 경우 Script Editor에서 실행:
```python
from netai.ap_placer.extension import ApPlacerExtension

_ap_placer_instance = ApPlacerExtension()
_ap_placer_instance.on_startup("")
```
`Snippets` → `Save Snippet`으로 저장해두면 편리합니다.



## AP 위치 데이터

`ap_locations.json` — 층별 AP ID + 도면 픽셀 좌표(px, py) 저장.

```json
{
  "floors": [
    {
      "id": "Floor_1",
      "usd_path": "/World/Ground/A_Exterior/Floor_1",
      "image_width_px": 2000,
      "image_height_px": 2000,
      "aps": [
        {"id": "GIST-AP-01", "px": 320, "py": 180}
      ]
    }
  ]
}
```

Floor prim bbox를 기준으로 픽셀 좌표 → USD 월드 좌표 자동 계산.


## 관련 레포

- [S7-AP-api](https://github.com/kwakminjung/S7-AP-api) — AP 데이터 수집 API 서버 (aplist-api, template-api)

## Extensions 아키텍처

<img width="1265" height="532" alt="image" src="https://github.com/user-attachments/assets/8b02b7a5-e194-44bc-a9da-eb60951df989" />
