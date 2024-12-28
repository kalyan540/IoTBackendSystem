from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import uuid
from pymongo import MongoClient
from fastapi.security import OAuth2PasswordBearer

# MongoDB setup
client = MongoClient("mongodb://mongodb:27017")
db = client["mydatabase"]
users_collection = db["users"]

# Security configurations
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="signin")

# Models
class User(BaseModel):
    username: str
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: str | None = None

# Helper functions
def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(days=1)
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user(email: str):
    return users_collection.find_one({"email": email})

def create_user(username: str, email: str, hashed_password: str):
    user_id = str(uuid.uuid4())  # Generate unique ID
    users_collection.insert_one({
        "user_id": user_id,
        "username": username,
        "email": email,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow()
    })
    return user_id

# API Endpoints
@app.post("/signup", response_model=dict)
async def signup(user: User):
    if get_user(user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    user_id = create_user(user.username, user.email, hashed_password)
    return {"user_id": user_id, "message": "User created successfully"}

@app.post("/signin", response_model=Token)
async def signin(user: User):
    db_user = get_user(user.email)
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    access_token = create_access_token(data={"user_id": db_user["user_id"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=dict)
async def get_me(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = users_collection.find_one({"user_id": user_id})
        return {"user_id": user["user_id"], "username": user["username"], "email": user["email"]}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
