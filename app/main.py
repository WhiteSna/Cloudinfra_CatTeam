from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import Base, engine, get_db


# FastAPI 앱이 시작될 때와 종료될 때 실행되는 생명주기(lifespan) 함수입니다.
# 서버 시작 시 PostgreSQL에 urls 테이블이 없으면 자동으로 생성합니다.
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError:
        # 시작 시점 DB 연결 일시 오류로 테이블 생성에 실패해도 앱 기동 자체는 이어갑니다.
        # 실제 DB 연결 상태는 /health 및 각 API 요청에서 확인합니다.
        pass
    yield


# FastAPI 애플리케이션 인스턴스를 생성합니다.
app = FastAPI(
    title="URL Shortener Service API",
    description="단축 URL 생성, 리다이렉트, 클릭 수 추적 및 URL 조회 API",
    version="1.0.0",
    lifespan=lifespan,
)


# [기능 1] 긴 URL을 짧은 URL로 변환하는 엔드포인트입니다.
# 요청: POST /api/shorten, Body: {"original_url": "https://..."}
# 응답: 201 Created, {"short_code": "...", "short_url": "...", "original_url": "..."}
@app.post(
    "/api/shorten",
    response_model=schemas.ShortenResponse,
    status_code=status.HTTP_201_CREATED,
)
def shorten_url(
    payload: schemas.URLCreateRequest,
    request: Request,
    db: Session = Depends(get_db),  # 요청마다 DB 세션을 주입받고 끝나면 자동으로 닫습니다.
):
    try:
        # Pydantic의 HttpUrl 객체를 문자열로 변환해 DB에 저장합니다.
        created = crud.create_url(db=db, original_url=str(payload.original_url))

        # 현재 요청이 들어온 기본 주소(예: http://localhost:8000/) 뒤의 슬래시를 제거합니다.
        base_url = str(request.base_url).rstrip("/")

        return schemas.ShortenResponse(
            short_code=created.short_code,
            short_url=f"{base_url}/{created.short_code}",
            original_url=created.original_url,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터베이스 저장 중 오류가 발생했습니다.",
        ) from exc


# [기능 4] 특정 단축 코드의 상세 정보(원본 URL, 생성 시간, 접속 횟수)를 조회합니다.
# 주의: /{short_code} 보다 먼저 선언해야 /api/urls/... 경로가 /{short_code} 로 잘못 잡히지 않습니다.
@app.get("/api/urls/{short_code}", response_model=schemas.URLInfoResponse)
def get_url_info(short_code: str, db: Session = Depends(get_db)):
    try:
        url_obj = crud.get_url_by_code(db=db, short_code=short_code)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터베이스 조회 중 오류가 발생했습니다.",
        ) from exc

    if url_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지 않는 단축 코드입니다.",
        )

    return url_obj


# [기능 5] 저장된 전체 URL 목록을 조회합니다.
@app.get("/api/urls", response_model=list[schemas.URLInfoResponse])
def list_urls(db: Session = Depends(get_db)):
    try:
        return crud.get_all_urls(db=db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="URL 목록 조회 중 오류가 발생했습니다.",
        ) from exc


# [기능 6] 서버 및 PostgreSQL 데이터베이스 연결 상태를 확인합니다.
@app.get("/health", response_model=schemas.HealthResponse)
def health_check(db: Session = Depends(get_db)):
    try:
        # SELECT 1 쿼리를 실행해 PostgreSQL과 실제로 통신이 되는지 점검합니다.
        db.execute(text("SELECT 1"))
        return schemas.HealthResponse(
            status="ok",
            database="connected",
            detail="API server and PostgreSQL connection are healthy.",
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL 데이터베이스 연결에 실패했습니다.",
        ) from exc


# [기능 2 & 3] 단축 URL 접속 시 원본 URL로 리다이렉트하고 click_count를 1 증가시킵니다.
# status_code=307 을 사용해 원본 URL로 리다이렉트합니다.
@app.get("/{short_code}", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
def redirect_to_original_url(short_code: str, db: Session = Depends(get_db)):
    try:
        url_obj = crud.get_url_by_code(db=db, short_code=short_code)
        if url_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 단축 코드입니다.",
            )

        # 접속 횟수(click_count)를 1 증가시킨 뒤 저장합니다.
        updated = crud.increment_click_count(db=db, url_obj=url_obj)
        return RedirectResponse(
            url=updated.original_url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    except HTTPException:
        # 404 에러는 그대로 클라이언트에 전달합니다.
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="리다이렉트 처리 중 데이터베이스 오류가 발생했습니다.",
        ) from exc