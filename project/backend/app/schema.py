from pydantic import BaseModel
from typing import List, Optional

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

class UserAnswer(BaseModel):
    answer: str
