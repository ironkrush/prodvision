from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional, List, Dict, Tuple
from pydantic import BaseModel, EmailStr, Field
import os
from dotenv import load_dotenv
from transformers import pipeline
import asyncio
import httpx
import re
from bson import ObjectId
import json
import uvicorn
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import time

load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


RATE_LIMIT_DURATION = 60  
MAX_ATTEMPTS = 5  
login_attempts: Dict[str, Tuple[int, float]] = {}  

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handler for generic exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )

# Database connection with retry logic
async def connect_to_mongo():
    try:
        client = AsyncIOMotorClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=10
        )
        await client.admin.command('ping')
        return client
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        return None

# Initialize database connection
db = None

@app.on_event("startup")
async def startup_db_client():
    global db
    client = await connect_to_mongo()
    if client:
        db = client.videodb
        print("Connected to MongoDB")
    else:
        raise Exception("Failed to connect to MongoDB")

@app.on_event("shutdown")
async def shutdown_db_client():
    global db
    if db is not None:
        db.client.close()
        print("Closed MongoDB connection")
        db = None

# Security
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__default_rounds=12,
    bcrypt__min_rounds=8
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class User(BaseModel):
    email: str
    name: str
    hashed_password: str

class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=50)

class Video(BaseModel):
    id: str
    title: str
    thumbnail: str
    platform: str
    genre: str
    savedAt: datetime
    watchStatus: str
    userId: str

class PlaylistRequest(BaseModel):
    playlist_url: str

class InstagramRequest(BaseModel):
    url: str

# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_user(email: str):
    if (user := await db.users.find_one({"email": email})):
        return User(**user)

# Add this function for rate limiting
async def check_rate_limit(request: Request):
    client_ip = request.client.host
    current_time = time.time()
    
    if client_ip in login_attempts:
        attempts, first_attempt = login_attempts[client_ip]
        # Reset attempts if duration has passed
        if current_time - first_attempt > RATE_LIMIT_DURATION:
            login_attempts[client_ip] = (1, current_time)
        else:
            # Check if too many attempts
            if attempts >= MAX_ATTEMPTS:
                time_left = int(RATE_LIMIT_DURATION - (current_time - first_attempt))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many login attempts. Please try again in {time_left} seconds"
                )
            # Increment attempts
            login_attempts[client_ip] = (attempts + 1, first_attempt)
    else:
        # First attempt
        login_attempts[client_ip] = (1, current_time)

# Update the login endpoint
@app.post("/api/auth/login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        # Check rate limiting
        await check_rate_limit(request)
        
       
        email = form_data.username.lower().strip()
        
        
        user = await get_user(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not registered",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
   
        if not verify_password(form_data.password, user.hashed_password):
       
            client_ip = request.client.host
            current_attempts, first_attempt = login_attempts.get(client_ip, (0, time.time()))
            login_attempts[client_ip] = (current_attempts + 1, first_attempt)
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
       
        access_token = create_access_token(
            data={
                "sub": user.email,
                "name": user.name,
                "iat": datetime.utcnow(),
                "type": "access",
                "client_ip": request.client.host
            }
        )
        
       
        if request.client.host in login_attempts:
            del login_attempts[request.client.host]
        
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  
            "user": {
                "email": user.email,
                "name": user.name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
        "jti": f"{int(time.time())}_{os.urandom(8).hex()}"  
    })
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        print(f"Token creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create access token"
        )

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token_data = TokenData(email=email)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await get_user(token_data.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@app.post("/api/auth/register", response_model=dict)
async def register(user: UserCreate):
    try:
        
        if await db.users.find_one({"email": user.email.lower()}):
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
        
        
        if not any(char.isdigit() for char in user.password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one number"
            )
        if not any(char.isupper() for char in user.password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one uppercase letter"
            )
        
       
        user_dict = {
            "email": user.email.lower(),
            "name": user.name,
            "hashed_password": get_password_hash(user.password),
            "created_at": datetime.utcnow()
        }
        
        
        try:
            await db.users.insert_one(user_dict)
        except Exception as e:
            print(f"Database error during registration: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create user account"
            )
        
        return {
            "message": "User created successfully",
            "email": user.email.lower()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during registration"
        )

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

@app.get("/api/videos")
async def get_videos(current_user: User = Depends(get_current_user)):
    try:
        cursor = db.videos.find({"userId": current_user.email})
        videos = []
        async for video in cursor:
           
            video["_id"] = str(video["_id"])
            if isinstance(video.get("savedAt"), datetime):
                video["savedAt"] = video["savedAt"].isoformat()
            videos.append(video)
        return videos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch videos: {str(e)}")


classifier = pipeline("zero-shot-classification")


async def classify_video_genre(title: str, description: str = "") -> str:
    try:
       
        candidate_labels = [
            "Music and Entertainment",
            "Gaming and Esports",
            "Education and Learning",
            "Technology and Programming",
            "Lifestyle and Vlogs",
            "Sports and Fitness",
            "News and Politics",
            "Arts and Creativity",
            "Science and Nature",
            "Food and Cooking"
        ]
        
       
        text_to_classify = f"{title}. {description}"
        
        
        result = classifier(
            text_to_classify,
            candidate_labels,
            multi_label=False
        )
        
       
        genre_mapping = {
            "Music and Entertainment": "music",
            "Gaming and Esports": "gaming",
            "Education and Learning": "education",
            "Technology and Programming": "technology",
            "Lifestyle and Vlogs": "lifestyle",
            "Sports and Fitness": "sports",
            "News and Politics": "news",
            "Arts and Creativity": "arts",
            "Science and Nature": "science",
            "Food and Cooking": "food"
        }
        
        
        top_label = result["labels"][0]
        return genre_mapping.get(top_label, "other")
    except Exception as e:
        print(f"Genre classification error: {str(e)}")
        return "other"

@app.post("/api/videos/youtube")
async def add_youtube_playlist(request: PlaylistRequest, current_user: User = Depends(get_current_user)):
    try:
       
        if "list=" not in request.playlist_url:
            raise HTTPException(status_code=400, detail="Invalid YouTube playlist URL")
        
        playlist_id = request.playlist_url.split("list=")[-1].split("&")[0]
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/youtube/v3/playlistItems",
                params={
                    "part": "snippet",
                    "playlistId": playlist_id,
                    "maxResults": 50,
                    "key": YOUTUBE_API_KEY
                }
            )
            
            if response.status_code == 403:
                raise HTTPException(status_code=403, detail="YouTube API key is invalid or quota exceeded")
            elif response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch playlist. Please check the URL and try again.")
            
            data = response.json()
            if not data.get("items"):
                raise HTTPException(status_code=404, detail="No videos found in playlist")
            
            videos = []
            current_time = datetime.utcnow()
            
            for item in data["items"]:
                snippet = item["snippet"]
                video_id = snippet["resourceId"]["videoId"]
                title = snippet["title"]
                description = snippet.get("description", "")
                
               
                video_genre = await classify_video_genre(title, description)
                
                
                thumbnails = snippet["thumbnails"]
                thumbnail_url = (
                    thumbnails.get("maxres", {}).get("url") or
                    thumbnails.get("high", {}).get("url") or
                    thumbnails.get("medium", {}).get("url") or
                    thumbnails.get("default", {}).get("url")
                )
                
                video = {
                    "id": video_id,
                    "title": title,
                    "thumbnail": thumbnail_url,
                    "platform": "youtube",
                    "genre": video_genre,
                    "savedAt": current_time,
                    "watchStatus": "unwatched",
                    "userId": current_user.email,
                    "description": description
                }
                videos.append(video)
            
            if videos:
                
                result = await db.videos.insert_many(videos)
                
                
                return JSONEncoder().encode({
                    "message": f"Successfully added {len(videos)} videos from playlist",
                    "count": len(videos),
                    "videos": videos
                })
            else:
                raise HTTPException(status_code=404, detail="No valid videos found in playlist")
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/api/videos/instagram")
async def add_instagram_video(request: InstagramRequest, current_user: User = Depends(get_current_user)):
    try:
        
        if not re.match(r'https?://(?:www\.)?instagram\.com/(?:reel|p)/[a-zA-Z0-9_-]+/?.*', request.url):
            raise HTTPException(status_code=400, detail="Invalid Instagram URL")
            
       
        video_id = re.search(r'/(?:reel|p)/([a-zA-Z0-9_-]+)/?', request.url).group(1)
        
       
        INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        if not INSTAGRAM_ACCESS_TOKEN:
            raise HTTPException(
                status_code=501,
                detail="Instagram integration requires API setup. Please configure INSTAGRAM_ACCESS_TOKEN in .env"
            )
            
        async with httpx.AsyncClient() as client:
            
            response = await client.get(
                f"https://graph.instagram.com/v12.0/{video_id}",
                params={
                    "fields": "id,media_type,media_url,thumbnail_url,permalink,caption",
                    "access_token": INSTAGRAM_ACCESS_TOKEN
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to fetch Instagram video. Please check the URL and try again."
                )
                
            data = response.json()
            
           
            if data.get("media_type") not in ["VIDEO", "REELS"]:
                raise HTTPException(
                    status_code=400,
                    detail="URL must point to a video or reel"
                )
                
           
            caption = data.get("caption", "")
            video_genre = await classify_video_genre(caption)
            
            video = {
                "id": data["id"],
                "title": caption[:100] + "..." if len(caption) > 100 else caption,
                "thumbnail": data.get("thumbnail_url", ""),
                "platform": "instagram",
                "genre": video_genre,
                "savedAt": datetime.utcnow().isoformat(),
                "watchStatus": "unwatched",
                "userId": current_user.email,
                "description": caption,
                "originalUrl": data["permalink"]
            }
            
        
            await db.videos.insert_one(video)
            
            return {
                "message": "Successfully added Instagram video",
                "video": {
                    "id": video["id"],
                    "title": video["title"],
                    "platform": "instagram",
                    "genre": video["genre"]
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add Instagram video: {str(e)}"
        )

@app.put("/api/videos/{video_id}/watch-status")
async def update_watch_status(video_id: str, status: str, current_user: User = Depends(get_current_user)):
    if status not in ["watched", "unwatched"]:
        raise HTTPException(status_code=400, detail="Invalid watch status")
    
    result = await db.videos.update_one(
        {"id": video_id, "userId": current_user.email},
        {"$set": {"watchStatus": status}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return {"message": "Watch status updated"}

async def send_notification(user_email: str, video_title: str):
    # TODO: Implement notification system (email, push notifications, etc.)
    print(f"Sending notification to {user_email} about {video_title}")

async def check_unwatched_videos():
    while True:
        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        unwatched_videos = await db.videos.find({
            "watchStatus": "unwatched",
            "savedAt": {"$lte": two_weeks_ago}
        }).to_list(length=None)
        
        for video in unwatched_videos:
            await send_notification(video["userId"], video["title"])
        
        await asyncio.sleep(86400)  

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_unwatched_videos()) 