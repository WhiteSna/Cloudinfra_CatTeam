"""PostgreSQL에 저장될 단축 URL 테이블을 SQLAlchemy ORM으로 정의합니다."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class URL(Base):
    """원본 URL, 단축 코드, 생성 시각, 접속 횟수를 저장하는 테이블입니다."""

    # 테이블 이름은 요구사항과 동일하게 urls로 지정합니다.
    __tablename__ = "urls"

    # 기본키는 데이터베이스가 새 행마다 자동 증가시킵니다.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # 원본 URL은 길이 제한 없이 저장하기 위해 PostgreSQL TEXT를 사용합니다.
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    # unique 제약조건은 코드 생성이 우연히 겹쳐도 DB에서 중복 저장을 막습니다.
    short_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    # DB 서버가 행을 생성하는 시각을 기록해 서버/클라이언트 시간 차이를 줄입니다.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # 새 URL은 접속 전이므로 0부터 시작하고, DB에서도 기본값을 보장합니다.
    click_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
