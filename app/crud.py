import secrets
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models import URL


# 중복되지 않는 짧은 코드(예: aB12cD)를 생성하는 함수입니다.
# db 세션을 받아서 이미 DB에 같은 short_code가 있는지 확인한 뒤, 없을 때만 반환합니다.
def generate_unique_short_code(db: Session, length: int = 6) -> str:
    # URL에 안전하게 들어갈 수 있는 문자 집합(영문 대/소문자 + 숫자)입니다.
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    while True:
        # 지정한 길이(기본 6글자)만큼 랜덤 코드를 조합합니다.
        code = "".join(secrets.choice(alphabet) for _ in range(length))

        # DB의 urls 테이블에서 동일한 short_code가 이미 존재하는지 조회합니다.
        stmt = select(URL).where(URL.short_code == code)
        existing = db.execute(stmt).scalar_one_or_none()

        # 중복된 코드가 없다면 이 코드를 확정해서 돌려줍니다.
        if existing is None:
            return code


# 새로운 원본 URL을 받아 단축 코드를 만들고 DB에 저장(Create)하는 함수입니다.
def create_url(db: Session, original_url: str) -> URL:
    try:
        # 1. 중복되지 않는 단축 코드를 먼저 생성합니다.
        short_code = generate_unique_short_code(db)

        # 2. URL 모델 인스턴스를 만듭니다. (click_count는 모델 기본값 0으로 시작합니다.)
        db_url = URL(
            original_url=original_url,
            short_code=short_code,
        )

        # 3. 세션에 추가하고, commit()으로 PostgreSQL에 실제 저장합니다.
        db.add(db_url)
        db.commit()

        # 4. DB에서 자동 생성된 id, created_at 등의 값을 객체에 최신화합니다.
        db.refresh(db_url)
        return db_url
    except SQLAlchemyError:
        # 저장 중 DB 오류가 나면 변경 내역을 되돌리고(rollback) 예외를 밖으로 전달합니다.
        db.rollback()
        raise


# short_code로 단건 URL 정보를 조회(Read)하는 함수입니다.
def get_url_by_code(db: Session, short_code: str) -> URL | None:
    stmt = select(URL).where(URL.short_code == short_code)
    return db.execute(stmt).scalar_one_or_none()


# 저장된 전체 URL 목록을 최신순(id 내림차순)으로 조회(Read)하는 함수입니다.
def get_all_urls(db: Session) -> list[URL]:
    stmt = select(URL).order_by(URL.id.desc())
    return list(db.execute(stmt).scalars().all())


# 단축 URL에 접속했을 때 click_count를 1 증가시키고 저장(Update)하는 함수입니다.
def increment_click_count(db: Session, url_obj: URL) -> URL:
    try:
        url_obj.click_count += 1
        db.add(url_obj)
        db.commit()
        db.refresh(url_obj)
        return url_obj
    except SQLAlchemyError:
        db.rollback()
        raise