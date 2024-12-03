from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from datetime import datetime
from pymongo import MongoClient
from jose import JWTError, jwt
from typing import Optional

# MongoDB setup
client = MongoClient("mongodb://mongodb:27017")
db = client["mydatabase"]
devices_collection = db["devices"]

# Application setup
app = FastAPI()

# Security configurations
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"

# Helper functions

def decode_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_device(device_id: str):
    return devices_collection.find_one({"device_id": device_id})

def get_devices_by_user(user_id: str):
    return list(devices_collection.find({"user_id": user_id}))

# API Endpoints

@app.get("/device/{device_id}/{value_type}")
async def get_device_value(device_id: str, value_type: str, authorization: str = Header(...)):
    """
    Endpoint to fetch a specific value from a device.
    :param device_id: The unique identifier of the device.
    :param value_type: The value to fetch (e.g., value1, value2, etc.).
    :param authorization: The Bearer token for authentication.
    """
    # Extract the token from the Authorization header
    token = authorization.split(" ")[1]  # "Bearer <token>"
    payload = decode_jwt_token(token)

    # Ensure the device exists
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Ensure the device belongs to the user
    if device["user_id"] != payload["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied for this device")

    # Validate the requested value_type (e.g., value1, value2)
    if value_type not in device:
        raise HTTPException(status_code=400, detail=f"Invalid value type '{value_type}' requested")

    # Return the requested value
    return {value_type: device[value_type],"timestamp":device["data_timestamp"]}

