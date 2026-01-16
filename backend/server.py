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
import imagehash
import io

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
SUPABASE_BUCKET = "event-photos"

UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

JWT_SECRET = os.environ.get('JWT_SECRET', 'photoevent-secret')
JWT_ALGORITHM = 'HS256'

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
app = FastAPI(title="PhotoEvent Pro")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ LIGHTWEIGHT IMAGE MATCHING ============
def get_image_hashes(image_bytes: bytes) -> dict:
    """Get multiple perceptual hashes for better matching"""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        # Resize for consistency
        img = img.resize((256, 256), Image.Resampling.LANCZOS)
        return {
            "phash": str(imagehash.phash(img, hash_size=16)),
            "dhash": str(imagehash.dhash(img, hash_size=16)),
            "average": str(imagehash.average_hash(img, hash_size=16))
        }
    except Exception as e:
        logger.error(f"Hash error: {e}")
        return {}

def compare_hashes(h1: dict, h2: dict) -> float:
    """Compare multiple hashes, return best similarity"""
    if not h1 or not h2:
        return 0
    try:
        scores = []
        for key in ["phash", "dhash", "average"]:
            if key in h1 and key in h2:
                hash1 = imagehash.hex_to_hash(h1[key])
                hash2 = imagehash.hex_to_hash(h2[key])
                dist = hash1 - hash2
                sim = max(0, 100 - (dist * 0.5))  # Adjusted scale
                scores.append(sim)
        return max(scores) if scores else 0
    except:
        return 0

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
def create_token(uid, email):
    return jwt.encode({"sub": uid, "email": email, "exp": datetime.now(timezone.utc) + timedelta(hours=24)}, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_user(cred: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(cred.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0})
        if not user: raise HTTPException(401, "Not found")
        return user
    except: raise HTTPException(401, "Invalid")

# ============ AUTH ============
@api_router.post("/auth/register", response_model=TokenResponse)
async def register(d: UserCreate):
    if await db.users.find_one({"email": d.email}): raise HTTPException(400, "Exists")
    uid = str(uuid.uuid4())
    u = {"id": uid, "email": d.email, "name": d.name, "password_hash": hash_password(d.password), "created_at": datetime.now(timezone.utc).isoformat()}
    await db.users.insert_one(u)
    return TokenResponse(access_token=create_token(uid, d.email), user=UserResponse(id=uid, email=d.email, name=d.name, created_at=u["created_at"]))

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(d: UserLogin):
    u = await db.users.find_one({"email": d.email}, {"_id": 0})
    if not u or not verify_password(d.password, u["password_hash"]): raise HTTPException(401, "Invalid")
    return TokenResponse(access_token=create_token(u["id"], u["email"]), user=UserResponse(id=u["id"], email=u["email"], name=u["name"], created_at=u["created_at"]))

@api_router.get("/auth/me", response_model=UserResponse)
async def me(u: dict = Depends(get_user)):
    return UserResponse(id=u["id"], email=u["email"], name=u["name"], created_at=u["created_at"])

# ============ EVENTS ============
@api_router.post("/events", response_model=EventResponse)
async def create_event(d: EventCreate, u: dict = Depends(get_user)):
    eid = str(uuid.uuid4())
    e = {"id": eid, "name": d.name, "description": d.description or "", "date": d.date or datetime.now(timezone.utc).strftime("%Y-%m-%d"), "user_id": u["id"], "photo_count": 0, "qr_url": f"/event/{eid}", "created_at": datetime.now(timezone.utc).isoformat()}
    await db.events.insert_one(e)
    (UPLOADS_DIR / eid).mkdir(exist_ok=True)
    return EventResponse(**e)

@api_router.get("/events", response_model=List[EventResponse])
async def list_events(u: dict = Depends(get_user)):
    return [EventResponse(**e) for e in await db.events.find({"user_id": u["id"]}, {"_id": 0}).to_list(100)]

@api_router.get("/events/{eid}", response_model=EventResponse)
async def get_event(eid: str, u: dict = Depends(get_user)):
    e = await db.events.find_one({"id": eid, "user_id": u["id"]}, {"_id": 0})
    if not e: raise HTTPException(404)
    return EventResponse(**e)

@api_router.delete("/events/{eid}")
async def del_event(eid: str, u: dict = Depends(get_user)):
    r = await db.events.delete_one({"id": eid, "user_id": u["id"]})
    if r.deleted_count == 0: raise HTTPException(404)
    await db.photos.delete_many({"event_id": eid})
    shutil.rmtree(UPLOADS_DIR / eid, ignore_errors=True)
    return {"ok": True}

# ============ PHOTOS ============
@api_router.post("/events/{eid}/photos", response_model=List[PhotoResponse])
async def upload(eid: str, files: List[UploadFile] = File(...), u: dict = Depends(get_user)):
    if not await db.events.find_one({"id": eid, "user_id": u["id"]}): raise HTTPException(404)
    folder = UPLOADS_DIR / eid
    folder.mkdir(exist_ok=True)
    uploaded = []
    for f in files:
        if not f.content_type or not f.content_type.startswith("image/"): continue
        try:
            content = await f.read()
            pid = str(uuid.uuid4())
            ext = f.filename.split(".")[-1] if "." in f.filename else "jpg"
            fn = f"{pid}.{ext}"
            hashes = get_image_hashes(content)
            async with aiofiles.open(folder / fn, 'wb') as out:
                await out.write(content)
            url = f"/api/uploads/{eid}/{fn}"
            photo = {"id": pid, "event_id": eid, "url": url, "filename": f.filename, "hashes": hashes, "created_at": datetime.now(timezone.utc).isoformat()}
            await db.photos.insert_one(photo)
            uploaded.append(PhotoResponse(**photo))
            logger.info(f"Uploaded {f.filename} with hashes")
        except Exception as e:
            logger.error(f"Error: {e}")
    if uploaded:
        await db.events.update_one({"id": eid}, {"$inc": {"photo_count": len(uploaded)}})
    return uploaded

@api_router.get("/events/{eid}/photos", response_model=List[PhotoResponse])
async def get_photos(eid: str, u: dict = Depends(get_user)):
    if not await db.events.find_one({"id": eid, "user_id": u["id"]}): raise HTTPException(404)
    return [PhotoResponse(**p) for p in await db.photos.find({"event_id": eid}, {"_id": 0}).to_list(1000)]

# ============ PUBLIC ============
@api_router.get("/public/events/{eid}")
async def pub_event(eid: str):
    e = await db.events.find_one({"id": eid}, {"_id": 0, "user_id": 0})
    if not e: raise HTTPException(404)
    return e

@api_router.get("/public/events/{eid}/photos")
async def pub_photos(eid: str):
    if not await db.events.find_one({"id": eid}): raise HTTPException(404)
    return await db.photos.find({"event_id": eid}, {"_id": 0}).to_list(1000)

# ============ FACE MATCHING ============
@api_router.post("/public/events/{eid}/find-my-photos", response_model=List[MatchedPhotoResponse])
async def find_photos(eid: str, selfie: UploadFile = File(...)):
    if not await db.events.find_one({"id": eid}): raise HTTPException(404)
    
    content = await selfie.read()
    selfie_hashes = get_image_hashes(content)
    if not selfie_hashes:
        raise HTTPException(400, "Could not process image")
    
    photos = await db.photos.find({"event_id": eid}, {"_id": 0}).to_list(1000)
    logger.info(f"COMPARING SELFIE AGAINST {len(photos)} PHOTOS")
    
    THRESHOLD = 60  # 60% match threshold
    matched = []
    all_scores = []
    
    for p in photos:
        h = p.get("hashes", {})
        if h:
            sim = compare_hashes(selfie_hashes, h)
            all_scores.append({"file": p["filename"], "score": sim})
            if sim >= THRESHOLD:
                matched.append(MatchedPhotoResponse(id=p["id"], event_id=p["event_id"], url=p["url"], filename=p["filename"], similarity=round(sim, 1), created_at=p["created_at"]))
    
    all_scores.sort(key=lambda x: x["score"], reverse=True)
    logger.info(f"TOP SCORES: {all_scores[:5]}")
    logger.info(f"MATCHES >= {THRESHOLD}%: {len(matched)}")
    
    matched.sort(key=lambda x: x.similarity, reverse=True)
    return matched

@api_router.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(api_router)
app.mount("/api/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("shutdown")
async def shutdown(): client.close()
