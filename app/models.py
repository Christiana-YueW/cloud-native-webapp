from sqlalchemy import Column, String, DateTime, Integer, BigInteger, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID  
from sqlalchemy.orm import relationship
from app.database import Base  
import uuid 
from datetime import datetime, timezone


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    account_created = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    account_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User(username='{self.username}', first_name='{self.first_name}')>"


class HealthCheck(Base):
    __tablename__ = "health_checks"
    
    check_id = Column(BigInteger, primary_key=True, autoincrement=True)
    check_datetime = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    def __repr__(self):
        return f"<HealthCheck(check_id={self.check_id})>"


class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    department_code = Column(String(6), nullable=False)
    number = Column(String(6), nullable=False)
    title = Column(String(255), nullable=False)
    credit_hours = Column(Integer, nullable=False)
    classification = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    prerequisites = Column(String(512), nullable=True)
    has_syllabus = Column(Boolean, default=False, nullable=False)
    date_created = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    date_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    syllabus = relationship("Syllabus", back_populates="course", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('department_code', 'number', name='uq_course_dept_number'),
    )

    def __repr__(self):
        return f"<Course({self.department_code} {self.number}: {self.title})>"


class Syllabus(Base):
    __tablename__ = "syllabi"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, unique=True)
    file_name = Column(String(255), nullable=False)
    s3_bucket_name = Column(String(255), nullable=False)
    s3_object_key = Column(String(1024), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    url = Column(String(2048), nullable=False)
    date_created = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    date_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    course = relationship("Course", back_populates="syllabus")

    def __repr__(self):
        return f"<Syllabus(course_id={self.course_id}, file={self.file_name})>"