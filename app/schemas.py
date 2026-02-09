from pydantic import BaseModel


class DataItem(BaseModel):
    source: str
    payload: dict


class TimezoneEntry(BaseModel):
    zone_name: str
    abbreviation: str
    offset_seconds: int
    dst: int


class ApiKeyResponse(BaseModel):
    api_key: str
    created_at: str
