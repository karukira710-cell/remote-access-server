from flask import Flask
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Storage
agents = {}
sessions = {}

@app.route('/')
def home():
    return """
    <html>
    <head><title>Remote Access Server</title>
    <style>
        body { font-family: Arial; margin: 50px; background: #f0f0f0; }
        .container { background: white; padding: 30px; border-radius: 10px; max-width: 800px; margin: auto; }
        h1 { color: #333; }
        .status { color: green; font-weight: bold; }
    </style>
    </head>
    <body>
        <div class="container">
            <h1>✅ Remote Access Server</h1>
            <p><strong>Status:</strong> <span class="status">ONLINE</span></p>
            <p><strong>Agents:</strong> {}</p>
            <p><strong>Sessions:</strong> {}</p>
            <p><strong>URL:</strong> https://remote-access-server-7.onrender.com</p>
            <hr>
            <p style="color: #666;">Server is running properly.</p>
        </div>
    </body>
    </html>
    """.format(len(agents), len(sessions))

@app.route('/health')
def health():
    return {'status': 'ok', 'time': time.time()}

# Socket.IO Events
@socketio.on('connect')
def connect():
    print("Client connected")

@socketio.on('register_agent')
def register_agent(data):
    agent_id = data.get('agent_id', 'unknown')
    agents[agent_id] = {'sid': request.sid, 'time': time.time()}
    
    emit('registered', {'agent_id': agent_id, 'status': 'ok'})
    emit('agent_online', {'agent_id': agent_id}, broadcast=True)
    print(f"Agent registered: {agent_id}")

@socketio.on('register_controller')
def register_controller(data):
    controller_id = data.get('controller_id', 'controller')
    emit('controller_ready', {'controller_id': controller_id})
    emit('agents_list', {'agents': list(agents.keys())})
    print(f"Controller registered: {controller_id}")

@socketio.on('list_agents')
def list_agents():
    emit('agents_list', {'agents': list(agents.keys())})

@socketio.on('connect_agent')
def connect_agent(data):
    agent_id = data.get('agent_id')
    controller_id = data.get('controller_id', 'controller')
    
    if agent_id in agents:
        session_id = f"{agent_id}_{controller_id}_{int(time.time())}"
        sessions[session_id] = {'agent': agent_id, 'controller': controller_id}
        
        emit('session_created', {
            'session_id': session_id,
            'agent_id': agent_id
        })
        
        emit('session_request', {
            'session_id': session_id,
            'controller_id': controller_id
        }, room=agents[agent_id]['sid'])
        
        print(f"Session created: {session_id}")

@socketio.on('accept_session')
def accept_session(data):
    session_id = data.get('session_id')
    if session_id in sessions:
        emit('session_active', {'session_id': session_id}, broadcast=True)

@socketio.on('send_command')
def send_command(data):
    session_id = data.get('session_id')
    command = data.get('command')
    
    if session_id in sessions:
        agent_id = sessions[session_id]['agent']
        if agent_id in agents:
            emit('execute', {
                'command': command,
                'session_id': session_id
            }, room=agents[agent_id]['sid'])

@sio.on('command_result')
def command_result(data):
    emit('result', data, broadcast=True)

@socketio.on('disconnect')
def disconnect():
    for agent_id, info in list(agents.items()):
        if info['sid'] == request.sid:
            del agents[agent_id]
            emit('agent_offline', {'agent_id': agent_id}, broadcast=True)
            print(f"Agent disconnected: {agent_id}")

if __name__ == '__main__':
    print("Server starting on port 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
