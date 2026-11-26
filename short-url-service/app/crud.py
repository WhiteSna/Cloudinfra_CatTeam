"""엔드포인트와 DB 작업을 분리해 URL 생성·조회·접속 횟수를 처리합니다."""

import secrets
import string

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import URL

# 62개 문자 조합으로 짧고 추측하기 어려운 단축 코드를 만듭니다.
CODE_CHARACTERS = string.ascii_letters + string.digits
CODE_LENGTH = 6
MAX_CODE_ATTEMPTS = 5


def create_url(db: Session, original_url: str) -> URL:
    """고유 코드를 생성하고 URL 행을 저장합니다.

    코드 충돌은 매우 드물지만, 마지막 방어선은 DB의 unique 제약조건입니다.
    해당 코드가 실제로 이미 존재하는 충돌일 때만 새 코드를 만들어 재시도합니다.
    """
    for _ in range(MAX_CODE_ATTEMPTS):
        short_code = "".join(secrets.choice(CODE_CHARACTERS) for _ in range(CODE_LENGTH))
        url = URL(original_url=original_url, short_code=short_code, click_count=0)
        db.add(url)
        try:
            db.commit()
            db.refresh(url)
            return url
        except IntegrityError:
            # 실패한 트랜잭션은 재사용할 수 없으므로 rollback 후 충돌 원인을 확인합니다.
            db.rollback()
            existing_url = db.scalar(select(URL.id).where(URL.short_code == short_code))
            if existing_url is None:
                # 코드 중복이 아닌 제약조건 오류는 재시도하지 않고 호출자에게 전달합니다.
                raise

    # 다섯 번 연속 충돌한 경우 오류를 숨기지 않고 마지막 DB 예외를 발생시킵니다.
    raise IntegrityError(
        "단축 코드 생성",
        {"attempts": MAX_CODE_ATTEMPTS},
        Exception("고유한 단축 코드를 생성하지 못했습니다."),
    )


def get_url_by_code(db: Session, short_code: str) -> URL | None:
    """단축 코드에 해당하는 ORM 행을 찾고, 없으면 None을 반환합니다."""
    return db.scalar(select(URL).where(URL.short_code == short_code))


def get_all_urls(db: Session) -> list[URL]:
    """최근 생성한 URL부터 목록으로 반환해 새 데이터 확인을 쉽게 합니다."""
    statement = select(URL).order_by(URL.created_at.desc(), URL.id.desc())
    return list(db.scalars(statement).all())


def increment_click_count(db: Session, short_code: str) -> str | None:
    """원자적 UPDATE로 접속 횟수를 하나 늘리고 해당 원본 URL을 반환합니다.

    증가를 DB 한 번의 연산으로 수행하므로 동시 접속에서 읽기-수정-쓰기 경합으로
    횟수가 누락되는 일을 방지합니다. 코드가 없으면 아무 행도 바꾸지 않습니다.
    """
    statement = (
        update(URL)
        .where(URL.short_code == short_code)
        .values(click_count=URL.click_count + 1)
        .returning(URL.original_url)
    )
    original_url = db.execute(statement).scalar_one_or_none()
    if original_url is None:
        return None

    db.commit()
    return original_url
