from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from uuid import UUID
from typing import Optional


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

# check to make sure no empty or whitespace
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