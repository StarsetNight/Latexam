from pydantic import BaseModel
from datetime import datetime


class BaseModel(BaseModel):
    class Config:
        # FIXME 'json_dumps' has been removed?
        json_dumps = lambda obj, **kwargs: dumps(obj, ensure_ascii=False, **kwargs)
        json_encoders = {
            datetime: lambda v: int(v.timestamp())  # 将datetime转换为时间戳
        }
