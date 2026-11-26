"""단축, 리다이렉트, 조회, 상태 확인 API의 정상·오류 흐름을 검증합니다."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models import URL


@pytest.fixture(autouse=True)
def override_db_dependency() -> Generator[None, None, None]:
    """모든 요청이 테스트 전용 엔진에 연결되도록 FastAPI 의존성을 교체합니다."""
    from app.database import SessionLocal

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def test_shorten_url_saves_url_and_returns_short_link(
    client: TestClient, db_session: Session
) -> None:
    """정상 입력은 코드와 URL을 저장하고 접속 횟수 0인 응답을 반환해야 합니다."""
    original_url = "https://www.youtube.com/watch?v=abcdef123456"

    response = client.post("/api/shorten", json={"original_url": original_url})

    assert response.status_code == 201
    body = response.json()
    assert len(body["short_code"]) == 6
    assert body["short_url"].endswith(f"/{body['short_code']}")
    assert body["original_url"] == original_url
    saved_url = db_session.query(URL).filter_by(short_code=body["short_code"]).one()
    assert saved_url.original_url == original_url
    assert saved_url.click_count == 0


@pytest.mark.parametrize(
    "invalid_url",
    ["not-a-url", "ftp://example.com/file", "https://", "https://example.com:invalid"],
)
def test_shorten_url_rejects_invalid_url(client: TestClient, invalid_url: str) -> None:
    """HTTP(S) 주소가 아니거나 호스트가 빠진 입력은 요청 검증 단계에서 거부해야 합니다."""
    response = client.post("/api/shorten", json={"original_url": invalid_url})
    assert response.status_code == 422


def test_duplicate_short_code_is_retried(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """생성 코드가 이미 사용 중이면 다시 생성해 고유 코드만 저장하는지 확인합니다."""
    db_session.add(
        URL(original_url="https://existing.example", short_code="aaaaaa", click_count=0)
    )
    db_session.commit()
    generated_characters = iter("aaaaaabbbbbb")
    monkeypatch.setattr("app.crud.secrets.choice", lambda _characters: next(generated_characters))

    response = client.post(
        "/api/shorten", json={"original_url": "https://new.example"}
    )

    assert response.status_code == 201
    assert response.json()["short_code"] == "bbbbbb"


def test_redirect_increments_count_and_info_api_returns_updated_count(
    client: TestClient,
) -> None:
    """생성부터 저장·리다이렉트·접속 횟수 조회까지 실제 사용자 흐름을 검증합니다."""
    original_url = "https://example.com/article"
    create_response = client.post("/api/shorten", json={"original_url": original_url})
    short_code = create_response.json()["short_code"]

    redirect_response = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_response.status_code == 307
    assert redirect_response.headers["location"] == original_url

    info_response = client.get(f"/api/urls/{short_code}")
    assert info_response.status_code == 200
    assert info_response.json()["original_url"] == original_url
    assert info_response.json()["click_count"] == 1


def test_repeated_redirect_increments_count_each_time(client: TestClient) -> None:
    """정상 접속마다 증가하고, 잘못된 코드 접속은 저장된 횟수에 영향을 주지 않아야 합니다."""
    short_code = client.post(
        "/api/shorten", json={"original_url": "https://example.com"}
    ).json()["short_code"]

    assert client.get(f"/{short_code}", follow_redirects=False).status_code == 307
    assert client.get(f"/{short_code}", follow_redirects=False).status_code == 307
    assert client.get("/missing-code", follow_redirects=False).status_code == 404
    assert client.get(f"/api/urls/{short_code}").json()["click_count"] == 2


def test_redirect_unknown_code_returns_404_without_changing_data(client: TestClient) -> None:
    """등록하지 않은 코드에 접속하면 404를 돌려주고 기존 URL 데이터는 그대로 둡니다."""
    response = client.get("/unknown", follow_redirects=False)
    assert response.status_code == 404


def test_read_url_unknown_code_returns_404(client: TestClient) -> None:
    """등록하지 않은 코드를 정보 조회 API로 요청하면 HTTP 404여야 합니다."""
    response = client.get("/api/urls/not-found")
    assert response.status_code == 404


def test_list_urls_returns_saved_rows(client: TestClient) -> None:
    """목록 응답에는 방금 저장한 코드와 원본 URL, 접속 횟수가 포함되어야 합니다."""
    original_url = "https://example.com/list"
    client.post("/api/shorten", json={"original_url": original_url})

    response = client.get("/api/urls")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["original_url"] == original_url
    assert response.json()[0]["click_count"] == 0


def test_health_reports_database_connection(client: TestClient) -> None:
    """정상 DB 연결 시 서버와 데이터베이스가 모두 정상이라는 응답을 확인합니다."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_database_errors_return_service_unavailable(client: TestClient) -> None:
    """목록 조회 중 DB 오류가 발생하면 오류를 숨기지 않고 HTTP 503을 반환합니다."""
    def broken_db():
        raise OperationalError("SELECT urls", {}, Exception("test database unavailable"))
        yield  # noqa: RET503

    app.dependency_overrides[get_db] = broken_db
    try:
        response = client.get("/api/urls")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert "데이터베이스" in response.json()["detail"]


def test_health_reports_database_failure(client: TestClient) -> None:
    """DB 연결 점검 실패 시 /health가 정상 상태로 가장하지 않고 503을 반환합니다."""
    class BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise OperationalError("SELECT 1", {}, Exception("test database unavailable"))

    def broken_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "error"}
