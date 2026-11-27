from datetime import datetime
from pydantic import BaseModel, ConfigDict, HttpUrl


# [요청 스키마] 사용자가 POST /api/shorten 으로 URL을 줄여달라고 보낼 때의 데이터 형식입니다.
# {"original_url": "https://www.youtube.com/watch?v=abcdef123456"} 형태를 검증합니다.
class URLCreateRequest(BaseModel):
    # HttpUrl 타입을 쓰면 http:// 또는 https:// 로 시작하는 올바른 URL 형식인지 자동으로 검사합니다.
    original_url: HttpUrl


# [응답 스키마 1] 단축 URL을 새로 만들었을 때(POST /api/shorten) 돌려줄 결과 형식입니다.
class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str


# [응답 스키마 2] DB에 저장된 URL 상세 정보(단건/목록 조회)를 돌려줄 때 쓰는 형식입니다.
class URLInfoResponse(BaseModel):
    # SQLAlchemy 모델 객체(예: URL 인스턴스)의 속성 값을 Pydantic 스키마로 바로 읽을 수 있게 허용합니다.
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_url: str
    short_code: str
    created_at: datetime
    click_count: int


# [응답 스키마 3] 서버 및 DB 상태를 확인할 때(GET /health) 돌려줄 응답 형식입니다.
class HealthResponse(BaseModel):
    status: str
    database: str
    detail: str | None = None