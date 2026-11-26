# 단축 URL 서비스 API 가이드 및 최종 테스트 결과

## 1. 가상환경 및 패키지 설치
- python -m venv .venv
- .\.venv\Scripts\Activate.ps1
- pip install -r requirements.txt

## 2. 환경변수(.env) 설정
- .env.example을 참고해 루트에 .env 파일을 생성합니다.
- DATABASE_URL=postgresql+psycopg://postgres:비밀번호@localhost:5432/shortener

## 3. 서버 실행 및 Swagger UI
- uvicorn app.main:app --reload
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## 4. 주요 API 목록 및 예시
- POST /api/shorten: 원본 URL을 받아 단축 코드 생성 및 저장
  - 요청 예시: {"original_url": "[https://www.youtube.com/watch?v=abcdef123456](https://www.youtube.com/watch?v=abcdef123456)"}
  - 정상 응답(201): {"short_code": "aB12cD", "short_url": "http://localhost:8000/aB12cD", "original_url": "..."}
  - 오류 응답(422): 잘못된 URL 형식 입력 시 검증 오류 반환
- GET /{short_code}: 단축 코드 조회 후 원본 URL로 리다이렉트(307) 및 click_count 1 증가 (없으면 404)
- GET /api/urls/{short_code}: 단건 URL 정보(original_url, short_code, created_at, click_count) 조회 (없으면 404)
- GET /api/urls: 전체 URL 목록 조회
- GET /health: 서버 및 DB 연결 상태 확인

## 5. 자주 발생하는 오류와 해결 방법
- DB 접속 오류: PostgreSQL 서비스 실행 여부와 .env의 DATABASE_URL(사용자명, 비밀번호, 포트, DB명) 확인
- Git에 .env나 .venv가 보이는 경우: .gitignore에 .env, .venv/, app/.venv/, __pycache__/, .pytest_cache/ 포함 여부 확인

## 6. 최종 테스트 결과 보고
- 자동 테스트(pytest -v): shortener_test DB 기준으로 총 14개 테스트 통과(14 passed) - 생성, 리다이렉트, 클릭 수 증가, 조회/목록, 헬스체크, 404/잘못된 입력 등 정상 및 오류 케이스와 통합 흐름 검증 완료
- DB 저장 확인: PostgreSQL urls 테이블에 레코드 생성 및 접속 시 click_count 증가 확인
- 리다이렉트 확인: GET /{short_code} 호출 시 원본 URL로 리다이렉트 응답 및 click_count 증가 확인
