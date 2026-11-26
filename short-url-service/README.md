# 단축 URL 서비스 API

Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL을 이용한 학습용 단축 URL API입니다.
단축 코드는 PostgreSQL에 저장되며, 방문할 때마다 접속 횟수가 증가한 뒤 HTTP 307로 원본 URL에 이동합니다.

## 1. 프로젝트 구조와 요청 흐름

```text
short-url-service/
├── app/
│   ├── __init__.py
│   ├── main.py       # FastAPI 앱, 상태 확인과 HTTP 엔드포인트
│   ├── database.py   # .env 읽기, SQLAlchemy 엔진·세션, Depends용 DB 세션
│   ├── models.py     # PostgreSQL urls 테이블 ORM 모델
│   ├── schemas.py    # 입력 URL 검증과 API 요청·응답 데이터 형식
│   └── crud.py       # 코드 생성, URL 조회, 클릭 횟수 변경
├── tests/
│   ├── conftest.py   # 개발 DB와 분리된 테스트 DB 및 테스트 픽스처
│   └── test_api.py   # API 단위 테스트와 전체 사용자 흐름 테스트
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

요청 데이터는 Pydantic 스키마에서 검증된 다음 FastAPI 엔드포인트로 전달됩니다.
엔드포인트는 `Depends(get_db)`로 요청 전용 SQLAlchemy `Session`을 받고, CRUD 함수가 ORM을 통해 PostgreSQL 데이터를 처리합니다. 응답을 보낸 뒤 세션은 닫힙니다. 서버 시작 시 ORM 모델에 정의된 `urls` 테이블이 없으면 생성하며, 기존 테이블의 데이터를 지우지 않습니다.

## 2. Python 환경과 패키지 설치

Python 3.12를 설치한 뒤 이 디렉터리에서 가상환경을 만듭니다.

```powershell
py -3.12 -m venv .venv
```

Windows PowerShell에서 활성화:

```powershell
.\.venv\Scripts\Activate.ps1
```

Windows 명령 프롬프트(CMD)에서 활성화:

```bat
.venv\Scripts\activate.bat
```

필요한 라이브러리를 설치합니다.

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. PostgreSQL 데이터베이스 준비

PostgreSQL에 접속할 수 있는 관리자 계정으로 사용자와 데이터베이스를 생성합니다. 아래 예시는 `psql` 명령줄에서 실행하며, 안전을 위해 실제 비밀번호로 `change_me`를 바꾸세요.

```sql
CREATE USER short_url_user WITH PASSWORD 'change_me';
CREATE DATABASE short_url_db OWNER short_url_user;
```

이미 같은 이름의 데이터베이스나 사용자가 있다면 생성 명령 대신 해당 계정과 데이터베이스를 사용하면 됩니다. PostgreSQL 서버가 실행 중이고 지정한 포트(기본값 `5432`)로 연결 가능한지도 확인하세요.

## 4. 환경변수 설정

예시 파일을 복사해 실제 설정 파일을 만듭니다.

```powershell
Copy-Item .env.example .env
```

`.env`를 열어 실제 주소, 사용자, 비밀번호를 설정합니다.

```dotenv
DATABASE_URL=postgresql+psycopg://short_url_user:실제비밀번호@localhost:5432/short_url_db
```

URL 안의 비밀번호에 `@`, `:`, `/` 등의 예약 문자가 들어가면 URL 인코딩이 필요합니다. 실제 `.env` 파일은 `.gitignore`로 Git 추적 대상에서 제외됩니다. `.env.example`에는 비밀이 아닌 예시 값만 기록하세요.

## 5. 서버 실행 및 Swagger UI

이 디렉터리에서 서버를 실행합니다.

```powershell
uvicorn app.main:app --reload
```

- Swagger UI: <http://localhost:8000/docs>
- 상태 확인: <http://localhost:8000/health>

서버 시작 시 DB 연결이 실패해도 서버는 상태 확인 요청을 받을 수 있게 실행을 계속하며, 오류는 로그에 기록됩니다. `/health`는 연결 성공 시 HTTP 200, 실패 시 HTTP 503을 반환합니다.

## 6. API 사용법

Swagger UI에서 각 API를 선택하고 **Try it out** → 요청 값 입력 → **Execute**를 누릅니다. 아래 주소와 예시는 로컬 서버 기준입니다.

### URL 단축

- 역할: URL을 검증하고 DB에 저장한 뒤 고유 단축 코드와 주소를 반환합니다. 새 코드의 `click_count`는 0입니다.
- 방식/주소: `POST http://localhost:8000/api/shorten`
- 요청 JSON:

```json
{
  "original_url": "https://www.youtube.com/watch?v=abcdef123456"
}
```

- 정상 응답: HTTP 201

```json
{
  "short_code": "aB12cD",
  "short_url": "http://localhost:8000/aB12cD",
  "original_url": "https://www.youtube.com/watch?v=abcdef123456"
}
```

- 잘못된 URL 오류: HTTP 422, JSON에 `detail` 검증 오류가 포함됩니다.

### 단축 URL 접속 및 리다이렉트

- 역할: 접속 횟수를 원자적으로 1 증가시킨 뒤 원본 URL로 이동합니다.
- 방식/주소: `GET http://localhost:8000/{short_code}`
- 요청 JSON: 없음
- 정상 응답: HTTP 307, `Location` 응답 헤더가 저장된 원본 URL을 가리킵니다.
- 존재하지 않는 코드: HTTP 404, `{"detail":"단축 코드를 찾을 수 없습니다."}`

브라우저 주소창에 단축 URL을 직접 입력하면 원본 페이지로 이동합니다. Swagger에서 확인할 때는 Execute 후 응답 코드와 `Location` 헤더를 확인하세요. HTTP 클라이언트가 자동으로 리다이렉트를 따라가면 최종 응답이 원본 사이트 응답일 수 있으므로, 리다이렉트를 따라가지 않도록 설정하면 307을 확인할 수 있습니다.

### 단축 URL 정보 조회

- 역할: 원본 URL, 단축 코드, 생성 시간, 접속 횟수를 확인합니다.
- 방식/주소: `GET http://localhost:8000/api/urls/{short_code}`
- 요청 JSON: 없음
- 정상 응답: HTTP 200

```json
{
  "original_url": "https://www.youtube.com/watch?v=abcdef123456",
  "short_code": "aB12cD",
  "created_at": "2026-01-01T10:00:00Z",
  "click_count": 1
}
```

- 존재하지 않는 코드: HTTP 404, `{"detail":"단축 코드를 찾을 수 없습니다."}`

### 전체 URL 목록 조회

- 역할: 저장된 모든 URL을 생성 시각의 최신 순으로 조회합니다.
- 방식/주소: `GET http://localhost:8000/api/urls`
- 요청 JSON: 없음
- 정상 응답: HTTP 200, URL 정보 객체 배열 (데이터가 없으면 빈 배열 `[]`)
- DB 오류: HTTP 503, `{"detail":"데이터베이스 요청을 처리할 수 없습니다."}`

### 서버 및 DB 상태 확인

- 역할: API 서버와 DB 연결을 확인합니다.
- 방식/주소: `GET http://localhost:8000/health`
- 요청 JSON: 없음
- 정상 응답: HTTP 200, `{"status":"ok","database":"connected"}`
- DB 연결 오류: HTTP 503, `{"status":"degraded","database":"error"}`

## 7. 자동 테스트

테스트는 `TEST_DATABASE_URL`이 지정되면 그 DB를 사용하고, 지정되지 않으면 테스트 전용 SQLite 메모리 DB를 사용합니다. 개발용 `DATABASE_URL`은 테스트 엔진에 사용하지 않으며, 두 URL이 동일하게 설정된 경우 실수로 개발 DB를 변경하지 않도록 테스트 시작을 거부합니다. 테스트별 테이블을 준비하고 정리합니다.

필요하면 PostgreSQL의 **별도 테스트 데이터베이스**를 만들고 `.env`에 아래처럼 추가할 수 있습니다. 개발 DB와 같은 URL을 지정하지 마세요.

```dotenv
TEST_DATABASE_URL=postgresql+psycopg://short_url_test:테스트비밀번호@localhost:5432/short_url_test
```

전체 테스트 실행:

```powershell
pytest -v
```

테스트는 URL 입력 검증, 실제 ORM 저장, 코드 조회, 307 리다이렉트와 클릭 횟수 증가, 잘못된 코드의 404, 목록 조회, DB 오류의 503, `/health` 정상·오류 응답을 확인합니다. 통합 테스트는 단축 생성 → DB 저장 확인 → 접속 → 리다이렉트 확인 → 클릭 수 조회까지 한 번에 검증합니다.

## 8. PostgreSQL 저장 및 리다이렉트 확인

PostgreSQL의 `psql`에서 저장된 행을 확인할 수 있습니다.

```sql
SELECT id, original_url, short_code, created_at, click_count
FROM urls
ORDER BY created_at DESC;
```

단축 URL에 접속할 때마다 해당 행의 `click_count`가 1씩 증가합니다. 브라우저에서 직접 단축 주소를 열거나 `curl`로 리다이렉트 응답 헤더를 확인할 수 있습니다.

```powershell
curl.exe -i http://localhost:8000/aB12cD
```

정상 응답은 `307 Temporary Redirect`이며 `Location: https://...` 헤더가 원본 주소를 가리킵니다. 서버 로그나 `GET /api/urls/{short_code}` 응답에서 증가한 클릭 횟수도 확인하세요.

## 9. 자주 발생하는 오류

- **데이터베이스 연결 오류**: PostgreSQL 서비스가 실행 중인지, 호스트·포트·DB 이름·사용자·비밀번호가 `.env`의 `DATABASE_URL`과 일치하는지 확인합니다. 서버 로그와 `/health`의 HTTP 503 응답도 확인하세요.
- **`ModuleNotFoundError`**: 가상환경이 활성화되었는지 확인하고 `pip install -r requirements.txt`를 실행합니다.
- **PowerShell 가상환경 실행 정책 오류**: CMD의 활성화 명령을 사용하거나 조직의 PowerShell 실행 정책을 확인합니다.
- **HTTP 422**: 요청 JSON 키가 `original_url`인지, 값이 호스트를 포함하는 `http://` 또는 `https://` 주소인지 확인합니다.
- **HTTP 404**: 생성 응답의 `short_code`를 정확히 사용했는지 확인합니다.
- **테스트 시작 시 URL 동일 오류**: `DATABASE_URL`과 `TEST_DATABASE_URL`에 개발용 URL을 중복 지정하지 말고, 테스트 전용 DB URL을 사용하거나 테스트의 기본 SQLite 메모리 DB를 사용합니다.

## 10. 테스트 결과 기록

테스트 코드는 이 프로젝트 안에 포함되어 있으며, 실행 결과는 개발 환경에 따라 달라지므로 `pytest -v`를 실행해 실제 통과·실패를 확인합니다. PostgreSQL 서버가 없는 환경에서도 SQLite 테스트 DB로 API 및 ORM 흐름을 검증할 수 있습니다. PostgreSQL 연결과 실제 저장은 PostgreSQL을 실행한 뒤 위의 SQL 조회 방법으로 확인하세요.
