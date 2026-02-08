from flask import Flask
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Simple storage
agents = {}
sessions = {}

@app.route('/')
def home():
    return f"""
    <h1>Remote Access Server</h1>
    <p>Status: <strong style='color:green'>Online</strong></p>
    <p>Active Agents: {len(agents)}</p>
    <p>Active Sessions: {len(sessions)}</p>
    """

@socketio.on('connect')
def connect():
    print("New connection")

@socketio.on('register')
def register(data):
    agent_id = data.get('agent_id')
    agents[agent_id] = request.sid
    emit('registered', {'status': 'ok'})
    print(f"Agent registered: {agent_id}")

@socketio.on('get_agents')
def list_agents():
    emit('agents_list', {'agents': list(agents.keys())})

@socketio.on('connect_to')
def connect_to(data):
    agent_id = data.get('agent_id')
    if agent_id in agents:
        session_id = f"sess_{int(time.time())}"
        sessions[session_id] = agent_id
        emit('session_created', {'session_id': session_id})
        emit('new_connection', {'session_id': session_id}, room=agents[agent_id])

@socketio.on('command')
def command(data):
    session_id = data.get('session_id')
    cmd = data.get('command')
    if session_id in sessions:
        agent_id = sessions[session_id]
        emit('execute', {'command': cmd}, room=agents[agent_id])

@socketio.on('result')
def result(data):
    session_id = data.get('session_id')
    output = data.get('output')
    emit('command_output', {'output': output}, room=session_id)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
