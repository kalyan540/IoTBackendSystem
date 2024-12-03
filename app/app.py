from flask import Flask, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

# Connect to MongoDB
mongo_client = MongoClient("mongodb://mongodb:27017")
db = mongo_client["mydatabase"]

# CRUD endpoints
@app.route('/add', methods=['POST'])
def add_document():
    data = request.json
    result = db.mycollection.insert_one(data)
    # Convert ObjectId to string and return
    data['_id'] = str(result.inserted_id)
    return jsonify({"status": "success", "data": data}), 201

@app.route('/list', methods=['GET'])
def list_documents():
    documents = list(db.mycollection.find({}, {"_id": 0}))
    return jsonify(documents), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
