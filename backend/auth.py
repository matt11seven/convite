"""
Sistema de Autenticação JWT
Enterprise-grade authentication with password hashing, JWT tokens, and role-based access
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
import os
import uuid
from pymongo import MongoClient

# Environment variables
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'fallback-secret-key')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')

# Database setup
client = MongoClient(MONGO_URL)
db = client.convites_secure_db
users_collection = db.users
sessions_collection = db.sessions

# Security setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse

# Password utilities
def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

# JWT utilities
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a new JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

# User management
def create_user(user_data: UserCreate) -> Dict[str, Any]:
    """Create a new user."""
    # Check if user already exists
    existing_user = users_collection.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user document
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "password_hash": hash_password(user_data.password),
        "role": "user",  # Default role
        "is_active": True,
        "created_at": datetime.utcnow(),
        "last_login": None,
        "login_attempts": 0,
        "locked_until": None
    }
    
    # Insert user
    users_collection.insert_one(user_doc)
    
    # Return user without password
    user_doc.pop("password_hash", None)
    user_doc.pop("_id", None)
    return user_doc

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user with email and password."""
    user = users_collection.find_one({"email": email})
    
    if not user:
        return None
    
    # Check if account is locked
    if user.get("locked_until") and user["locked_until"] > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to too many failed attempts"
        )
    
    # Check if account is active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Verify password
    if not verify_password(password, user["password_hash"]):
        # Increment login attempts
        attempts = user.get("login_attempts", 0) + 1
        update_data = {"login_attempts": attempts}
        
        # Lock account after 5 failed attempts
        if attempts >= 5:
            update_data["locked_until"] = datetime.utcnow() + timedelta(hours=1)
        
        users_collection.update_one(
            {"_id": user["_id"]}, 
            {"$set": update_data}
        )
        return None
    
    # Successful login - reset attempts and update last login
    users_collection.update_one(
        {"_id": user["_id"]}, 
        {
            "$set": {
                "last_login": datetime.utcnow(),
                "login_attempts": 0
            },
            "$unset": {"locked_until": ""}
        }
    )
    
    # Remove sensitive data
    user.pop("password_hash", None)
    user.pop("_id", None)
    return user

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    user = users_collection.find_one({"id": user_id}, {"password_hash": 0, "_id": 0})
    return user

# Dependencies for FastAPI
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = verify_token(token)
        if payload is None:
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get current active user."""
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user

async def require_admin(current_user: Dict[str, Any] = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Require admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# Session management
def create_session(user_id: str, token: str, ip_address: str, user_agent: str) -> str:
    """Create a new session."""
    session_id = str(uuid.uuid4())
    session_doc = {
        "id": session_id,
        "user_id": user_id,
        "token": token,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "created_at": datetime.utcnow(),
        "last_activity": datetime.utcnow(),
        "is_active": True
    }
    
    sessions_collection.insert_one(session_doc)
    return session_id

def invalidate_session(session_id: str) -> bool:
    """Invalidate a session."""
    result = sessions_collection.update_one(
        {"id": session_id},
        {"$set": {"is_active": False, "invalidated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0

def cleanup_expired_sessions():
    """Clean up expired sessions."""
    expiry_time = datetime.utcnow() - timedelta(hours=JWT_EXPIRATION_HOURS)
    sessions_collection.delete_many({"created_at": {"$lt": expiry_time}})

# Initialize admin user
def init_admin_user():
    """Initialize admin user if not exists."""
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    # Verificar se as credenciais de admin estão configuradas
    if not admin_email or not admin_password:
        print("⚠️  WARNING: ADMIN_EMAIL and ADMIN_PASSWORD must be set in .env file")
        print("⚠️  Admin user will not be created automatically")
        return
    
    # Check if admin exists
    admin_user = users_collection.find_one({"email": admin_email})
    if not admin_user:
        admin_data = UserCreate(
            email=admin_email,
            password=admin_password,
            full_name="System Administrator"
        )
        
        try:
            user_doc = create_user(admin_data)
            # Update role to admin
            users_collection.update_one(
                {"id": user_doc["id"]},
                {"$set": {"role": "admin"}}
            )
            print(f"✅ Admin user created successfully: {admin_email}")
        except Exception as e:
            print(f"❌ Failed to create admin user: {e}")
    else:
        print(f"✅ Admin user already exists: {admin_email}")