#!/usr/bin/env python3
"""승인 v3.1 아이콘(오픈삼국 docs/design/ui-v3 의 IC, 24 격자 · 선 1.8)을 이 저장소 원본 규격(20 격자 · 선 1.5 · <path d> 만)으로 옮긴다.

새로 그리지 않는다. 좌표만 20/24 배다(선 1.8 × 20/24 = 1.5 라 굵기도 같다). `<circle>` · `<rect>` 는 같은 모양의 닫힌 경로로 적는다.

- 원은 호 두 개 + `z` 로 닫는다. 열린 호는 시작점에 사각 끝(stroke-linecap square)이 붙어 테두리 밖으로 튀어나온다(2026-10-01 정정).
- 좌표는 소수 여섯 자리까지 적는다. 세 자리 반올림은 상대 좌표가 이어지는 꺾은선(왕관 등)에서 가장자리 픽셀을 바꿨다(2026-10-01 정정).

사용: python3 tools/assets/v31_icons_to_20.py <오픈삼국 docs/design/ui-v3 경로>
      → assets/ui-icons/source/<이름>.svg 를 쓴 뒤 tools/assets/build_ui_icons.py 로 sprite · export 를 굽는다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets" / "ui-icons" / "source"
K = 20 / 24
DECIMALS = 6

# 이름 ← (v3.1 IC 키, 라벨). 이름은 v3.1 키 그대로가 원칙이고, 기존 이름과 헷갈리는 것만 바꿨다.
NAMES: dict[str, tuple[str, str]] = {
    # 부품(#24)
    "lock": ("lock", "잠김"),
    "clock": ("clock", "시각"),
    "target": ("target", "대상 고르기"),
    "play": ("play", "재생"),
    "pause": ("pause", "멈춤"),
    "skip-back": ("skipb", "이전 사건"),
    "skip-forward": ("skipf", "다음 사건"),
    "copy": ("copy", "복사"),
    "help": ("help", "도움말"),
    "list": ("list", "목록"),
    "alert": ("alert", "경고"),
    "unplug": ("unplug", "연결 끊김"),
    "chevron-left": ("back", "뒤로"),
    # 셸 레일 · 하단 탭(#25)
    "war-room": ("war", "작전실"),
    "retinue": ("retinue", "부"),
    "stratagem": ("stratagem", "계책"),
    "territory": ("territory", "영지"),
    "corps": ("corps", "군단"),
    "court": ("court", "조정"),
    "records": ("records", "기록"),
    "plaza": ("plaza", "광장"),
    "admin": ("admin", "관리"),
    "menu": ("menu", "전체 메뉴"),
    # 화면 보드(2026-10-01 — 보드에서 쓰는데 스프라이트에 없던 것)
    "season": ("season", "계절"),
    "check": ("check", "확인"),
    "next": ("next", "다음"),
    "prev": ("prev", "이전"),
    "up": ("up", "위로"),
    "arrow": ("arrow", "아래 화살표"),
    "layers": ("layers", "지도 층"),
    "legend": ("legend", "범례"),
    "logout": ("logout", "로그아웃"),
    "lobby": ("lobby", "로비로"),
    "crown": ("crown", "황실"),
    "clear": ("clear", "지우기"),
    "swap": ("swap", "바꾸기"),
    "pause-circle": ("pausec", "멈춤(원)"),
}

NUM = r"-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?"


def fmt(v: float) -> str:
    s = f"{v:.{DECIMALS}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def scale_path(d: str) -> str:
    out = []
    for cmd, args in re.findall(r"([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)", d):
        nums = [float(x) for x in re.findall(NUM, args)]
        if cmd in "Aa":
            scaled = []
            for i in range(0, len(nums), 7):
                rx, ry, rot, large, sweep, x, y = nums[i:i + 7]
                scaled += [fmt(rx * K), fmt(ry * K), fmt(rot), str(int(large)), str(int(sweep)), fmt(x * K), fmt(y * K)]
            out.append(cmd + " ".join(scaled))
        else:
            out.append(cmd + " ".join(fmt(n * K) for n in nums))
    return " ".join(out)


def attrs(tag: str) -> dict[str, float]:
    return {k: float(v) for k, v in re.findall(r'(\w+)="(' + NUM + r')"', tag)}


def to_paths(fragment: str) -> list[str]:
    paths = []
    for tag in re.findall(r"<(?:path|circle|rect)\b[^>]*/>", fragment):
        if tag.startswith("<path"):
            paths.append(scale_path(re.search(r'd="([^"]+)"', tag).group(1)))
        elif tag.startswith("<circle"):
            a = attrs(tag)
            cx, cy, r = a["cx"] * K, a["cy"] * K, a["r"] * K
            paths.append(f"M{fmt(cx - r)} {fmt(cy)}a{fmt(r)} {fmt(r)} 0 1 0 {fmt(2 * r)} 0a{fmt(r)} {fmt(r)} 0 1 0 {fmt(-2 * r)} 0z")
        else:
            a = attrs(tag)
            x, y, w, h = a["x"] * K, a["y"] * K, a["width"] * K, a["height"] * K
            paths.append(f"M{fmt(x)} {fmt(y)}h{fmt(w)}v{fmt(h)}h{fmt(-w)}z")
    return paths


def main() -> int:
    ui_dir = Path(sys.argv[1])
    sys.path.insert(0, str(ui_dir))
    import v31system  # noqa: F401 — IC 를 v3.1 판으로 채운다
    from v3common import IC

    for name, (key, label) in NAMES.items():
        body = "".join(f'\n  <path d="{p}"/>' for p in to_paths(IC[key]))
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
               'stroke-width="1.5" stroke-linecap="square" stroke-linejoin="miter">\n'
               f"  <title>{label}</title>{body}\n</svg>\n")
        (SOURCE / f"{name}.svg").write_text(svg, encoding="utf-8")
    print(f"{len(NAMES)} icons → {SOURCE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
