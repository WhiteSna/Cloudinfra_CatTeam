"""환경변수로 설정한 데이터베이스와 SQLAlchemy 세션을 준비합니다."""

import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

# 프로젝트 디렉터리의 .env 파일을 읽어 비밀 정보가 코드에 들어가지 않게 합니다.
load_dotenv()

# 개발 환경에서는 PostgreSQL 주소를 .env의 DATABASE_URL에 지정합니다.
# 기본 주소는 로컬 개발용 예시이며, 운영 비밀번호를 코드에 기록하지 않습니다.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://short_url_user:change_me@localhost:5432/short_url_db",
)

# SQLite 메모리 DB는 연결이 바뀌면 데이터가 사라지므로 테스트에서 같은 연결을 공유합니다.
engine_options: dict[str, object] = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
    if ":memory:" in DATABASE_URL:
        engine_options["poolclass"] = StaticPool

# Engine은 연결 풀을 관리하고, SessionLocal은 요청마다 DB 작업 단위를 만듭니다.
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """모든 ORM 테이블 모델이 상속하는 공통 기반 클래스입니다."""


def get_db() -> Generator[Session, None, None]:
    """요청 하나에서 사용할 세션을 제공하고, 요청 종료 후 반드시 닫습니다.

    FastAPI의 Depends가 이 생성기를 호출해 엔드포인트에 세션을 전달합니다.
    finally를 사용하므로 정상 응답과 예외 응답 모두에서 연결 자원이 반환됩니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
