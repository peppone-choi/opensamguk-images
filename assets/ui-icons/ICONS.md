# UI 아이콘 원본 (ui-2026-09)

20×20 격자, 선 1.5px `currentColor`, 각진 끝(square/miter). 색은 소비 쪽 CSS 가 정한다(청동·이끼·적갈·정보).

| 이름 | 라벨 |
|---|---|
| `dept-ops` | 작전실 |
| `dept-nation` | 국가 운영 |
| `dept-military` | 군사 |
| `dept-info` | 정보 |
| `dept-plaza` | 광장 |
| `dept-records` | 기록 |
| `hub-best-generals` | 명장 순위 |
| `hub-emperor` | 황제 정보 |
| `hub-generals` | 장수 일람 |
| `hub-kingdoms` | 세력 순위 |
| `hub-npcs` | NPC 일람 |
| `hub-hall-of-fame` | 명예의 전당 |
| `hub-traffic` | 접속 통계 |
| `cmd-ok` | 가능 |
| `cmd-need` | 부족 |
| `cmd-no` | 불가 |
| `cmd-sealed` | 봉인 |
| `res-gold` | 금 |
| `res-rice` | 쌀 |
| `res-troops` | 병력 |
| `res-provisions` | 군량 |
| `search` | 검색 |
| `refresh` | 갱신 |
| `close` | 닫기 |
| `arrow-left` | 왼쪽 |
| `arrow-right` | 오른쪽 |
| `arrow-up` | 위 |
| `arrow-down` | 아래 |
| `external` | 외부 링크 |
| `filter` | 필터 |
| `auction` | 경매 |
| `dice` | 베팅 |
| `diplomacy` | 외교 |
| `mail` | 서신 |
| `tools` | 관리 |
| `members` | 회원 |
| `lock` | 잠김 |
| `clock` | 시각 |
| `target` | 대상 고르기 |
| `play` | 재생 |
| `pause` | 멈춤 |
| `skip-back` | 이전 사건 |
| `skip-forward` | 다음 사건 |
| `copy` | 복사 |
| `help` | 도움말 |
| `list` | 목록 |
| `alert` | 경고 |
| `unplug` | 연결 끊김 |
| `chevron-left` | 뒤로 |
| `war-room` | 작전실 |
| `retinue` | 부 |
| `stratagem` | 계책 |
| `territory` | 영지 |
| `corps` | 군단 |
| `court` | 조정 |
| `records` | 기록 |
| `plaza` | 광장 |
| `admin` | 관리 |
| `menu` | 전체 메뉴 |

## v3.1 부품 아이콘(2026-09-30 승인)

위 13개(`lock` … `chevron-left`)는 승인된 v3.1 디자인 시스템 `icon()`(오픈삼국 `docs/design/ui-v3/v3common.py` · `v31system.py` 의 `IC`,
24 격자 · 선 1.8)을 새로 그리지 않고 옮긴 것이다. 좌표만 20/24 배(선 1.8 × 20/24 = 1.5 라 굵기도 같다)이고, `<circle>` · `<rect>` 는
같은 모양의 경로로 적었다(이 빌더는 `<path d>` 만 읽는다). v3.1 키 → 이름: `skipb` → `skip-back`, `skipf` → `skip-forward`, `back` → `chevron-left`.

## v3.1 셸 레일 · 하단 탭 아이콘(2026-09-30 승인)

`war-room` … `menu` 10개는 같은 방식으로 v3.1 `IC`(`war` · `retinue` · `stratagem` · `territory` · `corps` · `court` · `records` ·
`plaza` · `admin` · `menu`)에서 옮겼다(좌표 20/24 배, 새로 그리지 않음). v3.1 키 `war` → 이름 `war-room`(다른 이름과 헷갈리지 않게).
