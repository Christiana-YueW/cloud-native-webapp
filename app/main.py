from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import Response, JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from app.database import get_db, engine, Base
from app.models import User, HealthCheck
from app.schemas import UserCreate, UserUpdate, UserResponse
from app.auth import hash_password, get_current_user
from datetime import datetime, timezone
import base64


Base.metadata.create_all(bind=engine)

app = FastAPI(

    title="CSYE 6225 - Cloud Native Web Application",
    description="""

    CSYE 6225 - Cloud Native Web Application - Spring 2026

    ## Overview 
    RESTful API for user account management with authentication support.
    
    ## Authentication
    This API uses HTTP Basic Authentication for protected endpoints. 
    Use your registered email address as the username and your account password.
    
    ## Versioning
    API versioning is handled via URL path prefix (e.g., `/v1/`).
    """,
    version="1.0.0",

)

### validate the request

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    raw_errors = exc.errors()
    content_type = request.headers.get("content-type", "")

    def normalize(obj):
        # 把 bytes 转成可 JSON 的字符串
        if isinstance(obj, (bytes, bytearray)):
            # 直接 decode（不可 decode 就用 base64）
            try:
                return obj.decode("utf-8", errors="replace")
            except Exception:
                return base64.b64encode(obj).decode("ascii")
        if isinstance(obj, dict):
            return {k: normalize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [normalize(v) for v in obj]
        if isinstance(obj, tuple):
            return [normalize(v) for v in obj]  # tuple 改 list
        return obj

    errors = normalize(raw_errors)

    # 判断是否 body 解析格式错误
    def is_body_loc(e):
        loc = e.get("loc")
        return isinstance(loc, (list, tuple)) and len(loc) > 0 and loc[0] == "body"

    is_body_format_error = any(
        is_body_loc(e) and e.get("type") in [
            "value_error.jsondecode",
            "type_error.dict",
            "json_invalid",
            "model_attributes_type",
        ]
        for e in raw_errors
    )

    # 非 application/json 且 body 格式错误 => 415
    if (not content_type.startswith("application/json")) and is_body_format_error:
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={
                "detail": "Unsupported Media Type. Content-Type must be application/json"
            },
        )

    # 其他校验错误 => 422
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
    )


######## HealthCheck API

@app.get('/healthz', status_code=status.HTTP_200_OK, 
         summary='Health Check Endpoint',
         description='''
         Returns server health status. Used by load balancers and orchestration tools.

         **Requirements:**
            - Must not accept request body
            - Must not accept query parameters
            - Response must not be cached
            
        **Status Codes:**
            - 200 OK: Service is healthy and database connection is successful
            - 400 Bad Request: Request contains body or query parameters
            - 405 Method Not Allowed: Only GET is supported
            - 503 Service Unavailable: Database connection failed or service unhealthy


         ''')

# GET only; 400 to reject any request body 
# insert into health_checks to verify DB connectivity; DB failure -> 503
# Response body must be empty; add no-cache headers


async def health_check(request: Request, db: Session = Depends(get_db)):

    # reject query parameters
    if request.query_params:

        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "X-Content-Type-Options": "nosniff"
            }
        )

    body = await request.body()

    if body:
        return Response(

            status_code=status.HTTP_400_BAD_REQUEST,
            headers={

                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                "X-Content-Type-Options": "nosniff"

            }

        )
    
    try:

        health_check_record = HealthCheck()
        db.add(health_check_record)
        db.commit()

        return Response(
            status_code=status.HTTP_200_OK,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "X-Content-Type-Options": "nosniff"
            }
        )
    
    except Exception:

        db.rollback()

        return Response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "X-Content-Type-Options": "nosniff"
            }

        )

# only get is allowed. others are not allowed 

@app.api_route('/healthz', methods=['POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'],
               summary='Health Check - method not allowed')
async def health_check_method_not_allowed():

    return Response(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff"
        }
    )


########## User management API

@app.post('/v1/user', response_model=UserResponse,
          status_code=status.HTTP_201_CREATED, 
          summary='Create a user account', 
          description='''
            Creates a new user account with the provided information.

            **Validation Rules:**
            - Email must be unique and valid format
            - Password must be at least 8 characters
            - First name and last name are required
    
            **Notes:**
            - Password is stored using BCrypt hashing
            - `id`, `account_created`, and `account_updated` are set by the server
            - User cannot set values for `account_created` or `account_updated`
            - Password is never returned in response
    
            **Status Codes:**
            - 201 Created: User account successfully created
            - 400 Bad Request: Validation failed or user already exists
          
          ''')

def create_user(user: UserCreate, db: Session = Depends(get_db)):
    
    existing_user = db.query(User).filter(User.username == user.username).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    
    hashed_password = hash_password(user.password)

    new_user = User(

        username=user.username,
        password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name

    )


    db.add(new_user)
    db.commit()
    db.refresh(new_user)


    return new_user


@app.get("/v1/user/self", response_model=UserResponse, status_code=status.HTTP_200_OK,
         summary='Get user account information',
         description='''
         
         Retrieves the authenticated user's account information.
    
        **Authentication Required:** HTTP Basic Auth
    
        **Notes:**
            - User can only retrieve their own account information
            - Response includes all user fields except password
    
        **Status Codes:**
            - 200 OK: User information successfully retrieved
            - 401 Unauthorized: Authentication failed
         
         ''')


def get_user(current_user: User = Depends(get_current_user)):


    return current_user



@app.put("/v1/user/self", status_code=status.HTTP_204_NO_CONTENT,
         summary='Update user account information',
         description='''
         Updates the authenticated user's account information.
    
        **Authentication Required:** HTTP Basic Auth
        
        **Updatable Fields:**
        - `first_name`
        - `last_name`
        - `password`
        
        **Non-Updatable Fields:**
        - `id` (immutable)
        - `username` (immutable)
        - `account_created` (set by server)
        - `account_updated` (automatically updated by server)
        
        **Notes:**
        - At least one field must be provided for update
        - Attempting to update non-updatable fields will result in 400 error
        - `account_updated` is automatically set to current timestamp on successful update
        - New password is hashed using BCrypt before storage
        
        **Status Codes:**
        - 204 No Content: Update successful (no response body)
        - 400 Bad Request: Invalid fields or no fields provided
        - 401 Unauthorized: Authentication failed
         
         
         
         
         
         ''')

# Only first_name, last_name, password can be updated
# account_updated is set by server on success
# Return 400 for attempts to update any other field

async def update_user(
    request: Request,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    raw = await request.json()

    forbidden = {"id", "username", "account_created", "account_updated"}
    if any(k in raw for k in forbidden):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attempting to update read-only field"
        )

    update_data = user_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update"
        )
    
    #update each part
    if user_update.first_name is not None:
        current_user.first_name = user_update.first_name
    
    if user_update.last_name is not None:
        current_user.last_name = user_update.last_name
    
    if user_update.password is not None:
        current_user.password = hash_password(user_update.password)

    db.commit()
    db.refresh(current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

######################
@app.get('/',
         summary='API Information',
         description="Returns basic API information and available endpoints")

def root():
    
    return {

        "message": "CSYE 6225 - Cloud Native Web Application API",
        "version": "1.0.0",
        "endpoints": {
            "health_check": "GET /healthz",
            "create_user": "POST /v1/user",
            "get_user": "GET /v1/user/self",
            "update_user": "PUT /v1/user/self",
            "api_docs": "/docs"
        }

    }