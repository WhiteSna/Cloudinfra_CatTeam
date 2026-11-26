from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text
from app.database import Base


# PostgreSQL의 'urls' 테이블과 연결되는 ORM 모델 클래스입니다.
# 파이썬 클래스 하나가 데이터베이스 테이블 한 개를 뜻합니다.
class URL(Base):
    __tablename__ = "urls"  # 실제 DB에 만들어질 테이블 이름입니다.

    # 각 데이터를 구분하는 고유 번호(기본키, 1부터 자동으로 1씩 증가합니다.)
    id = Column(Integer, primary_key=True, index=True)

    # 사용자가 줄이려고 입력한 긴 URL입니다. 길이 제한이 있을 수 있어 Text 타입을 씁니다.
    original_url = Column(Text, nullable=False)

    # 단축 URL 뒤에 붙는 짧은 코드입니다. 중복되면 안 되므로 unique=True를 주고,
    # 검색을 빠르게 하려고 index=True를 설정합니다.
    short_code = Column(String(20), unique=True, index=True, nullable=False)

    # 단축 URL이 만들어진 시간입니다. 새 데이터가 생길 때 현재 UTC 시간이 자동으로 들어갑니다.
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # 단축 URL이 클릭된 횟수입니다. 처음 만들 때는 0으로 시작합니다.
    click_count = Column(Integer, default=0, nullable=False)