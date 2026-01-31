import random
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dnd_vtt_ultra_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dnd_vtt.db'

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", allow_unsafe_werkzeug=True)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

rooms_data = {}
active_users = {}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dm_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100), default="Новый герой")
    str = db.Column(db.Integer, default=10)
    dex = db.Column(db.Integer, default=10)
    con = db.Column(db.Integer, default=10)
    int = db.Column(db.Integer, default=10)
    wis = db.Column(db.Integer, default=10)
    cha = db.Column(db.Integer, default=10)
    hp = db.Column(db.Integer, default=10)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    if current_user.is_authenticated:
        rooms = Room.query.all()
        for r in rooms:
            dm = User.query.get(r.dm_id)
            r.dm_username = dm.username if dm else "Unknown"
        return render_template('lobby.html', rooms=rooms)
    return redirect(url_for('login'))


@app.route('/register', methods=['POST'])
def register():
    user = User(username=request.form['username'], password=generate_password_hash(request.form['password']))
    db.session.add(user)
    db.session.commit()
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/create_room', methods=['POST'])
@login_required
def create_room():
    new_room = Room(name=request.form['room_name'], dm_id=current_user.id)
    db.session.add(new_room)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/room/<int:room_id>')
@login_required
def room(room_id):
    room_obj = Room.query.get_or_404(room_id)
    is_dm = (room_obj.dm_id == current_user.id)
    char = Character.query.filter_by(user_id=current_user.id).first()
    if not char:
        char = Character(user_id=current_user.id, name=current_user.username)
        db.session.add(char)
        db.session.commit()
    return render_template('room.html', room=room_obj, is_dm=is_dm, char=char)


@socketio.on('join')
def on_join(data):
    rid = str(data['room'])
    join_room(rid)
    room_obj = Room.query.get(int(rid))

    if rid not in rooms_data:
        rooms_data[rid] = {'tokens': {}, 'initiative': []}

    if rid not in active_users: active_users[rid] = {}
    is_dm = (room_obj.dm_id == current_user.id)
    active_users[rid][request.sid] = {'name': current_user.username, 'is_dm': is_dm}

    if is_dm: join_room(f"dm_{rid}")

    emit('update_player_list', active_users[rid], room=rid)
    emit('init_state', rooms_data[rid], room=request.sid)


@socketio.on('request_player_update')
def handle_player_request(data):
    rid = str(data['room'])
    if rid in active_users:
        emit('update_player_list', active_users[rid], room=request.sid)


@socketio.on('move_token')
def handle_move(data):
    rid = str(data['room'])
    tid = data['id']
    rooms_data[rid]['tokens'][tid] = data
    emit('update_map', data, room=rid, include_self=False)


@socketio.on('clear_board')
def handle_clear(data):
    rid = str(data['room'])
    rooms_data[rid]['tokens'] = {k: v for k, v in rooms_data[rid]['tokens'].items() if not k.startswith('enemy')}
    emit('board_cleared', {}, room=rid)


@socketio.on('roll_dice')
def handle_roll(data):
    rid = str(data['room'])
    res = random.randint(1, int(data['dice']))
    msg = {'user': current_user.username, 'res': res, 'dice': data['dice'], 'private': data['private']}
    if data['private']:
        emit('dice_res', msg, room=request.sid)
        emit('dice_res', msg, room=f"dm_{rid}")
    else:
        emit('dice_res', msg, room=rid)


@socketio.on('update_initiative')
def handle_init(data):
    rid = str(data['room'])
    rooms_data[rid]['initiative'].append(data)
    rooms_data[rid]['initiative'].sort(key=lambda x: int(x['value']), reverse=True)
    emit('init_list_update', rooms_data[rid]['initiative'], room=rid)


@socketio.on('clear_initiative')
def clear_init(data):
    rid = str(data['room'])
    rooms_data[rid]['initiative'] = []
    emit('init_list_update', [], room=rid)


@socketio.on('save_char')
def save_char(data):
    char = Character.query.filter_by(user_id=current_user.id).first()
    if char:
        char.name = data['name'];
        char.hp = data['hp']
        char.str, char.dex, char.con = data['str'], data['dex'], data['con']
        char.int, char.wis, char.cha = data['int'], data['wis'], data['cha']
        db.session.commit()
        emit('save_confirm', {'status': 'success'}, room=request.sid)


@socketio.on('disconnect')
def on_disconnect():
    for rid in active_users:
        if request.sid in active_users[rid]:
            del active_users[rid][request.sid]
            emit('update_player_list', active_users[rid], room=rid)
            break


if __name__ == '__main__':
    with app.app_context(): db.create_all()
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)