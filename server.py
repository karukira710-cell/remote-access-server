from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

agents = {}

@app.route('/')
def home():
    return "✅ Remote Access Server is Running"

@app.route('/status')
def status():
    return jsonify({
        'status': 'online',
        'agents': len(agents),
        'timestamp': time.time()
    })

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('register_agent')
def handle_agent(data):
    agent_id = data.get('agent_id', 'unknown')
    agents[agent_id] = request.sid
    emit('registered', {'agent_id': agent_id})
    print(f"Agent registered: {agent_id}")

@socketio.on('command')
def handle_command(data):
    agent_id = data.get('agent_id')
    command = data.get('command')
    if agent_id in agents:
        emit('execute', {'command': command}, room=agents[agent_id])

@socketio.on('result')
def handle_result(data):
    print(f"Result: {data}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
