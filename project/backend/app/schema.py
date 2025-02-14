from pydantic import BaseModel, validator, Field
from typing import Optional

class StringCastingBase(BaseModel):
    @validator('*', pre=True)
    def cast_all_to_str(cls, value):
        if value is None:
            return value
        return str(value)

class NCSCode(StringCastingBase):
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

class UserAnswer(StringCastingBase):
    answer: str

class InterviewRequest(BaseModel):
    answer: str
    companyname : str 
    subcategory: str