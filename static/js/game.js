const socket = io();
const ROOM_ID = window.location.pathname.split('/').pop();

socket.emit('join', { room: ROOM_ID });

setInterval(() => {
    socket.emit('request_player_update', { room: ROOM_ID });
}, 5000);

function addInitiative() {
    const name = document.getElementById('init-name').value;
    const value = document.getElementById('init-val').value;
    if (name && value) {
        socket.emit('update_initiative', { room: ROOM_ID, name: name, value: value });
        document.getElementById('init-name').value = '';
        document.getElementById('init-val').value = '';
    }
}

function clearInitiative() {
    if (confirm("Очистить список инициативы?")) {
        socket.emit('clear_initiative', { room: ROOM_ID });
    }
}

socket.on('init_list_update', (list) => {
    const container = document.getElementById('initiative-list');
    container.innerHTML = '';
    list.forEach(item => {
        const div = document.createElement('div');
        div.className = 'init-item';
        div.innerHTML = `<span class="init-score">${item.value}</span> <span class="init-name">${item.name}</span>`;
        container.appendChild(div);
    });
});

socket.on('update_player_list', (users) => {
    const listContainer = document.getElementById('player-list');
    if (!listContainer) return;
    listContainer.innerHTML = '';
    const processedNames = new Set();
    Object.values(users).forEach(user => {
        if (processedNames.has(user.name)) return;
        processedNames.add(user.name);
        const div = document.createElement('div');
        div.className = `player-entry ${user.is_dm ? 'is-master' : ''}`;
        div.innerHTML = `<div class="status-dot"></div><span class="player-name">${user.name}</span><span class="player-role">${user.is_dm ? 'Master' : 'Player'}</span>`;
        listContainer.appendChild(div);
    });
});

function drag(ev) { ev.dataTransfer.setData("text", ev.target.id); }
function allowDrop(ev) { ev.preventDefault(); }
function drop(ev) {
    ev.preventDefault();
    const id = ev.dataTransfer.getData("text");
    const board = document.getElementById('game-board');
    const rect = board.getBoundingClientRect();
    let x = Math.floor((ev.clientX - rect.left) / 50) * 50 + 2;
    let y = Math.floor((ev.clientY - rect.top) / 50) * 50 + 2;
    const el = document.getElementById(id);
    el.style.left = x + 'px'; el.style.top = y + 'px';
    socket.emit('move_token', { id: id, x: x, y: y, room: ROOM_ID, label: el.innerText, type: el.classList.contains('enemy-token') ? 'enemy' : 'player' });
}

socket.on('init_state', (data) => {
    for (const id in data.tokens) updateOrSpawnToken(data.tokens[id]);
    // Загрузка инициативы при входе
    if (data.initiative) {
        const container = document.getElementById('initiative-list');
        container.innerHTML = '';
        data.initiative.forEach(item => {
            const div = document.createElement('div');
            div.className = 'init-item';
            div.innerHTML = `<span class="init-score">${item.value}</span> <span class="init-name">${item.name}</span>`;
            container.appendChild(div);
        });
    }
});

socket.on('update_map', (data) => { updateOrSpawnToken(data); });

function updateOrSpawnToken(data) {
    let el = document.getElementById(data.id);
    if (!el) {
        el = document.createElement('div');
        el.id = data.id;
        el.className = data.type === 'enemy' ? 'token enemy-token' : 'token player-token';
        el.innerText = data.label;
        el.draggable = true;
        el.ondragstart = drag;
        document.getElementById('game-board').appendChild(el);
    }
    el.style.left = data.x + 'px'; el.style.top = data.y + 'px';
}

function updateMod(input) {
    const val = parseInt(input.value) || 10;
    const mod = Math.floor((val - 10) / 2);
    input.parentElement.querySelector('.mod').innerText = (mod >= 0 ? '+' : '') + mod;
}

function updateHPBar() {
    const cur = parseInt(document.getElementById('hp-cur').value) || 0;
    const max = parseInt(document.getElementById('hp-max').value) || 1;
    document.getElementById('hp-fill').style.width = Math.min(100, (cur / max) * 100) + '%';
}

function saveCharacter() {
    const stats = document.querySelectorAll('.stat-box input');
    const data = {
        name: document.querySelector('.char-name-input').value,
        str: parseInt(stats[0].value), dex: parseInt(stats[1].value), con: parseInt(stats[2].value),
        int: parseInt(stats[3].value), wis: parseInt(stats[4].value), cha: parseInt(stats[5].value),
        hp: parseInt(document.getElementById('hp-cur').value), room: ROOM_ID
    };
    socket.emit('save_char', data);
}

function roll(sides) {
    const isPrivate = document.getElementById('private-roll').checked;
    socket.emit('roll_dice', { dice: sides, private: isPrivate, room: ROOM_ID });
}

socket.on('dice_res', (data) => {
    const log = document.getElementById('roll-log');
    const entry = document.createElement('div');
    entry.innerHTML = `${data.private ? '<span style="color:#f1c40f">[Тайный]</span> ' : ''}<strong>${data.user}</strong>: d${data.dice} 🎲 <b>${data.res}</b>`;
    log.prepend(entry);
});

function spawnEnemy() {
    const id = 'enemy-' + Math.random().toString(36).substr(2, 5);
    const data = { id: id, x: 52, y: 52, label: '💀', type: 'enemy', room: ROOM_ID };
    updateOrSpawnToken(data);
    socket.emit('move_token', data);
}

function clearTable() { socket.emit('clear_board', { room: ROOM_ID }); }
socket.on('board_cleared', () => { document.querySelectorAll('.enemy-token').forEach(e => e.remove()); });