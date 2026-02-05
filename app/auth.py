import bcrypt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User




#### HTTP basic auth 
security = HTTPBasic()

# Hash passwords with BCrypt (salt included) before storing.
def hash_password(password: str) -> str:


    password_bytes = password.encode('utf-8')
    
    salt = bcrypt.gensalt(rounds=12)
    
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    return hashed.decode('utf-8')

# Validate credentials by comparing plaintext input against stored BCrypt hash.
def verify_password(plain_password: str, hashed_password: str) -> bool:


    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    
    return bcrypt.checkpw(password_bytes, hashed_bytes)



# HTTP Basic Auth: username is the user's email address (field name: username).
def get_current_user(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:

    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    if not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return user