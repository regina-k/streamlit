# additional 위치 데이터

이 폴더는 아파트 데이터에 추가로 붙일 수 있는 보조 위치 데이터를 담는다. 현재 `data/apartment/preprocessed/apartment.csv` 생성에는 사용하지 않았고, 이후 단지 좌표 기반 거리 피처를 만들 때 사용할 수 있다.

## 사용법

프로젝트 루트에서 아래 명령어를 실행하면 이 폴더에 `school.csv`, `station.csv`, `hospital.csv`가 다시 생성된다.

```powershell
python .\scripts\preprocess_locations.py
```

## 가공 방식

- `school.csv`는 한국교육시설안전원 초중등학교 위치 CSV에서 만들었다.
- `station.csv`는 도시철도 역사 정보 XLSX에서 만들었다.
- `hospital.csv`는 건강보험심사평가원 병원정보서비스 API에서 상급종합병원과 종합병원을 수집해 만들었다.
- 좌표계는 모두 WGS84 위도/경도(`EPSG:4326`)이다.
- 병원 API의 `YPos`를 `lat`, `XPos`를 `lon`으로 변환했다.
- 도로명주소 좌표 변환 API는 사용하지 않았다.

## 파일

- `school.csv`: 초등학교, 중학교, 고등학교 위치.
- `station.csv`: 도시철도역 위치. 같은 역명/좌표 기준으로 노선 중복을 줄인 파일이다.
- `hospital.csv`: 상급종합병원과 종합병원 위치.

## school.csv 컬럼 메타

| 컬럼 | 의미 |
|---|---|
| `id` | 학교 식별자. 원천 학교ID 앞에 `school:`을 붙인 값이다. |
| `name` | 학교명. |
| `type` | 학교급. 예: 초등학교, 중학교, 고등학교. |
| `lat` | 위도. WGS84 기준. |
| `lon` | 경도. WGS84 기준. |
| `address` | 도로명주소. |
| `jibun_address` | 지번주소. |
| `source` | 원천 데이터명. |

## station.csv 컬럼 메타

| 컬럼 | 의미 |
|---|---|
| `id` | 역 위치 식별자. 중복 정리 후 부여한 `station_unique:` 기반 ID이다. |
| `name` | 역사명. |
| `type` | 노선명. 환승역은 여러 노선명이 `|`로 연결될 수 있다. |
| `lat` | 역 위도. WGS84 기준. |
| `lon` | 역 경도. WGS84 기준. |
| `address` | 역사 도로명주소. |
| `operator` | 운영기관명. 여러 기관이 있으면 `|`로 연결될 수 있다. |
| `source` | 원천 데이터명. |

## hospital.csv 컬럼 메타

| 컬럼 | 의미 |
|---|---|
| `id` | 병원 식별자. HIRA 요양기관 식별값 앞에 `hospital:`을 붙인 값이다. |
| `name` | 병원명. |
| `type` | 병원 종별. 현재 상급종합 또는 종합병원. |
| `lat` | 병원 위도. HIRA API의 `YPos` 값이다. |
| `lon` | 병원 경도. HIRA API의 `XPos` 값이다. |
| `address` | 병원 주소. |
| `doctor_count` | 의사 총수. HIRA API의 `drTotCnt` 값이다. |
| `phone` | 병원 전화번호. |
| `source` | 원천 데이터명. |
