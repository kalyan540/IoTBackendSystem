import paho.mqtt.client as mqtt
from pymongo import MongoClient
import json
import logging
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# MongoDB configuration
MONGO_URI = "mongodb://mongodb:27017"
DB_NAME = "mydatabase"
COLLECTION_NAME = "devices"

# MQTT configuration
BROKER = "mosquitto"
PORT = 1884
TOPIC = "devices/+/data"

# Define accepted keys
ACCEPTED_KEYS = {"value1", "value2", "value3", "data_timestamp"}

# Connect to MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
devices_collection = db[COLLECTION_NAME]

# ThreadPoolExecutor for handling high throughput
executor = ThreadPoolExecutor(max_workers=10)

# Function to process each message
def process_message(topic, payload):
    try:
        # Parse topic to extract device_id
        topic_parts = topic.split("/")
        device_id = topic_parts[1]  # Extract the wildcard (device_id)

        # Check if device_id exists in the devices collection
        device = devices_collection.find_one({"device_id": device_id})
        if not device:
            logging.warning(f"Device with device_id {device_id} not found in the database.")
            return  # If device does not exist, exit without updating

        # Parse and validate the message payload
        data = json.loads(payload)
        update_data = {key: data[key] for key in ACCEPTED_KEYS if key in data}

        if update_data:
            # Update the device document with valid keys
            result = devices_collection.update_one(
                {"device_id": device_id},
                {"$set": update_data}
            )

            if result.matched_count > 0:
                logging.info(f"Updated {device_id} with data: {update_data}")
            else:
                logging.warning(f"No matching device found for device_id {device_id}.")
        else:
            logging.warning(f"Message contains no valid keys for device_id {device_id}: {data}")
    except Exception as e:
        logging.error(f"Error processing message from topic {topic}: {e}")

# MQTT message callback
def on_message(client, userdata, msg):
    # Submit the message processing task to the executor
    executor.submit(process_message, msg.topic, msg.payload.decode("utf-8"))

# MQTT client setup
client = mqtt.Client()
client.on_message = on_message

# Connect to the MQTT broker
client.connect(BROKER, PORT, 60)

# Subscribe to the topic
client.subscribe(TOPIC)

# Start the MQTT client loop
logging.info(f"Listening for messages on topic: {TOPIC}")
client.loop_forever()
