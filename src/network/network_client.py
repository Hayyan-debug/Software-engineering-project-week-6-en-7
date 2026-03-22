import json
import socket
import threading


class NetworkClient:
    """
    Sends local player state to the server, receives opponent state back.
    All socket I/O runs on a background thread so the game loop never blocks.
    Uses JSON message protocol with type envelopes.
    """

    def __init__(self, host: str = "localhost", port: int = 5555):
        self.host = host
        self.port = port
        self.sock: socket.socket | None = None
        self.connected = False
        self.player_id: int = -1  # assigned by server (0 or 1)
        self.player_name = f"Player_{threading.get_ident() % 1000}"
        self._lock = threading.Lock()

        # Incoming data buckets
        self.opponent_state: dict = {}  # latest game-play state
        self.opponent_lobby: dict = {}  # weapon / arena selections
        self.room_full = False  # True once 2 players paired
        self.opponent_ready = False
        self.all_ready = False
        self.opponent_disconnected = False
        self.room_players: list[dict] = []  # [{player_id, name}, ...]

    # Connection
    def connect(self, room_key: str = "DEFAULT") -> bool:
        """Try to connect to the given room; returns True on success."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(10)

            # Send join_room
            join_msg = json.dumps({"type": "join_room", "room_key": room_key, "name": self.player_name}) + "\n"
            self.sock.sendall(join_msg.encode())

            # Wait for welcome message with player_id
            buf = b""
            while b"\n" not in buf:
                chunk = self.sock.recv(4096)
                if not chunk:
                    return False
                buf += chunk

            line, _ = buf.split(b"\n", 1)
            welcome = json.loads(line.decode())

            if welcome.get("type") == "error":
                print(f"[client] Server error: {welcome.get('message')}")
                return False
            if welcome.get("type") != "welcome":
                return False

            self.player_id = welcome["player_id"]

            self.connected = True
            self.sock.settimeout(None)  # blocking recv in thread
            threading.Thread(target=self._recv_loop, daemon=True).start()
            threading.Thread(target=self._heartbeat_loop, daemon=True).start()
            return True
        except OSError:
            return False

    # Sending
    def _send(self, msg: dict) -> None:
        if not self.connected or self.sock is None:
            return
        try:
            self.sock.sendall((json.dumps(msg) + "\n").encode())
        except OSError:
            self.connected = False

    def send_state(self, state: dict) -> None:
        """Send game-play state to server."""
        self._send({"type": "state", "data": state})

    def send_lobby_selection(self, selection: dict) -> None:
        """Send weapon / arena selection during lobby."""
        self._send({"type": "lobby_selection", "data": selection})

    def send_ready(self) -> None:
        """Signal that this player is ready to start."""
        self._send({"type": "ready"})

    # Receiving
    def get_opponent_state(self) -> dict:
        with self._lock:
            snap = dict(self.opponent_state)
            # Clear consumed hit_events
            if "hit_events" in self.opponent_state:
                self.opponent_state["hit_events"] = []
            return snap

    def get_opponent_lobby(self) -> dict:
        with self._lock:
            return dict(self.opponent_lobby)

    def _recv_loop(self) -> None:
        buffer = b""
        while self.connected:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.strip():
                        continue
                    msg = json.loads(line.decode())
                    self._handle_message(msg)
            except Exception:
                break
        self.connected = False

    def _handle_message(self, msg: dict) -> None:
        msg_type = msg.get("type", "")
        with self._lock:
            if msg_type == "opponent_state":
                new_state = msg.get("data", {})
                new_hits = new_state.get("hit_events", [])
                old_hits = self.opponent_state.get("hit_events", [])

                # Merge old+new hit states so we don't drop events in high framerate bursts
                if new_hits:
                    new_state["hit_events"] = old_hits + new_hits
                else:
                    new_state["hit_events"] = old_hits

                self.opponent_state = new_state
            elif msg_type == "opponent_lobby":
                self.opponent_lobby = msg.get("data", {})
            elif msg_type == "room_full":
                self.room_full = True
                self.room_players = msg.get("players", [])
            elif msg_type == "opponent_ready":
                self.opponent_ready = True
            elif msg_type == "all_ready":
                self.all_ready = True
            elif msg_type == "opponent_disconnected":
                self.opponent_disconnected = True

    def _heartbeat_loop(self) -> None:
        while self.connected:
            self._send({"type": "heartbeat"})
            import time

            time.sleep(2)
