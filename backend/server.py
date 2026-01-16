from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
import shutil
import aiofiles
import httpx
from PIL import Image
import io
import numpy as np

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
SUPABASE_BUCKET = "event-photos"

# Local fallback
UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# JWT
JWT_SECRET = os.environ.get('JWT_SECRET', 'photoevent-secret')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
app = FastAPI(title="PhotoEvent Pro API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============ FACE EMBEDDING (DeepFace - no dlib) ============
try:
    from deepface import DeepFace
    FACE_MODEL_LOADED = True
    logger.info("DeepFace loaded successfully")
except Exception as e:
    FACE_MODEL_LOADED = False
    logger.warning(f"DeepFace not available: {e}")

def get_face_embedding(image_bytes: bytes) -> Optional[List[float]]:
    """Extract 128-d face embedding using DeepFace (Facenet model)"""
    if not FACE_MODEL_LOADED:
        return None
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        img_array = np.array(img)
        
        # Get embedding using Facenet (128-d vector)
        result = DeepFace.represent(
            img_array, 
            model_name="Facenet",
            enforce_detection=False,
            detector_backend="opencv"
        )
        
        if result and len(result) > 0:
            embedding = result[0].get("embedding", [])
            logger.info(f"Face embedding extracted: {len(embedding)} dimensions")
            return embedding
        return None
    except Exception as e:
        logger.error(f"Embedding extraction failed: {e}")
        return None

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    try:
        a = np.array(vec1)
        b = np.array(vec2)
        similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        return float(similarity)
    except:
        return 0.0

def embedding_distance(vec1: List[float], vec2: List[float]) -> float:
    """Calculate Euclidean distance (lower = more similar)"""
    try:
        return float(np.linalg.norm(np.array(vec1) - np.array(vec2)))
    except:
        return 999.0

# ============ SUPABASE STORAGE ============
class SupabaseStorage:
    def __init__(self, url: str, key: str, bucket: str):
        self.url = url.rstrip('/')
        self.key = key
        self.bucket = bucket
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    
    async def upload_file(self, path: str, content: bytes, content_type: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.url}/storage/v1/object/{self.bucket}/{path}",
                    headers={**self.headers, "Content-Type": content_type},
                    content=content
                )
                if response.status_code in [200, 201]:
                    return f"{self.url}/storage/v1/object/public/{self.bucket}/{path}"
        except Exception as e:
            logger.error(f"Upload error: {e}")
        return None

supabase_storage = SupabaseStorage(SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET)

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

# ============ HELPERS ============
def hash_password(p): return pwd_context.hash(p)
def verify_password(p, h): return pwd_context.verify(p, h)
def create_access_token(uid, email):
    return jwt.encode({"sub": uid, "email": email, "exp": datetime.now(timezone.utc) + timedelta(hours=24)}, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0})
        if not user: raise HTTPException(401, "User not found")
        return user
    except jwt.ExpiredSignatureError: raise HTTPException(401, "Token expired")
    except jwt.JWTError: raise HTTPException(401, "Invalid token")

# ============ AUTH ============
@api_router.post("/auth/register", response_model=TokenResponse)
async def register(data: UserCreate):
    if await db.users.find_one({"email": data.email}): raise HTTPException(400, "Email exists")
    uid = str(uuid.uuid4())
    user = {"id": uid, "email": data.email, "name": data.name, "password_hash": hash_password(data.password), "created_at": datetime.now(timezone.utc).isoformat()}
    await db.users.insert_one(user)
    return TokenResponse(access_token=create_access_token(uid, data.email), user=UserResponse(**{k: user[k] for k in ["id","email","name","created_at"]}))

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user or not verify_password(data.password, user["password_hash"]): raise HTTPException(401, "Invalid credentials")
    return TokenResponse(access_token=create_access_token(user["id"], user["email"]), user=UserResponse(**{k: user[k] for k in ["id","email","name","created_at"]}))

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(u: dict = Depends(get_current_user)):
    return UserResponse(**{k: u[k] for k in ["id","email","name","created_at"]})

# ============ EVENTS ============
@api_router.post("/events", response_model=EventResponse)
async def create_event(data: EventCreate, u: dict = Depends(get_current_user)):
    eid = str(uuid.uuid4())
    event = {"id": eid, "name": data.name, "description": data.description or "", "date": data.date or datetime.now(timezone.utc).strftime("%Y-%m-%d"), "user_id": u["id"], "photo_count": 0, "qr_url": f"/event/{eid}", "created_at": datetime.now(timezone.utc).isoformat()}
    await db.events.insert_one(event)
    (UPLOADS_DIR / eid).mkdir(exist_ok=True)
    return EventResponse(**event)

@api_router.get("/events", response_model=List[EventResponse])
async def get_events(u: dict = Depends(get_current_user)):
    return [EventResponse(**e) for e in await db.events.find({"user_id": u["id"]}, {"_id": 0}).to_list(100)]

@api_router.get("/events/{eid}", response_model=EventResponse)
async def get_event(eid: str, u: dict = Depends(get_current_user)):
    e = await db.events.find_one({"id": eid, "user_id": u["id"]}, {"_id": 0})
    if not e: raise HTTPException(404, "Event not found")
    return EventResponse(**e)

@api_router.delete("/events/{eid}")
async def delete_event(eid: str, u: dict = Depends(get_current_user)):
    r = await db.events.delete_one({"id": eid, "user_id": u["id"]})
    if r.deleted_count == 0: raise HTTPException(404, "Event not found")
    await db.photos.delete_many({"event_id": eid})
    shutil.rmtree(UPLOADS_DIR / eid, ignore_errors=True)
    return {"message": "Deleted"}

# ============ PHOTO UPLOAD ============
@api_router.post("/events/{eid}/photos", response_model=List[PhotoResponse])
async def upload_photos(eid: str, files: List[UploadFile] = File(...), u: dict = Depends(get_current_user)):
    event = await db.events.find_one({"id": eid, "user_id": u["id"]}, {"_id": 0})
    if not event: raise HTTPException(404, "Event not found")
    
    folder = UPLOADS_DIR / eid
    folder.mkdir(exist_ok=True)
    uploaded = []
    
    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"): continue
        try:
            content = await file.read()
            pid = str(uuid.uuid4())
            ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
            fname = f"{pid}.{ext}"
            
            # Extract face embedding
            embedding = get_face_embedding(content)
            faces_detected = 1 if embedding else 0
            logger.info(f"Photo {file.filename}: {faces_detected} face(s) detected")
            
            # Save locally
            async with aiofiles.open(folder / fname, 'wb') as f:
                await f.write(content)
            url = f"/api/uploads/{eid}/{fname}"
            
            # Try Supabase
            cloud_url = await supabase_storage.upload_file(f"{eid}/{fname}", content, file.content_type)
            if cloud_url: url = cloud_url
            
            photo = {"id": pid, "event_id": eid, "url": url, "filename": file.filename, "face_embedding": embedding, "created_at": datetime.now(timezone.utc).isoformat()}
            await db.photos.insert_one(photo)
            uploaded.append(PhotoResponse(**photo))
        except Exception as e:
            logger.error(f"Upload error {file.filename}: {e}")
    
    if uploaded:
        await db.events.update_one({"id": eid}, {"$inc": {"photo_count": len(uploaded)}})
    return uploaded

@api_router.get("/events/{eid}/photos", response_model=List[PhotoResponse])
async def get_event_photos(eid: str, u: dict = Depends(get_current_user)):
    if not await db.events.find_one({"id": eid, "user_id": u["id"]}): raise HTTPException(404, "Event not found")
    return [PhotoResponse(**p) for p in await db.photos.find({"event_id": eid}, {"_id": 0}).to_list(1000)]

# ============ PUBLIC ============
@api_router.get("/public/events/{eid}")
async def get_public_event(eid: str):
    e = await db.events.find_one({"id": eid}, {"_id": 0, "user_id": 0})
    if not e: raise HTTPException(404, "Event not found")
    return e

@api_router.get("/public/events/{eid}/photos")
async def get_public_photos(eid: str):
    if not await db.events.find_one({"id": eid}): raise HTTPException(404, "Event not found")
    return await db.photos.find({"event_id": eid}, {"_id": 0}).to_list(1000)

# ============ FACE MATCHING ============
@api_router.post("/public/events/{eid}/find-my-photos", response_model=List[MatchedPhotoResponse])
async def find_my_photos(eid: str, selfie: UploadFile = File(...)):
    """Vector embedding face matching with cosine similarity"""
    if not await db.events.find_one({"id": eid}): raise HTTPException(404, "Event not found")
    
    # Get selfie embedding
    selfie_bytes = await selfie.read()
    selfie_embedding = get_face_embedding(selfie_bytes)
    
    if not selfie_embedding:
        logger.warning("NO FACE DETECTED IN SELFIE")
        raise HTTPException(400, "No face detected in selfie. Please try again with a clearer photo.")
    
    logger.info(f"Selfie embedding: {len(selfie_embedding)} dimensions")
    
    # Get all photos with embeddings
    photos = await db.photos.find({"event_id": eid}, {"_id": 0}).to_list(1000)
    logger.info(f"TOTAL PHOTOS IN EVENT: {len(photos)}")
    
    photos_with_faces = [p for p in photos if p.get("face_embedding")]
    logger.info(f"PHOTOS WITH FACE EMBEDDINGS: {len(photos_with_faces)}")
    
    matched = []
    DISTANCE_THRESHOLD = 0.6  # Match if distance < 0.6
    
    for photo in photos_with_faces:
        emb = photo["face_embedding"]
        distance = embedding_distance(selfie_embedding, emb)
        similarity = max(0, (1 - distance) * 100)  # Convert to percentage
        
        logger.info(f"Photo {photo['filename']}: distance={distance:.3f}, similarity={similarity:.1f}%")
        
        if distance < DISTANCE_THRESHOLD:
            matched.append(MatchedPhotoResponse(
                id=photo["id"], event_id=photo["event_id"], url=photo["url"],
                filename=photo["filename"], similarity=round(similarity, 1),
                created_at=photo["created_at"]
            ))
    
    matched.sort(key=lambda x: x.similarity, reverse=True)
    logger.info(f"MATCHES FOUND: {len(matched)} (threshold: distance < {DISTANCE_THRESHOLD})")
    
    return matched

@api_router.get("/health")
async def health(): return {"status": "ok", "face_model": FACE_MODEL_LOADED}

app.include_router(api_router)
app.mount("/api/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("shutdown")
async def shutdown(): client.close()
