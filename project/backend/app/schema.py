from pydantic import BaseModel, validator
from typing import Optional

class UserAnswer(BaseModel):
    answer: str

class NCSCode(BaseModel):
    ncsDegr: Optional[str]
    ncsLclasCd: Optional[str]
    ncsLclasCdNm: Optional[str]
    ncsMclasCd: Optional[str]
    ncsMclasCdNm: Optional[str]
    ncsSclasCd: Optional[str]
    ncsSclasCdNm: Optional[str]
    ncsSubdCd: Optional[str]
    ncsSubdCdNm: Optional[str]
    dutyCd: Optional[str]

    @validator('*', pre=True)
    def cast_all_to_str(cls, value):
        if value is None:
            return value
        return str(value)
