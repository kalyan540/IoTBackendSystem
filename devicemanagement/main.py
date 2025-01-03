from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from datetime import datetime, timezone
from pymongo import MongoClient
from jose import JWTError, jwt
from typing import List
import uuid
from cryptography.fernet import Fernet

# MongoDB setup
client = MongoClient("mongodb://mongodb:27017")
db = client["mydatabase"]
devices_collection = db["devices"]

# Application setup
app = FastAPI()

# Security configurations
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"

#Device Security configurations
ENCRYPTION_KEY = b'_T3L0eU8ovtJSZCMf7GxkXh1GP1ebNuLlHLcfM8vu4Q='
cipher = Fernet(ENCRYPTION_KEY)

# Models
class Device(BaseModel):
    device_id: str  # device_id passed from the device memory
    #device_name: str
    #device_type: str
    #status: str

class DeviceResponse(BaseModel):
    device_id: str
    device_name: str
    device_type: str
    status: str
    created_at: datetime

class User(BaseModel):
    user_id: str

# Helper functions

def get_device(device_id: str):
    return devices_collection.find_one({"device_id": device_id})

def get_devices_by_user(user_id: str):
    return list(devices_collection.find({"user_id": user_id}))

def decode_device_info(encoded_data: str) -> dict:
    """
    Decode the encoded string to retrieve the original device information.

    Parameters:
    - encoded_data (str): The encoded string to decode

    Returns:
    - dict: Contains the original manufacturer name, device type, secret key, and timestamp
    """
    try:
        # Decrypt the data
        decoded_data = cipher.decrypt(encoded_data.encode('utf-8')).decode('utf-8')
        # Split the data into components
        manufacturer_name, device_Name, device_type, timestamp = decoded_data.split(":")
        return {
            "manufacturer_name": manufacturer_name,
            "device_name": device_Name,
            "device_type": device_type,
            "timestamp": timestamp
        }
    except Exception as e:
        raise ValueError("Invalid encoded data or decryption failed.") from e

def create_device(user_id: str, device_id: str):
    # Ensure device ID is unique
    if get_device(device_id):
        raise HTTPException(status_code=400, detail="Device ID already exists")
    current_time = datetime.now(timezone.utc)
    decoded_info = decode_device_info(device_id)
    device = {
        "device_id": device_id,
        "user_id": user_id,
        "device_name": decoded_info["device_name"],
        "device_type": decoded_info["device_type"],
        "status": "connected",
        "created_at": current_time,
        "health_timestamp": current_time,
        "value1": 0,
        "value2": 0,
        "value3": 0,
        "battery_percentage": 100,
        "data_timestamp": current_time,
    }
    devices_collection.insert_one(device)
    return device

def remove_device(device_id: str):
    result = devices_collection.delete_one({"device_id": device_id})
    return result.deleted_count > 0

def decode_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# API Endpoints

@app.post("/add_device", response_model=DeviceResponse)
async def add_device(device: Device, authorization: str = Header(...)):
    # Extract the token from the Authorization header
    token = authorization.split(" ")[1]  # "Bearer <token>"
    payload = decode_jwt_token(token)

    # Ensure device ID is unique across all users
    if get_device(device.device_id):
        raise HTTPException(status_code=400, detail="Device ID already exists")

    # Assign device to user
    device_data = create_device(user_id=payload["user_id"], device_id=device.device_id)
    return device_data

@app.get("/devices", response_model=List[DeviceResponse])
async def get_devices(authorization: str = Header(...)):
    # Extract the token from the Authorization header
    token = authorization.split(" ")[1]  # "Bearer <token>"
    payload = decode_jwt_token(token)

    # Retrieve all devices associated with the user
    user_devices = get_devices_by_user(payload["user_id"])
    if not user_devices:
        raise HTTPException(status_code=404, detail="No devices found for this user")
    return user_devices

@app.get("/device/{device_id}", response_model=DeviceResponse)
async def get_device_by_id(device_id: str, authorization: str = Header(...)):
    # Extract the token from the Authorization header
    token = authorization.split(" ")[1]  # "Bearer <token>"
    payload = decode_jwt_token(token)
    
    # Retrieve a specific device by ID
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if device["user_id"] != payload["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied for this device")
    return device

@app.delete("/device/{device_id}", response_model=dict)
async def delete_device(device_id: str, authorization: str = Header(...)):
    # Extract the token from the Authorization header
    token = authorization.split(" ")[1]  # "Bearer <token>"
    payload = decode_jwt_token(token)

    # Ensure the device belongs to the current user
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if device["user_id"] != payload["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied for this device")
    
    # Remove the device
    success = remove_device(device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {"message": "Device successfully removed"}
