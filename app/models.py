from sqlalchemy import Column, String, DateTime, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID  
from app.database import Base  
import uuid 
from datetime import datetime  


from datetime import datetime, timezone

class User(Base):

    __tablename__ = "users"
    
    id = Column(
        UUID(as_uuid=True),  
        primary_key=True,    
        default=uuid.uuid4,   
        nullable=False        
    )
    
    username = Column(
        String(255),      
        unique=True,      
        nullable=False,   
        index=True        
    )
    
    password = Column(
        String(255),      
        nullable=False    
    )
    
    first_name = Column(
        String(100),      
        nullable=False    
    )
    
    last_name = Column(
        String(100),      
        nullable=False    
    )
    
    # store timestamps in UTC for consistency 
    # created once, updated time changes when updated 
    account_created = Column(
        DateTime(timezone=True),                    
        default=lambda: datetime.now(timezone.utc),    
        nullable=False               
    )
    
    account_updated = Column(
        DateTime(timezone=True),                    
        default=lambda: datetime.now(timezone.utc),     
        onupdate=lambda: datetime.now(timezone.utc),    
        nullable=False               
    )
    
    def __repr__(self):

        return f"<User(username='{self.username}', first_name='{self.first_name}')>"


class HealthCheck(Base):

    __tablename__ = "health_checks"
    
    check_id = Column(
        BigInteger,       
        primary_key=True, 
        autoincrement=True 
    )
    
    check_datetime = Column(
        DateTime(timezone=True),                 
        default=lambda: datetime.now(timezone.utc),  
        nullable=False,         
        index=True               
    )
    
    def __repr__(self):

        return f"<HealthCheck(check_id={self.check_id}, check_datetime='{self.check_datetime}')>"