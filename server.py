from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import json
import hashlib
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Database simulation
agents_db = {}  # {agent_id: {socket_id, ip, last_seen, system_info}}
sessions_db = {}  # {session_id: {controller_id, agent_id, created_at}}
command_history = []

# Authentication tokens (simple)
VALID_TOKENS = {
    'agent': 'AGENT_TOKEN_123',
    'controller': 'CONTROLLER_TOKEN_456'
}

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Remote Access Server</title></head>
    <body>
        <h1>🚀 Remote Access Server</h1>
        <p>Status: <strong style="color:green">Online</strong></p>
        <p>Active Agents: {}</p>
        <p>Active Sessions: {}</p>
    </body>
    </html>
    """.format(len(agents_db), len(sessions_db))

@app.route('/api/status')
def api_status():
    return {
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'agents': len(agents_db),
        'sessions': len(sessions_db),
        'uptime': time.time() - start_time
    }

@app.route('/api/agents')
def list_agents():
    agents_list = []
    for agent_id, info in agents_db.items():
        agents_list.append({
            'id': agent_id,
            'ip': info.get('ip', 'Unknown'),
            'last_seen': info.get('last_seen'),
            'system': info.get('system_info', {}),
            'online': (time.time() - info.get('last_seen', 0)) < 60
        })
    return {'agents': agents_list}

# Socket.IO Events
@socketio.on('connect')
def handle_connect():
    client_ip = request.remote_addr
    print(f"[+] New connection from {client_ip}")

@socketio.on('authenticate')
def handle_auth(data):
    client_type = data.get('type')
    token = data.get('token')
    client_id = data.get('client_id')
    
    if token != VALID_TOKENS.get(client_type):
        emit('auth_error', {'message': 'Invalid token'})
        return False
    
    if client_type == 'agent':
        # Agent registration
        system_info = data.get('system_info', {})
        agents_db[client_id] = {
            'socket_id': request.sid,
            'ip': request.remote_addr,
            'last_seen': time.time(),
            'system_info': system_info
        }
        emit('authenticated', {'agent_id': client_id})
        socketio.emit('agent_online', {'agent_id': client_id}, broadcast=True)
        print(f"[+] Agent registered: {client_id}")
    
    elif client_type == 'controller':
        emit('authenticated', {'controller_id': client_id})
        print(f"[+] Controller authenticated: {client_id}")

@socketio.on('agent_heartbeat')
def handle_heartbeat(data):
    agent_id = data.get('agent_id')
    if agent_id in agents_db:
        agents_db[agent_id]['last_seen'] = time.time()
        agents_db[agent_id]['system_info'] = data.get('system_info', {})

@socketio.on('request_session')
def handle_session_request(data):
    controller_id = data.get('controller_id')
    agent_id = data.get('agent_id')
    
    if agent_id not in agents_db:
        emit('error', {'message': 'Agent not found'})
        return
    
    # Create session
    session_id = hashlib.md5(f"{controller_id}{agent_id}{time.time()}".encode()).hexdigest()[:12]
    sessions_db[session_id] = {
        'controller_id': controller_id,
        'agent_id': agent_id,
        'created_at': time.time(),
        'controller_sid': request.sid,
        'agent_sid': agents_db[agent_id]['socket_id']
    }
    
    # Create room
    join_room(session_id, sid=request.sid)  # Controller joins
    join_room(session_id, sid=agents_db[agent_id]['socket_id'])  # Agent joins
    
    emit('session_created', {
        'session_id': session_id,
        'agent_id': agent_id
    }, room=request.sid)
    
    emit('session_request', {
        'session_id': session_id,
        'controller_id': controller_id
    }, room=agents_db[agent_id]['socket_id'])
    
    print(f"[+] Session created: {session_id}")

@socketio.on('accept_session')
def handle_session_accept(data):
    session_id = data.get('session_id')
    if session_id in sessions_db:
        emit('session_active', {
            'session_id': session_id,
            'controller_id': sessions_db[session_id]['controller_id']
        }, room=sessions_db[session_id]['controller_sid'])
        print(f"[+] Session accepted: {session_id}")

@socketio.on('command')
def handle_command(data):
    session_id = data.get('session_id')
    command = data.get('command')
    
    if session_id not in sessions_db:
        return
    
    # Log command
    command_history.append({
        'session_id': session_id,
        'command': command,
        'timestamp': time.time(),
        'from': 'controller'
    })
    
    # Forward to agent
    emit('execute', {
        'session_id': session_id,
        'command': command,
        'command_id': len(command_history)
    }, room=session_id)

@socketio.on('command_result')
def handle_command_result(data):
    session_id = data.get('session_id')
    output = data.get('output')
    command_id = data.get('command_id')
    
    if session_id not in sessions_db:
        return
    
    # Log result
    if command_id < len(command_history):
        command_history[command_id]['result'] = output[:500]  # Limit size
    
    # Forward to controller
    emit('result', {
        'session_id': session_id,
        'output': output,
        'command_id': command_id
    }, room=session_id)

@socketio.on('file_transfer_request')
def handle_file_request(data):
    session_id = data.get('session_id')
    filename = data.get('filename')
    filesize = data.get('filesize')
    
    emit('file_request', {
        'filename': filename,
        'filesize': filesize,
        'session_id': session_id
    }, room=session_id)

@socketio.on('file_chunk')
def handle_file_chunk(data):
    session_id = data.get('session_id')
    chunk = data.get('chunk')
    chunk_num = data.get('chunk_num')
    
    emit('file_data', {
        'chunk': chunk,
        'chunk_num': chunk_num,
        'session_id': session_id
    }, room=session_id)

@socketio.on('disconnect')
def handle_disconnect():
    # Cleanup disconnected clients
    for agent_id, info in list(agents_db.items()):
        if info['socket_id'] == request.sid:
            del agents_db[agent_id]
            socketio.emit('agent_offline', {'agent_id': agent_id}, broadcast=True)
            print(f"[-] Agent disconnected: {agent_id}")

# Background task for cleanup
def cleanup_task():
    while True:
        time.sleep(60)
        current_time = time.time()
        # Remove inactive agents
        for agent_id, info in list(agents_db.items()):
            if current_time - info['last_seen'] > 120:  # 2 minutes
                del agents_db[agent_id]
                print(f"[-] Removed inactive agent: {agent_id}")

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
cleanup_thread.start()

start_time = time.time()

if __name__ == '__main__':
    print("🚀 Advanced Remote Access Server Starting...")
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
