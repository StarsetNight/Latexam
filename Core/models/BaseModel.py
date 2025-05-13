from datetime import datetime

from pydantic import BaseModel as BaseModel_
from ujson import dumps


class BaseModel(BaseModel_):
    class Config:
        json_dumps = lambda obj, **kwargs: dumps(obj, ensure_ascii=False, **kwargs)
        json_encoders = {
            datetime: lambda v: int(v.timestamp())  # 将datetime转换为时间戳
        }
        orm_mode = True
