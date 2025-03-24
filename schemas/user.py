# app/schemas/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    name: Optional[str]
    avatar: Optional[str]

class UserCreate(UserBase):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True #orm 객체를 pydantic으로 가져올 때 사용

class UserUpdate(UserBase):
    pass

class Token(BaseModel):
    access_token: str
    token_type: str
    
class UserLinkCreate(BaseModel):
    url: str

class UserLinkResponse(UserLinkCreate):
    id: int

    class Config:
        from_attributes = True