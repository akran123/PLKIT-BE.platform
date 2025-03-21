# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import jwt
from pydantic import BaseModel, EmailStr
from typing import Optional
import crud, schemas, database
from config import settings
from schemas.auth import Token, TokenData, UserResponse, UserCreate
from database import get_db

# 설정된 OAuth2PasswordBearer 인스턴스 생성
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") # 토큰 받기 위한 경로

router = APIRouter(prefix="/auth", tags=["Auth"])


# JWT 액세스 토큰 생성 함수
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):  
    #들어오는 데이터 형식dict,expires_delta: 기본값 none 추가 가능
    
    """
    JWT 액세스 토큰을 생성합니다.

    Args:
        data (dict): 토큰에 포함할 데이터.
        expires_delta (Optional[timedelta]): 토큰 만료 시간 설정. 기본값은 설정 파일의 시간.

    Returns:
        str: 생성된 JWT 토큰 문자열.
    """
    to_encode = data.copy()  
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES) #30분으로 정의되어있음
    )
    #expires_delta 가 없으면 30분 있을 시 expire_delta 사용
    to_encode.update({"exp": expire}) #jwt 토큰에 만료시간 포함(추후 검증을 통해서 만료여부 판단)
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )  #jwt 토큰 암호화 함수 
    # 포함될 데이터, 세팅의 시크릿 키, 인코딩알고리즘
    #secret key 토큰 암호화(서명)하는데 필요한 키
    return encoded_jwt


# 현재 사용자 검증 함수
async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    # Authorize 헤더에 있는 jwt 토큰을 추출함, db는 session에 있는 db에 의존
    """
    JWT 토큰을 통해 현재 사용자를 확인합니다.

    Args:
        token (str): 인증 헤더의 JWT 토큰.
        db (Session): 데이터베이스 세션 종속성.

    Returns:
        User: 인증된 사용자의 User 객체.

    Raises:
        HTTPException: 토큰이 유효하지 않거나 사용자를 찾을 수 없는 경우 발생.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명을 확인할 수 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )  #인증 실패할 때 띄우는 메세지 
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        ) #들어오는 토큰을 알아볼 수 있게 바꿈 json 형식식
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)   #pydantic 모델의 검증 절차 이메일 검증
    except jwt.PyJWTError:  
        raise credentials_exception
    user = crud.user.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


# 로그인 엔드포인트
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    사용자를 인증하고 JWT 액세스 토큰을 반환합니다.

    Args:
        form_data (OAuth2PasswordRequestForm): 사용자의 이메일과 비밀번호를 포함.
        db (Session): 데이터베이스 세션 종속성.

    Returns:
        dict: 액세스 토큰과 토큰 타입이 포함된 응답.

    Raises:
        HTTPException: 사용자의 인증 정보가 올바르지 않을 때 발생.
    """
    user = crud.user.get_user_by_email(db, email=form_data.username)   #이메일을 통해 로그인을 검증함
    if not user or not crud.user.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 일치하지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES) # 토큰 만료 시간 설정
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )  # 토큰생성에 필요한 데이터들 담아서 노큰 생성
    # WWW-Authenticate : 클라이언트가 인증이 필요할 때 서버가 인증 방식(Bearer 등)을 명시하는 HTTP 헤더
    return {"access_token": access_token, "token_type": "bearer"}   #토큰과 토큰의 타입을 반환


# 회원가입 엔드포인트
@router.post("/signup", response_model=UserResponse)
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    # UserCreat 스키마를 통해 들어오는 데이터 검증, 디비 세션 의존, 반환 모델 UserResponse 스키마
    """
    새로운 사용자를 등록합니다.

    Args:
        user (UserCreate): 새 사용자 정보 (이메일, 비밀번호 등 포함).
        db (Session): 데이터베이스 세션 종속성.

    Returns:
        UserResponse: 새로 생성된 사용자에 대한 정보.

    Raises:
        HTTPException: 이메일이 이미 등록된 경우 발생.
    """
    db_user = crud.user.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이메일이 이미 등록되어 있습니다.",
        )
    new_user = crud.user.create_user(db=db, user=user)  #json 형식 데이터
    print(new_user.__dict__)
    return new_user  #UserResponse 형식에 맞게 데이터 반환
