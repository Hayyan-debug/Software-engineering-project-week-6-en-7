"""
server.py - Gauntlet Galaxy
Multiplayer game server (TCP sockets, JSON protocol)

Pairs players into 2-player rooms, relays state during lobby and gameplay.
"""

import socket
import threading
import json
import time

HOST = '0.0.0.0'
PORT = 5555
MAX_PLAYERS_PER_ROOM = 2
TICK_RATE = 0.05        # 20 ticks/s
HEARTBEAT_TIMEOUT = 8   # seconds before dropping a silent client

# ── Room management ────────────────────────────────────────────────────────

class Room:
    """A 2-player game room."""

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: dict[socket.socket, dict] = {}   # conn -> player info
        self.lock = threading.Lock()

    @property
    def full(self) -> bool:
        return len(self.players) >= MAX_PLAYERS_PER_ROOM

    def add_player(self, conn: socket.socket, name: str, player_id: int) -> None:
        with self.lock:
            self.players[conn] = {
                "name": name,
                "player_id": player_id,
                "state": {},
                "lobby": {},          # weapon / arena selections
                "last_seen": time.time(),
                "ready": False,
            }

    def remove_player(self, conn: socket.socket) -> str | None:
        with self.lock:
            info = self.players.pop(conn, None)
            return info["name"] if info else None

    def get_opponent(self, conn: socket.socket) -> tuple[socket.socket, dict] | None:
        with self.lock:
            for c, info in self.players.items():
                if c is not conn:
                    return c, info
        return None

    def broadcast(self, msg: dict, exclude: socket.socket | None = None) -> None:
        data = json.dumps(msg).encode() + b"\n"
        with self.lock:
            for conn in list(self.players.keys()):
                if conn is exclude:
                    continue
                try:
                    conn.sendall(data)
                except OSError:
                    pass


# Global state
rooms: dict[str, Room] = {}  # room_id -> Room
rooms_lock = threading.Lock()


def get_or_create_room(room_id: str) -> Room:
    """Return the room for the given ID, creating it if necessary."""
    with rooms_lock:
        if room_id not in rooms:
            rooms[room_id] = Room(room_id)
        return rooms[room_id]


# ── Client handler ─────────────────────────────────────────────────────────

def handle_client(conn: socket.socket, addr: tuple) -> None:
    room: Room | None = None
    player_id = -1
    name = ""

    try:
        # 1. Wait for join_room message
        buffer = b""
        join_msg = None
        while b"\n" not in buffer:
            chunk = conn.recv(1024)
            if not chunk:
                return
            buffer += chunk

        line, buffer = buffer.split(b"\n", 1)
        try:
            join_msg = json.loads(line.decode())
        except json.JSONDecodeError:
            return

        if join_msg.get("type") != "join_room":
            return

        room_key = join_msg.get("room_key", "default").upper()
        name = join_msg.get("name", f"Player_{addr[1]}")

        # 2. Assign to the requested room
        room = get_or_create_room(room_key)
        
        with room.lock:
            if room.full:
                conn.sendall(json.dumps({"type": "error", "message": "Room is full"}).encode() + b"\n")
                return
                
            # Assign ID based on current players
            existing_ids = [p["player_id"] for p in room.players.values()]
            player_id = 0 if 0 not in existing_ids else 1

        # Send welcome with assigned player_id
        welcome = {"type": "welcome", "player_id": player_id}
        conn.sendall(json.dumps(welcome).encode() + b"\n")

        room.add_player(conn, name, player_id)
        print(f"[room {room.room_id}] {name} (P{player_id}) connected from {addr}")

        # If this was the second player, notify both that the room is full
        if room.full:
            # Build player list for both
            with room.lock:
                player_list = [
                    {"player_id": info["player_id"], "name": info["name"]}
                    for info in room.players.values()
                ]
            room.broadcast({"type": "room_full", "players": player_list})
            print(f"[room {room.room_id}] Room is full — match starting!")

        # 4. Main receive loop
        buffer = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buffer += chunk

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line.decode())
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type", "")

                # Heartbeat — just update last_seen
                if msg_type == "heartbeat":
                    with room.lock:
                        if conn in room.players:
                            room.players[conn]["last_seen"] = time.time()
                    continue

                # Player state update (during gameplay)
                if msg_type == "state":
                    with room.lock:
                        if conn in room.players:
                            room.players[conn]["state"] = msg.get("data", {})
                            room.players[conn]["last_seen"] = time.time()
                    # Relay to opponent immediately
                    opponent = room.get_opponent(conn)
                    if opponent:
                        opp_conn, _ = opponent
                        relay = {"type": "opponent_state", "data": msg.get("data", {})}
                        try:
                            opp_conn.sendall(json.dumps(relay).encode() + b"\n")
                        except OSError:
                            pass
                    continue

                # Lobby selection (weapon / arena)
                if msg_type == "lobby_selection":
                    with room.lock:
                        if conn in room.players:
                            room.players[conn]["lobby"] = msg.get("data", {})
                            room.players[conn]["last_seen"] = time.time()
                    # Relay to opponent
                    opponent = room.get_opponent(conn)
                    if opponent:
                        opp_conn, _ = opponent
                        relay = {"type": "opponent_lobby", "data": msg.get("data", {})}
                        try:
                            opp_conn.sendall(json.dumps(relay).encode() + b"\n")
                        except OSError:
                            pass
                    continue

                # Player ready signal
                if msg_type == "ready":
                    with room.lock:
                        if conn in room.players:
                            room.players[conn]["ready"] = True
                            room.players[conn]["last_seen"] = time.time()
                    # Check if both ready
                    with room.lock:
                        all_ready = all(p["ready"] for p in room.players.values())
                    if all_ready:
                        room.broadcast({"type": "all_ready"})
                    else:
                        # Notify opponent that this player is ready
                        opponent = room.get_opponent(conn)
                        if opponent:
                            opp_conn, _ = opponent
                            try:
                                opp_conn.sendall(json.dumps({"type": "opponent_ready"}).encode() + b"\n")
                            except OSError:
                                pass
                    continue

    except (ConnectionResetError, ConnectionAbortedError, OSError):
        pass
    finally:
        if room:
            removed = room.remove_player(conn)
            print(f"[room {room.room_id}] {removed or name} disconnected")
            # Notify remaining player
            room.broadcast({"type": "opponent_disconnected"})
        try:
            conn.close()
        except OSError:
            pass


# ── Heartbeat checker ──────────────────────────────────────────────────────

def heartbeat_checker():
    """Periodically check for timed-out clients."""
    while True:
        time.sleep(HEARTBEAT_TIMEOUT / 2)
        now = time.time()
        with rooms_lock:
            empty_rooms = []
            for room_id, room in rooms.items():
                with room.lock:
                    to_remove = []
                    for conn, info in room.players.items():
                        if now - info["last_seen"] > HEARTBEAT_TIMEOUT:
                            print(f"[room {room.room_id}] {info['name']} timed out")
                            to_remove.append(conn)
                for conn in to_remove:
                    room.remove_player(conn)
                    room.broadcast({"type": "opponent_disconnected"})
                    try:
                        conn.close()
                    except OSError:
                        pass
                
                if len(room.players) == 0:
                    empty_rooms.append(room_id)
            
            for room_id in empty_rooms:
                del rooms[room_id]


# ── Entry point ────────────────────────────────────────────────────────────

_SERVER_RUNNING = False
_SERVER_SOCK = None

def accept_loop(server: socket.socket):
    global _SERVER_RUNNING
    while _SERVER_RUNNING:
        try:
            # Short timeout to allow check of _SERVER_RUNNING
            server.settimeout(1.0)
            conn, addr = server.accept()
            conn.settimeout(10)
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except socket.timeout:
            continue
        except OSError:
            break
            
    try:
        server.close()
    except Exception:
        pass

def start_server_daemon(port=5555):
    """Start the server in a background daemon thread."""
    global _SERVER_RUNNING, _SERVER_SOCK
    if _SERVER_RUNNING:
        return
        
    _SERVER_SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _SERVER_SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        _SERVER_SOCK.bind((HOST, port))
    except Exception:
        # If still bounds, that's fine, we fallback.
        pass
    _SERVER_SOCK.listen()
    _SERVER_RUNNING = True
    print(f"Gauntlet Galaxy server running on {HOST}:{port}")

    threading.Thread(target=heartbeat_checker, daemon=True).start()
    threading.Thread(target=accept_loop, args=(_SERVER_SOCK,), daemon=True).start()

def stop_server_daemon():
    """Stops the daemon server if it is running."""
    global _SERVER_RUNNING, _SERVER_SOCK
    if _SERVER_RUNNING:
        _SERVER_RUNNING = False
        if _SERVER_SOCK:
            try:
                _SERVER_SOCK.close()
            except Exception:
                pass
        _SERVER_SOCK = None
        print("Server shut down.")

def start_lan_broadcaster(room_key: str, port=5556):
    """Broadcasts the room key over UDP LAN so joiners can find the host IP."""
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    def broadcast_loop():
        msg = f"GAUNTLET_GALAXY|{room_key}".encode()
        while True:
            try:
                udp.sendto(msg, ('<broadcast>', port))
            except Exception:
                pass
            time.sleep(1)

    threading.Thread(target=broadcast_loop, daemon=True).start()

def start_server():
    """Start the server in the main thread (blocking)."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Gauntlet Galaxy server running on {HOST}:{PORT}")

    threading.Thread(target=heartbeat_checker, daemon=True).start()
    accept_loop(server)

if __name__ == "__main__":
    start_server()
