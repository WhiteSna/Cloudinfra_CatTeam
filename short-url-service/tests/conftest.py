"""테스트 전용 DB를 지정하고 각 테스트의 데이터를 격리합니다."""

import os

# TEST_DATABASE_URL이 설정되지 않으면 휘발성 SQLite 메모리 DB를 사용합니다.
# 이 기본값 덕분에 테스트가 개발 PostgreSQL에 접속하거나 데이터를 바꾸지 않습니다.
test_database_url = os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
configured_database_url = os.getenv("DATABASE_URL")
if configured_database_url and configured_database_url == test_database_url:
    raise RuntimeError("DATABASE_URL과 TEST_DATABASE_URL은 서로 다른 데이터베이스여야 합니다.")

# 앱 모듈이 엔진을 만들기 전에 테스트 DB URL을 지정해야 하므로 이곳에서 먼저 설정합니다.
os.environ["DATABASE_URL"] = test_database_url

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    """각 테스트 전후 테이블을 비워 테스트 간 데이터가 섞이지 않게 합니다."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session() -> Session:
    """테스트에서 저장된 ORM 행을 직접 검증할 독립 세션을 제공합니다."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


