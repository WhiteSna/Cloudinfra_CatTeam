"""API 요청값을 검증하고 응답에 포함할 데이터 모양을 정의합니다."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator


class URLCreate(BaseModel):
    """단축할 원본 URL을 JSON 요청에서 받는 스키마입니다."""

    original_url: str

    @field_validator("original_url")
    @classmethod
    def validate_original_url(cls, value: str) -> str:
        """HTTP(S) 주소와 호스트가 있는 URL만 허용하고 입력 문자열은 보존합니다."""
        if any(character.isspace() for character in value):
            raise ValueError("http 또는 https 형식의 올바른 URL을 입력해 주세요.")
        try:
            # HttpUrl은 scheme, 호스트, 포트 형식까지 검사하며 반환 시에는 원문을 유지합니다.
            HttpUrl(value)
        except ValueError as exception:
            raise ValueError("http 또는 https 형식의 올바른 URL을 입력해 주세요.") from exception
        return value


class URLCreated(BaseModel):
    """단축 URL 생성 결과를 클라이언트에 반환하는 응답 스키마입니다."""

    short_code: str
    short_url: str
    original_url: str


class URLInfo(BaseModel):
    """조회 API가 URL의 저장 정보와 접속 횟수를 반환할 때 사용합니다."""

    # from_attributes=True로 ORM 객체의 속성을 같은 이름의 응답 필드로 변환합니다.
    model_config = ConfigDict(from_attributes=True)

    original_url: str
    short_code: str
    created_at: datetime
    click_count: int
