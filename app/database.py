import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# .env 파일에 적어둔 환경변수(DATABASE_URL)를 읽어옵니다.
load_dotenv()

# .env에서 DATABASE_URL을 가져오고, 없으면 기본 로컬 주소를 씁니다.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:1234@localhost:5432/shortener",
)

# PostgreSQL과 연결하는 엔진을 만듭니다. (pool_pre_ping=True는 끊긴 연결을 미리 체크해 줍니다.)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# DB에 읽고 쓸 때 사용할 세션(대화 창구)을 찍어내는 공장입니다.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 앞으로 만들 테이블 모델들이 상속받을 기본 클래스입니다.
Base = declarative_base()


# API 요청마다 DB 세션을 하나 열고, 끝나면 자동으로 닫아주는 함수입니다.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()