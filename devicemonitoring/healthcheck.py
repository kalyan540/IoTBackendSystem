import pymongo
import os
import logging
from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timedelta

# Set up logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Celery setup
app = Celery('healthcheck', broker=os.getenv('CELERY_BROKER'))
app.conf.timezone = 'UTC'

# Configure Celery Beat schedule (run every minute)
app.conf.beat_schedule = {
    'check-device-health-every-minute': {
        'task': 'healthcheck.check_device_health',  # Task name
        'schedule': crontab(minute='*/1'),  # Run every minute
    },
}

# MongoDB connection setup
client = pymongo.MongoClient("mongodb://mongodb:27017")
db = client["mydatabase"]
devices_collection = db["devices"]


# Health check task (runs every minute)
@app.task
def check_device_health():
    # Get the current time
    logger.info("Checking device health...")
    current_time = datetime.utcnow()

    # Find devices that are connected
    devices = list(devices_collection.find({'status': 'connected'}))
    logger.info(devices)
    

    if not devices:
        logger.warning("No connected devices found.")
        return

    for device in devices:
        health_timestamp = device.get('health_timestamp')
        if health_timestamp:
            health_timestamp = datetime.strptime(health_timestamp, '%Y-%m-%dT%H:%M:%S')

            # Mark as disconnected if health timestamp is older than 30 seconds
            if current_time - health_timestamp > timedelta(seconds=30):
                devices_collection.update_one(
                    {'device_id': device['device_id']},
                    {'$set': {'status': 'disconnected'}}
                )
                logger.info(f"Device {device['device_id']} marked as disconnected.")
        else:
            logger.warning(f"Device {device['device_id']} has no health timestamp.")
