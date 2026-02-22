from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import Response, JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from app.database import get_db, engine, Base
from app.models import User, HealthCheck, Course, Syllabus
from app.schemas import UserCreate, UserUpdate, UserResponse, CourseCreate, CourseUpdate, CourseResponse, SyllabusResponse
from uuid import UUID
from app.auth import hash_password, get_current_user
from datetime import datetime, timezone
import base64
import httpx
import json
from sqlalchemy.exc import IntegrityError

import boto3
import uuid as uuid_lib
from fastapi import UploadFile, File
import os
import asyncio


# ==================== Cloud Platform Detection ====================

_detected_platform: str | None = None

CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
}

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
_s3_client = None

def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


async def safe_json(request: Request) -> dict:
    body = await request.body()
    if not body:
        return {}
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Malformed JSON"
        )


async def _detect_platform() -> str | None:
    timeout = httpx.Timeout(1.5)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                "http://metadata.google.internal/computeMetadata/v1/",
                headers={"Metadata-Flavor": "Google"}
            )
            if resp.status_code == 200:
                return "gcp"
    except Exception:
        pass
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            token_resp = await client.put(
                "http://169.254.169.254/latest/api/token",
                headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
                timeout=httpx.Timeout(1.0, connect=0.5)
            )
            if token_resp.status_code == 200:
                return "aws"
    except Exception:
        pass
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _detected_platform, S3_BUCKET_NAME
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
    if not S3_BUCKET_NAME:
        raise RuntimeError("S3_BUCKET_NAME environment variable is not set")
    Base.metadata.create_all(bind=engine)
    _detected_platform = await _detect_platform()
    yield

# ==================== App Init ====================

app = FastAPI(
    lifespan=lifespan,
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

# ==================== Validation Error Handler ====================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    raw_errors = exc.errors()
    content_type = request.headers.get("content-type", "")

    def normalize(obj):
        if isinstance(obj, (bytes, bytearray)):
            try:
                return obj.decode("utf-8", errors="replace")
            except Exception:
                return base64.b64encode(obj).decode("ascii")
        if isinstance(obj, dict):
            return {k: normalize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [normalize(v) for v in obj]
        if isinstance(obj, tuple):
            return [normalize(v) for v in obj]
        return obj

    errors = normalize(raw_errors)

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

    if (not content_type.startswith("application/json")) and is_body_format_error:
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={
                "detail": "Unsupported Media Type. Content-Type must be application/json"
            },
        )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": errors},
    )

# ==================== Health Check ====================

@app.get('/healthz', status_code=status.HTTP_200_OK,
         summary='Health Check Endpoint')
async def health_check(request: Request, db: Session = Depends(get_db)):

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
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
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

# ==================== Metadata Endpoint ====================

async def _get_gcp_metadata() -> dict:
    base = "http://metadata.google.internal/computeMetadata/v1"
    headers = {"Metadata-Flavor": "Google"}
    timeout = httpx.Timeout(5.0)

    async with httpx.AsyncClient(timeout=timeout) as client:

        async def get(path):
            r = await client.get(f"{base}{path}", headers=headers)
            r.raise_for_status()
            return r.text.strip()

        instance_id = await get("/instance/id")
        zone_full = await get("/instance/zone")
        region = zone_full.split("/")[-1]
        mt_full = await get("/instance/machine-type")
        machine_type = mt_full.split("/")[-1]
        iface_list_raw = await get("/instance/network-interfaces/")
        iface_indices = [
            line.strip().rstrip("/")
            for line in iface_list_raw.strip().splitlines()
            if line.strip()
        ]

        network_interfaces = []
        for idx in iface_indices:
            private_ip = await get(f"/instance/network-interfaces/{idx}/ip")
            try:
                public_ip = await get(
                    f"/instance/network-interfaces/{idx}/access-configs/0/external-ip"
                )
                if not public_ip:
                    public_ip = None
            except Exception:
                public_ip = None
            network_full = await get(f"/instance/network-interfaces/{idx}/network")
            network = network_full.split("/")[-1]
            network_interfaces.append({
                "private_ip": private_ip,
                "public_ip": public_ip,
                "network": network
            })

    return {
        "cloud_platform": "gcp",
        "instance_id": instance_id,
        "region": region,
        "machine_type": machine_type,
        "network_interfaces": network_interfaces
    }


async def _get_aws_metadata() -> dict:
    base = "http://169.254.169.254/latest/meta-data"
    timeout = httpx.Timeout(5.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        token_resp = await client.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"}
        )
        token_resp.raise_for_status()
        token = token_resp.text.strip()

        async def get(path):
            r = await client.get(
                f"{base}{path}",
                headers={"X-aws-ec2-metadata-token": token}
            )
            r.raise_for_status()
            return r.text.strip()

        instance_id = await get("/instance-id")
        az = await get("/placement/availability-zone")
        region = az[:-1]
        machine_type = await get("/instance-type")
        macs_raw = await get("/network/interfaces/macs/")
        macs = [m.strip().rstrip("/") for m in macs_raw.strip().splitlines() if m.strip()]

        network_interfaces = []
        for mac in macs:
            private_ip = await get(f"/network/interfaces/macs/{mac}/local-ipv4s")
            try:
                public_ip = await get(f"/network/interfaces/macs/{mac}/public-ipv4s")
                if not public_ip:
                    public_ip = None
            except Exception:
                public_ip = None
            vpc_id = await get(f"/network/interfaces/macs/{mac}/vpc-id")
            network_interfaces.append({
                "private_ip": private_ip,
                "public_ip": public_ip,
                "network": vpc_id
            })

    return {
        "cloud_platform": "aws",
        "instance_id": instance_id,
        "region": region,
        "machine_type": machine_type,
        "network_interfaces": network_interfaces
    }


@app.get("/v1/metadata", summary="Get cloud platform instance metadata")
async def get_metadata(request: Request):

    if request.query_params:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Bad Request",
                "message": "Query parameters are not allowed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": "/v1/metadata"
            },
            headers=CACHE_HEADERS
        )

    body = await request.body()
    if body:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Bad Request",
                "message": "Request body is not allowed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": "/v1/metadata"
            },
            headers=CACHE_HEADERS
        )

    if not _detected_platform:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "Service Unavailable",
                "message": "Unable to retrieve instance metadata. The application may not be running on a supported cloud platform.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": "/v1/metadata"
            },
            headers=CACHE_HEADERS
        )

    try:
        if _detected_platform == "gcp":
            data = await _get_gcp_metadata()
        else:
            data = await _get_aws_metadata()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=data,
            headers=CACHE_HEADERS
        )
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "Service Unavailable",
                "message": "Failed to retrieve metadata from cloud platform.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": "/v1/metadata"
            },
            headers=CACHE_HEADERS
        )


@app.api_route("/v1/metadata", methods=["POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
               summary="Metadata - method not allowed")
async def metadata_method_not_allowed():
    return Response(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        headers=CACHE_HEADERS
    )

# ==================== User Management ====================

@app.post('/v1/user', response_model=UserResponse,
          status_code=status.HTTP_201_CREATED,
          summary='Create a user account')
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
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    return new_user


@app.get("/v1/user/self", response_model=UserResponse, status_code=status.HTTP_200_OK,
         summary='Get user account information')
def get_user(current_user: User = Depends(get_current_user)):
    return current_user


@app.put("/v1/user/self", status_code=status.HTTP_204_NO_CONTENT,
         summary='Update user account information')
async def update_user(
    request: Request,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if request.headers.get("content-type", "").lower().split(";")[0].strip() != "application/json":
        raise HTTPException(status_code=415, detail="Unsupported Media Type. Content-Type must be application/json")

    raw = await safe_json(request)

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

    if user_update.first_name is not None:
        current_user.first_name = user_update.first_name
    if user_update.last_name is not None:
        current_user.last_name = user_update.last_name
    if user_update.password is not None:
        current_user.password = hash_password(user_update.password)

    db.commit()
    db.refresh(current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ==================== Root ====================

@app.get('/', summary='API Information')
def root():
    return {
        "message": "CSYE 6225 - Cloud Native Web Application API",
        "version": "1.0.0",
        "endpoints": {
            "health_check": "GET /healthz",
            "create_user": "POST /v1/user",
            "get_user": "GET /v1/user/self",
            "update_user": "PUT /v1/user/self",
            "metadata": "GET /v1/metadata",
            "api_docs": "/docs"
        }
    }


# ==================== Course Management ====================

IMMUTABLE_COURSE_FIELDS = {"id", "department_code", "number", "has_syllabus", "date_created", "date_updated"}


@app.get("/v1/courses", response_model=list[CourseResponse], status_code=status.HTTP_200_OK)
def list_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    courses = db.query(Course).order_by(Course.department_code, Course.number).all()
    return courses


@app.post("/v1/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    course: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing = db.query(Course).filter(
        Course.department_code == course.department_code,
        Course.number == course.number
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course {course.department_code} {course.number} already exists"
        )

    new_course = Course(
        department_code=course.department_code,
        number=course.number,
        title=course.title,
        credit_hours=course.credit_hours,
        classification=course.classification.value,
        description=course.description,
        prerequisites=course.prerequisites,
        has_syllabus=False
    )
    try:
        db.add(new_course)
        db.commit()
        db.refresh(new_course)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course {course.department_code} {course.number} already exists"
        )
    return new_course


@app.get("/v1/courses/{course_id}", response_model=CourseResponse, status_code=status.HTTP_200_OK)
def get_course(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


@app.put("/v1/courses/{course_id}", response_model=CourseResponse, status_code=status.HTTP_200_OK)
async def update_course(
    course_id: UUID,
    request: Request,
    course_update: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if request.headers.get("content-type", "").lower().split(";")[0].strip() != "application/json":
        raise HTTPException(status_code=415, detail="Unsupported Media Type. Content-Type must be application/json")

    # 先查课程是否存在
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # 再检查不可变字段
    raw = await safe_json(request)
    for field in IMMUTABLE_COURSE_FIELDS:
        if field in raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Field '{field}' cannot be updated"
            )

    update_data = course_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one updatable field must be provided"
        )

    for field, value in update_data.items():
        if field == "classification" and value is not None:
            setattr(course, field, value.value)
        else:
            setattr(course, field, value)

    db.commit()
    db.refresh(course)
    return course


@app.delete("/v1/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    has_syllabus = db.query(Syllabus).filter(Syllabus.course_id == course_id).first()
    if has_syllabus:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete course {course.department_code} {course.number} because it has a syllabus attached. Delete the syllabus first."
        )

    db.delete(course)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)







# ==================== Syllabus Management ====================

@app.post("/v1/courses/{course_id}/syllabus", response_model=SyllabusResponse, status_code=status.HTTP_201_CREATED)
async def upload_syllabus(
    course_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not S3_BUCKET_NAME:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="S3 bucket not configured")
    
    # 检查 Content-Type 必须是 multipart/form-data
    ct = (request.headers.get("content-type") or "").lower()
    if "multipart/form-data" not in ct:
        raise HTTPException(status_code=415, detail="Unsupported Media Type. Content-Type must be multipart/form-data")

    # 检查课程是否存在
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # 以 syllabi 表为准检查是否已有大纲
    existing = db.query(Syllabus).filter(Syllabus.course_id == course_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course {course.department_code} {course.number} already has a syllabus. Delete the existing syllabus first."
        )

    # 用 seek/tell 计算文件大小并检查空文件
    try:
            file.file.seek(0, os.SEEK_END)
            file_size = file.file.tell()
            file.file.seek(0)
            if file_size == 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")
    except HTTPException:
        raise
    except Exception:
        chunk = await file.read(1)
        if not chunk:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")
        try:
            file.file.seek(0)
        except Exception:
            pass
        file_size = 0

    # 清理文件名，防止路径注入
    safe_name = os.path.basename(file.filename or "upload")[:255]
    content_type = file.content_type or "application/octet-stream"

    # 构造唯一 S3 key
    file_uuid = str(uuid_lib.uuid4())
    s3_key = f"{course_id}/{file_uuid}/{safe_name}"

    # 上传到 S3
    s3 = get_s3_client()
    try:
        await asyncio.to_thread(
            s3.upload_fileobj,
            file.file,
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={"ContentType": content_type}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to upload file to S3: {str(e)}"
        )

    # 生成 presigned URL（bucket 是 private，需要签名才能访问）
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=3600
        )
    except Exception:
        url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

    # 保存元数据到数据库，失败时清理 S3
    syllabus = Syllabus(
        course_id=course_id,
        file_name=safe_name,
        s3_bucket_name=S3_BUCKET_NAME,
        s3_object_key=s3_key,
        content_type=content_type,
        file_size=file_size,
        url=url
    )
    try:
        db.add(syllabus)
        course.has_syllabus = True
        db.commit()
    except IntegrityError:
        db.rollback()
        try:
            await asyncio.to_thread(s3.delete_object, Bucket=S3_BUCKET_NAME, Key=s3_key)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Syllabus already exists for this course"
        )
    except Exception:
        db.rollback()
        try:
            await asyncio.to_thread(s3.delete_object, Bucket=S3_BUCKET_NAME, Key=s3_key)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save syllabus metadata"
        )

    db.refresh(syllabus)
    return syllabus


@app.get("/v1/courses/{course_id}/syllabus", response_model=SyllabusResponse, status_code=status.HTTP_200_OK)
def get_syllabus(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    syllabus = db.query(Syllabus).filter(Syllabus.course_id == course_id).first()
    if not syllabus:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No syllabus found for this course")

    return syllabus


@app.delete("/v1/courses/{course_id}/syllabus", status_code=status.HTTP_204_NO_CONTENT)
async def delete_syllabus(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not S3_BUCKET_NAME:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="S3 bucket not configured")

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    syllabus = db.query(Syllabus).filter(Syllabus.course_id == course_id).first()
    if not syllabus:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No syllabus found for this course")

    # 先删 S3，失败直接 503，不动 DB
    s3 = get_s3_client()
    try:
        await asyncio.to_thread(s3.delete_object, Bucket=S3_BUCKET_NAME, Key=syllabus.s3_object_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to delete file from S3: {str(e)}"
        )

    # 再删 DB
    try:
        db.delete(syllabus)
        course.has_syllabus = False
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete syllabus metadata"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
