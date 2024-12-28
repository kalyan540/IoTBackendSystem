from flask import Flask, request, jsonify
from flask import send_from_directory
from jose import jwt, JWTError
from cryptography.fernet import Fernet
import os
import datetime

# Flask app setup
app = Flask(__name__)

# Hardcoded secrets
SECRET_KEY = "your_jwt_secret_key"  # Replace with your secure JWT secret
ALGORITHM = "HS256"  # Algorithm for JWT decoding
FERNET_KEY = b'_T3L0eU8ovtJSZCMf7GxkXh1GP1ebNuLlHLcfM8vu4Q='  # Replace with your Fernet encryption key
cipher = Fernet(FERNET_KEY)

OTA_DIR = "/app/OTA"  # Path to the OTA directory
BASE_URL = "https://ota.eknow.in"  # Base URL for OTA file hosting


def decode_jwt_token(token: str):
    """
    Decode and validate a JWT token.

    Parameters:
    - token (str): JWT token to decode

    Returns:
    - dict: Decoded payload from the token
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise ValueError("Invalid token")


def decode_device_info(encoded_data: str) -> dict:
    """
    Decode the encrypted device information.

    Parameters:
    - encoded_data (str): Encrypted string to decode

    Returns:
    - dict: Contains manufacturer name, device name, device type, and timestamp
    """
    try:
        decoded_data = cipher.decrypt(encoded_data.encode('utf-8')).decode('utf-8')
        manufacturer_name, device_name, device_type, timestamp = decoded_data.split(":")
        return {
            "manufacturer_name": manufacturer_name,
            "device_name": device_name,
            "device_type": device_type,
            "timestamp": timestamp
        }
    except Exception as e:
        raise ValueError("Invalid encoded data or decryption failed.") from e


def generate_signed_url(filename: str, expiry_minutes: int = 10) -> str:
    """
    Generate a signed URL for secure file access.

    Parameters:
    - filename (str): The name of the file
    - expiry_minutes (int): Expiry time in minutes

    Returns:
    - str: Signed URL
    """
    expiry_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=expiry_minutes)
    payload = {
        "file": filename,
        "exp": expiry_time
    }
    signed_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return f"{BASE_URL}/{signed_token}/{filename}"


@app.route("/<token>/<filename>", methods=["GET"])
def serve_file(token, filename):
    """
    Serve the requested file after validating the signed URL token.

    Parameters:
    - token (str): The signed token from the URL
    - filename (str): The name of the requested file

    Returns:
    - File: The requested file if the token is valid
    """
    try:
        # Decode and validate the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Check if the filename in the token matches the requested file
        if payload.get("file") != filename:
            return jsonify({"error": "Invalid token or file mismatch"}), 403

        # Check if the file exists in the OTA directory
        file_path = os.path.join(OTA_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404

        # Serve the file
        return send_from_directory(OTA_DIR, filename, as_attachment=True)

    except JWTError as e:
        return jsonify({"error": "Invalid or expired token"}), 401
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500


@app.route("/get-ota-files", methods=["POST"])
def get_ota_files():
    try:
        # Validate and decode JWT token
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return jsonify({"error": "Authorization token is required"}), 401
        token = token.split(" ")[1]

        try:
            decode_jwt_token(token)
        except ValueError as e:
            return jsonify({"error": str(e)}), 401

        # Decode the encrypted device ID
        data = request.json
        encrypted_device_id = data.get("deviceID")
        if not encrypted_device_id:
            return jsonify({"error": "Device ID is required"}), 400

        try:
            device_info = decode_device_info(encrypted_device_id)
            device_name = device_info["device_name"]
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # Build folder path
        folder_path = os.path.join(OTA_DIR, device_name)
        if not os.path.exists(folder_path):
            return jsonify({"error": f"No OTA files available for device {device_name}"}), 404

        # Get files in the folder
        files = os.listdir(folder_path)
        file_links = [generate_signed_url(file) for file in files]

        return jsonify({"device": device_name, "ota_files": file_links})

    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500


if __name__ == "__main__":
    # Ensure OTA directory exists
    if not os.path.exists(OTA_DIR):
        os.makedirs(OTA_DIR)

    app.run(host="0.0.0.0", port=5004)
