import paho.mqtt.client as mqtt
import pymongo
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger()

# MongoDB connection
mongoclient = pymongo.MongoClient("mongodb://mongodb:27017")
db = mongoclient["mydatabase"]
devices_collection = db["devices"]

# MQTT broker connection
mqtt_broker = 'mosquitto'
mqtt_port = 1884
mqtt_topic = 'device/health'

# Callback for connection
def on_connect(client, userdata, flags, rc):
    logger.info(f"Connection Result Code: {rc}")
    if rc == 0:
        logger.info("Connected to MQTT broker!")
        client.subscribe(mqtt_topic)
        logger.info(f"Subscribed to topic: {mqtt_topic}")
    else:
        logger.error(f"Failed to connect, return code {rc}")

# Callback for messages
def on_message(client, userdata, msg):
    logger.info(f"Message received on topic {msg.topic}: {msg.payload.decode()}")
    try:
        data = json.loads(msg.payload.decode())
        device_id = data.get('device_id')
        status = data.get('status')
        health_timestamp = data.get('health_timestamp')
        battery_percentage = data.get('battery_percentage')

        if not device_id:
            logger.warning("Message does not contain a device_id. Skipping.")
            return

        # Check if the device_id exists in the collection
        existing_device = devices_collection.find_one({'device_id': device_id})
        if not existing_device:
            logger.warning(f"Device {device_id} does not exist in the database. Skipping update.")
            return

        # Update MongoDB for existing devices
        devices_collection.update_one(
            {'device_id': device_id},
            {
                '$set': {
                    'status': status,
                    'health_timestamp': health_timestamp,
                    'battery_percentage': battery_percentage,
                }
            }
        )
        logger.info(f"Device {device_id} updated successfully.")
    except Exception as e:
        logger.error(f"Error processing message: {e}")

# Setup MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect
client.on_message = on_message

try:
    logger.info(f"Connecting to broker {mqtt_broker}:{mqtt_port}")
    client.connect(mqtt_broker, mqtt_port, 60)
except Exception as e:
    logger.error(f"Error connecting to broker: {e}")
    exit(1)

client.loop_forever()
