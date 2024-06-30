# ok this was way better than hd3 reversing
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from celery import Celery
from marshmallow import Schema, fields, validate, ValidationError
import os
import re
import asyncio
import aiofiles
from werkzeug.utils import secure_filename

# Initialize Flask and its extensions
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SECRET_KEY'] = 'secret!'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
socketio = SocketIO(app)
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
db = SQLAlchemy(app)

# Define the database models
class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = fields.Str(required=True, validate=validate.Length(min=1))
    last_name = fields.Str(required=True, validate=validate.Length(min=1))
    swimmer_id = fields.Str(required=True, validate=validate.Length(equal=10))
    birth_date = fields.Date(required=True)
    event_number = fields.Str(required=True)
    heat_number = fields.Str(required=True)
    lane_number = fields.Str(required=True)
    seed_time = fields.Str(required=True, validate=validate.Regexp(r'^\d{1,2}:\d{2}\.\d{2}$'))

# Schema for participant validation
class ParticipantSchema(Schema):
    first_name = fields.Str(required=True, validate=validate.Length(min=1))
    last_name = fields.Str(required=True, validate=validate.Length(min=1))
    swimmer_id = fields.Str(required=True, validate=validate.Length(equal=10))
    birth_date = fields.Date(required=True)
    event_number = fields.Str(required=True)
    heat_number = fields.Str(required=True)
    lane_number = fields.Str(required=True)
    seed_time = fields.Str(required=True, validate=validate.Regexp(r'^\d{1,2}:\d{2}\.\d{2}$'))

participant_schema = ParticipantSchema()

# Flask route to handle file uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        emit('error', {'error': 'No file part'})
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        emit('error', {'error': 'No selected file'})
        return "No selected file", 400
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        result = parse_sd3_file.delay(file_path)
        return jsonify({"message": "File uploaded and parsing initiated", "task_id": result.id}), 202

# Celery task for processing SD3 files
@celery.task
def parse_sd3_file(file_path):
    asyncio.run(process_file(file_path))

async def process_file(file_path):
    async with aiofiles.open(file_path, 'r') as file:
        content = await file.read()
    parser = SD3Parser(content)
    participants = parser.parse_participants()
    store_data(participants)
    socketio.emit('message', {'data': 'File has been processed and data stored.'})

# Parser class for SD3 files
class SD3Parser:
    def __init__(self, content):
        self.content = content

    def parse_participants(self):
        participants = []
        participant_pattern = re.compile(r'^D01CA\s+(.*?),\s+(.*?)\s+(\w{10})USA(\d{8})\d{2}MX\s+(\d{3})\s+(\d)\s+(\d{4})\s+(.*?)Y', re.MULTILINE)
        for match in participant_pattern.finditer(self.content):
            try:
                participant_data = {
                    'first_name': match.group(2).strip(),
                    'last_name': match.group(1).strip(),
                    'swimmer_id': match.group(3).strip(),
                    'birth_date': match.group(4).strip(),
                    'event_number': match.group(5).strip(),
                    'heat_number': match.group(6).strip(),
                    'lane_number': match.group(7).strip(),
                    'seed_time': match.group(8).strip(),
                }
                validated_data = participant_schema.load(participant_data)
                participants.append(validated_data)
            except ValidationError as err:
                socketio.emit('error', {'error': str(err.messages)})
        return participants

# Function to store parsed data into the database
def store_data(participants):
    for participant in participants:
        entry = Participant(**participant)
        db.session.add(entry)
    db.session.commit()

if __name__ == '__main__':
    db.create_all()
    socketio.run(app, debug=True)
