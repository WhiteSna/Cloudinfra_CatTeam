"""FastAPI 애플리케이션과 단축 URL 서비스의 HTTP 엔드포인트를 정의합니다."""

import logging
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import crud
from app.database import Base, engine, get_db
from app.models import URL
from app.schemas import URLCreate, URLCreated, URLInfo

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """서버 시작 시 테이블을 준비하고, DB 장애가 있어도 상태 점검은 가능하게 합니다."""
    try:
        # 모델에 등록된 테이블이 없을 때만 생성하므로 기존 데이터는 삭제하지 않습니다.
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError:
        # 시작 시 연결 실패를 로그로 남기되 서버를 띄워 /health가 장애를 보고하게 합니다.
        logger.exception("서버 시작 중 데이터베이스 테이블을 준비하지 못했습니다.")
    yield


app = FastAPI(
    title="단축 URL 서비스 API",
    description="URL 단축, 리다이렉트, 접속 횟수와 서비스 상태를 관리합니다.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(_: Request, exception: SQLAlchemyError) -> JSONResponse:
    """처리되지 않은 DB 오류는 로그를 남기고 명시적인 서비스 오류로 응답합니다."""
    logger.exception("데이터베이스 요청 처리에 실패했습니다.", exc_info=exception)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "데이터베이스 요청을 처리할 수 없습니다."},
    )


@app.post(
    "/api/shorten",
    response_model=URLCreated,
    status_code=status.HTTP_201_CREATED,
    summary="긴 URL을 단축합니다",
)
def shorten_url(
    payload: URLCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> URLCreated:
    """검증된 원본 URL을 저장하고 생성한 단축 URL 정보를 반환합니다."""
    url = crud.create_url(db, payload.original_url)
    # 요청의 호스트 정보를 사용하므로 localhost뿐 아니라 배포 도메인에서도 동작합니다.
    short_url = f"{request.base_url}{url.short_code}"
    return URLCreated(
        short_code=url.short_code,
        short_url=short_url,
        original_url=url.original_url,
    )


@app.get(
    "/api/urls",
    response_model=list[URLInfo],
    summary="저장된 URL 목록을 조회합니다",
)
def list_urls(db: Session = Depends(get_db)) -> list[URL]:
    """저장된 모든 URL의 코드, 원본 주소, 생성 시각, 접속 횟수를 반환합니다."""
    return crud.get_all_urls(db)


@app.get(
    "/api/urls/{short_code}",
    response_model=URLInfo,
    summary="단축 URL 정보를 조회합니다",
)
def read_url(short_code: str, db: Session = Depends(get_db)) -> URL:
    """단축 코드가 없으면 HTTP 404, 있으면 저장 정보를 반환합니다."""
    url = crud.get_url_by_code(db, short_code)
    if url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="단축 코드를 찾을 수 없습니다.")
    return url


@app.get("/health", response_model=None, summary="서버 및 데이터베이스 상태를 확인합니다")
def health_check(db: Session = Depends(get_db)) -> JSONResponse | dict[str, str]:
    """간단한 DB 쿼리로 연결 상태를 검사하고 장애 시 HTTP 503을 반환합니다."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("상태 확인 중 데이터베이스 연결에 실패했습니다.")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "database": "error"},
        )
    return {"status": "ok", "database": "connected"}


@app.get("/{short_code}", response_class=RedirectResponse, summary="원본 URL로 리다이렉트합니다")
def redirect_to_original(short_code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    """코드가 있으면 접속 횟수를 먼저 증가시키고 HTTP 307로 원본 URL에 이동시킵니다."""
    original_url = crud.increment_click_count(db, short_code)
    if original_url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="단축 코드를 찾을 수 없습니다.")
    return RedirectResponse(url=original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
