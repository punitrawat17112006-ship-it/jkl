from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
from supabase import create_client, Client
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Supabase connection
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'photoevent-secret')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create the main app
app = FastAPI(title="PhotoEvent Pro API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============ MODELS ============

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class EventCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    date: Optional[str] = None

class EventResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    description: str
    date: str
    user_id: str
    photo_count: int
    qr_url: str
    created_at: str

class PhotoResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    event_id: str
    url: str
    filename: str
    created_at: str

# ============ HELPER FUNCTIONS ============

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============ AUTH ROUTES ============

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": hash_password(user_data.password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user)
    
    # Generate token
    token = create_access_token(user_id, user_data.email)
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=user_data.email,
            name=user_data.name,
            created_at=user["created_at"]
        )
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(user["id"], user["email"])
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            created_at=user["created_at"]
        )
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        created_at=current_user["created_at"]
    )

# ============ EVENT ROUTES ============

@api_router.post("/events", response_model=EventResponse)
async def create_event(event_data: EventCreate, current_user: dict = Depends(get_current_user)):
    event_id = str(uuid.uuid4())
    event_date = event_data.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Generate QR URL for customer page
    qr_url = f"/event/{event_id}"
    
    event = {
        "id": event_id,
        "name": event_data.name,
        "description": event_data.description or "",
        "date": event_date,
        "user_id": current_user["id"],
        "photo_count": 0,
        "qr_url": qr_url,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.events.insert_one(event)
    
    return EventResponse(**event)

@api_router.get("/events", response_model=List[EventResponse])
async def get_events(current_user: dict = Depends(get_current_user)):
    events = await db.events.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(100)
    return [EventResponse(**e) for e in events]

@api_router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, current_user: dict = Depends(get_current_user)):
    event = await db.events.find_one({"id": event_id, "user_id": current_user["id"]}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse(**event)

@api_router.delete("/events/{event_id}")
async def delete_event(event_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.events.delete_one({"id": event_id, "user_id": current_user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Delete associated photos from DB
    await db.photos.delete_many({"event_id": event_id})
    
    return {"message": "Event deleted successfully"}

# ============ PHOTO UPLOAD ROUTES ============

@api_router.post("/events/{event_id}/photos", response_model=List[PhotoResponse])
async def upload_photos(
    event_id: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    # Verify event exists and belongs to user
    event = await db.events.find_one({"id": event_id, "user_id": current_user["id"]}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    uploaded_photos = []
    
    for file in files:
        if not file.content_type.startswith("image/"):
            continue
        
        try:
            # Read file content
            content = await file.read()
            photo_id = str(uuid.uuid4())
            file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
            storage_path = f"{event_id}/{photo_id}.{file_ext}"
            
            # Upload to Supabase Storage
            result = supabase.storage.from_("event-photos").upload(
                path=storage_path,
                file=content,
                file_options={"content-type": file.content_type}
            )
            
            # Get public URL
            public_url = supabase.storage.from_("event-photos").get_public_url(storage_path)
            
            # Save to MongoDB
            photo = {
                "id": photo_id,
                "event_id": event_id,
                "url": public_url,
                "filename": file.filename,
                "storage_path": storage_path,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.photos.insert_one(photo)
            uploaded_photos.append(PhotoResponse(**photo))
            
        except Exception as e:
            logger.error(f"Error uploading {file.filename}: {str(e)}")
            continue
    
    # Update photo count
    if uploaded_photos:
        await db.events.update_one(
            {"id": event_id},
            {"$inc": {"photo_count": len(uploaded_photos)}}
        )
    
    return uploaded_photos

@api_router.get("/events/{event_id}/photos", response_model=List[PhotoResponse])
async def get_event_photos(event_id: str, current_user: dict = Depends(get_current_user)):
    event = await db.events.find_one({"id": event_id, "user_id": current_user["id"]}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    photos = await db.photos.find({"event_id": event_id}, {"_id": 0}).to_list(1000)
    return [PhotoResponse(**p) for p in photos]

# ============ PUBLIC EVENT ROUTE (for customers) ============

@api_router.get("/public/events/{event_id}")
async def get_public_event(event_id: str):
    event = await db.events.find_one({"id": event_id}, {"_id": 0, "user_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@api_router.get("/public/events/{event_id}/photos")
async def get_public_photos(event_id: str):
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    photos = await db.photos.find({"event_id": event_id}, {"_id": 0}).to_list(1000)
    return photos

# ============ HEALTH CHECK ============

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
