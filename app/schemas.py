from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from uuid import UUID
from typing import Optional

import re 
from enum import Enum



# Request validation:
# - username must be a valid email
# - password length >= 8
# - first_name/last_name required

class UserCreate(BaseModel):

   
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    username: EmailStr
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):

    first_name: Optional[str] = Field(None, min_length=1)
    last_name: Optional[str] = Field(None, min_length=1)
    password: Optional[str] = Field(None, min_length=8)

    @field_validator('first_name', 'last_name', 'password')
    @classmethod
    def check_not_empty(cls,v):

        if v is not None and len(v.strip()) == 0:
            raise ValueError('Field cannot be empty or whitespace')
        return v
    
class UserResponse(BaseModel):
   
    id: UUID
    
    first_name: str
    last_name: str
    username: str
    account_created: datetime
    account_updated: datetime    


    class Config:
        from_attributes = True





# ==================== Course Schemas ====================

class ClassificationEnum(str, Enum):
    core = "core"
    elective = "elective"

class CourseCreate(BaseModel):
    department_code: str = Field(..., min_length=2, max_length=6)
    number: str = Field(..., min_length=1, max_length=6)
    title: str = Field(..., min_length=1, max_length=255)
    credit_hours: int = Field(..., ge=1, le=8)
    classification: ClassificationEnum
    description: Optional[str] = Field(None, max_length=2000)
    prerequisites: Optional[str] = Field(None, max_length=512)

    @field_validator('department_code')
    @classmethod
    def validate_department_code(cls, v):
        if not re.match(r'^[A-Z]{2,6}$', v):
            raise ValueError('department_code must be 2-6 uppercase letters only')
        return v

class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    credit_hours: Optional[int] = Field(None, ge=1, le=8)
    classification: Optional[ClassificationEnum] = None
    description: Optional[str] = Field(None, max_length=2000)
    prerequisites: Optional[str] = Field(None, max_length=512)

    # 注意：空 body 的 400 检查放在 route 层做，这里不加 model_validator
    # 原因：Pydantic validator 抛出的错误会变成 422，作业要求是 400

class CourseResponse(BaseModel):
    id: UUID
    department_code: str
    number: str
    title: str
    credit_hours: int
    classification: str
    description: Optional[str] = None
    prerequisites: Optional[str] = None
    has_syllabus: bool
    date_created: datetime
    date_updated: datetime

    class Config:
        from_attributes = True

# ==================== Syllabus Schemas ====================

class SyllabusResponse(BaseModel):
    id: UUID
    course_id: UUID
    file_name: str
    s3_bucket_name: str
    s3_object_key: str
    content_type: str
    file_size: int
    url: str
    date_created: datetime
    date_updated: datetime

    class Config:
        from_attributes = True