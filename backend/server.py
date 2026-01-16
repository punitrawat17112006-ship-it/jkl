from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
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
import shutil
import aiofiles
import httpx
from PIL import Image
import imagehash
import io

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Supabase config
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
SUPABASE_BUCKET = "event-photos"

# Local uploads directory (fallback)
UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'photoevent-secret')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create the main app
app = FastAPI(title="PhotoEvent Pro API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============ SUPABASE STORAGE HELPER ============

class SupabaseStorage:
    def __init__(self, url: str, key: str, bucket: str):
        self.url = url.rstrip('/')
        self.key = key
        self.bucket = bucket
        self.storage_url = f"{self.url}/storage/v1"
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        self._connected = None
    
    async def check_connection(self) -> bool:
        if self._connected is not None:
            return self._connected
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.storage_url}/bucket", headers=self.headers)
                self._connected = response.status_code in [200, 401, 403]
                logger.info(f"Supabase status: {response.status_code}, connected: {self._connected}")
                return self._connected
        except Exception as e:
            logger.warning(f"Supabase unreachable: {e}")
            self._connected = False
            return False
    
    async def upload_file(self, path: str, content: bytes, content_type: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.storage_url}/object/{self.bucket}/{path}",
                    headers={**self.headers, "Content-Type": content_type},
                    content=content
                )
                if response.status_code in [200, 201]:
                    return f"{self.url}/storage/v1/object/public/{self.bucket}/{path}"
                logger.error(f"Upload failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return None

supabase_storage = SupabaseStorage(SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET)

# ============ LIGHTWEIGHT FACE MATCHING ============

def compute_image_hash(image_bytes: bytes) -> str:
    """Compute perceptual hash for an image - lightweight alternative to face recognition"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert('RGB')
        # Use perceptual hash - very fast and lightweight
        phash = imagehash.phash(img, hash_size=16)
        return str(phash)
    except Exception as e:
        logger.error(f"Hash computation error: {e}")
        return ""

def compute_similarity(hash1: str, hash2: str) -> float:
    """Compare two image hashes - returns similarity score 0-100"""
    try:
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        # Hamming distance - lower is more similar
        distance = h1 - h2
        # Stricter calculation: max distance for 16-bit hash is 256
        # Use exponential decay for stricter matching
        similarity = max(0, 100 * (1 - (distance / 64)))  # Much stricter: 64 instead of 256
        return similarity if similarity >= 80 else 0  # Hard cutoff at 80%
    except:
        return 0

async def extract_face_region(image_bytes: bytes) -> bytes:
    """Extract center region of image (likely face area) - lightweight approach"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert('RGB')
        width, height = img.size
        
        # Crop center region (where face likely is in a selfie)
        center_x, center_y = width // 2, height // 2
        crop_size = min(width, height) // 2
        
        left = max(0, center_x - crop_size)
        top = max(0, center_y - crop_size)
        right = min(width, center_x + crop_size)
        bottom = min(height, center_y + crop_size)
        
        cropped = img.crop((left, top, right, bottom))
        cropped = cropped.resize((128, 128))  # Normalize size
        
        buffer = io.BytesIO()
        cropped.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"Face extraction error: {e}")
        return image_bytes

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

class MatchedPhotoResponse(BaseModel):
    id: str
    event_id: str
    url: str
    filename: str
    similarity: float
    created_at: str

# ============ HELPER FUNCTIONS ============

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": user_id, "email": email, "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============ AUTH ROUTES ============

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    if await db.users.find_one({"email": user_data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id, "email": user_data.email, "name": user_data.name,
        "password_hash": hash_password(user_data.password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user)
    return TokenResponse(
        access_token=create_access_token(user_id, user_data.email),
        user=UserResponse(id=user_id, email=user_data.email, name=user_data.name, created_at=user["created_at"])
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_access_token(user["id"], user["email"]),
        user=UserResponse(id=user["id"], email=user["email"], name=user["name"], created_at=user["created_at"])
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**{k: current_user[k] for k in ["id", "email", "name", "created_at"]})

# ============ EVENT ROUTES ============

@api_router.post("/events", response_model=EventResponse)
async def create_event(event_data: EventCreate, current_user: dict = Depends(get_current_user)):
    event_id = str(uuid.uuid4())
    event = {
        "id": event_id, "name": event_data.name,
        "description": event_data.description or "",
        "date": event_data.date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "user_id": current_user["id"], "photo_count": 0,
        "qr_url": f"/event/{event_id}",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.events.insert_one(event)
    (UPLOADS_DIR / event_id).mkdir(exist_ok=True)
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
    await db.photos.delete_many({"event_id": event_id})
    shutil.rmtree(UPLOADS_DIR / event_id, ignore_errors=True)
    return {"message": "Event deleted"}

# ============ PHOTO UPLOAD ROUTES ============

@api_router.post("/events/{event_id}/photos", response_model=List[PhotoResponse])
async def upload_photos(event_id: str, files: List[UploadFile] = File(...), current_user: dict = Depends(get_current_user)):
    event = await db.events.find_one({"id": event_id, "user_id": current_user["id"]}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    use_supabase = await supabase_storage.check_connection()
    event_folder = UPLOADS_DIR / event_id
    event_folder.mkdir(exist_ok=True)
    
    uploaded_photos = []
    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            continue
        try:
            content = await file.read()
            photo_id = str(uuid.uuid4())
            file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
            safe_filename = f"{photo_id}.{file_ext}"
            storage_path = f"{event_id}/{safe_filename}"
            
            # Compute image hash for face matching
            img_hash = compute_image_hash(content)
            
            public_url = None
            if use_supabase:
                public_url = await supabase_storage.upload_file(storage_path, content, file.content_type)
            
            if not public_url:
                async with aiofiles.open(event_folder / safe_filename, 'wb') as f:
                    await f.write(content)
                public_url = f"/api/uploads/{event_id}/{safe_filename}"
            
            photo = {
                "id": photo_id, "event_id": event_id, "url": public_url,
                "filename": file.filename, "storage_path": storage_path,
                "image_hash": img_hash,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.photos.insert_one(photo)
            uploaded_photos.append(PhotoResponse(**photo))
        except Exception as e:
            logger.error(f"Upload error for {file.filename}: {e}")
    
    if uploaded_photos:
        await db.events.update_one({"id": event_id}, {"$inc": {"photo_count": len(uploaded_photos)}})
    
    return uploaded_photos

@api_router.get("/events/{event_id}/photos", response_model=List[PhotoResponse])
async def get_event_photos(event_id: str, current_user: dict = Depends(get_current_user)):
    event = await db.events.find_one({"id": event_id, "user_id": current_user["id"]}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    photos = await db.photos.find({"event_id": event_id}, {"_id": 0}).to_list(1000)
    return [PhotoResponse(**p) for p in photos]

# ============ PUBLIC EVENT ROUTES ============

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

# ============ SELFIE FACE MATCHING (Customer Feature) ============

@api_router.post("/public/events/{event_id}/find-my-photos", response_model=List[MatchedPhotoResponse])
async def find_my_photos(event_id: str, selfie: UploadFile = File(...)):
    """Customer uploads selfie to find their photos using lightweight image matching"""
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Read and process selfie
    selfie_content = await selfie.read()
    
    # Extract face region from selfie
    face_region = await extract_face_region(selfie_content)
    selfie_hash = compute_image_hash(face_region)
    
    if not selfie_hash:
        raise HTTPException(status_code=400, detail="Could not process selfie image")
    
    # Get all photos for this event
    photos = await db.photos.find({"event_id": event_id}, {"_id": 0}).to_list(1000)
    
    matched_photos = []
    STRICT_THRESHOLD = 80  # Only show 80%+ matches
    
    for photo in photos:
        photo_hash = photo.get("image_hash", "")
        if photo_hash:
            similarity = compute_similarity(selfie_hash, photo_hash)
            # STRICT: Only include photos with 80%+ similarity
            if similarity >= STRICT_THRESHOLD:
                matched_photos.append(MatchedPhotoResponse(
                    id=photo["id"],
                    event_id=photo["event_id"],
                    url=photo["url"],
                    filename=photo["filename"],
                    similarity=round(similarity, 1),
                    created_at=photo["created_at"]
                ))
    
    # Sort by similarity (highest first)
    matched_photos.sort(key=lambda x: x.similarity, reverse=True)
    
    logger.info(f"Found {len(matched_photos)} matching photos for selfie in event {event_id}")
    
    return matched_photos

# ============ STORAGE STATUS ============

@api_router.get("/storage/status")
async def storage_status():
    supabase_ok = await supabase_storage.check_connection()
    return {
        "supabase_connected": supabase_ok,
        "supabase_url": SUPABASE_URL,
        "bucket": SUPABASE_BUCKET,
        "mode": "cloud" if supabase_ok else "local"
    }

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include router and static files
app.include_router(api_router)
app.mount("/api/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

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
