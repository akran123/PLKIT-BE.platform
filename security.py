# app/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt
from config import settings
import crud, database

# OAuth2PasswordBearer setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")  #토큰 받기위한 경로

# Dependency for getting the current user
async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명을 확인할 수 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},  
    )  # WWW-Authenticate : 클라이언트가 인증이 필요할 때 서버가 인증 방식(Bearer 등)을 명시하는 HTTP 헤더
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )          # response 헤더에 들어오는 payload를 디코드(해석)해서 토큰, 시크릿키 추출
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = crud.user.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user
