import socket
import threading
import json
import time

HOST = '0.0.0.0'
PORT = 12345
MAX_PLAYERS = 4
TICK_RATE = 0.1
<<<<<<< HEAD

clients = {}
client_inputs = {}
=======
TIMEOUT = 5

clients = {}
client_last_seen = {}
>>>>>>> 181a6b0 (Initial commit: multiplayer server met networking)
game_state = {
    "players": {}
}

lock = threading.Lock()

def handle_client(conn, addr):
<<<<<<< HEAD
=======
    name = None
>>>>>>> 181a6b0 (Initial commit: multiplayer server met networking)
    try:
        conn.sendall(b"Welkom! Stuur je naam:\n")
        name_data = conn.recv(1024).decode().strip()
        if not name_data:
            conn.close()
            return
        
        name = name_data
        with lock:
<<<<<<< HEAD
            if len(clients) >= MAX_PLAYERS:
                conn.sendall(b"Server vol\n")
                conn.close()
                return
            clients[conn] = name
            game_state["players"][name] = {}
            client_inputs[name] = None
            print(f"{name} connected from {addr}")
=======
            if name not in game_state["players"]:
                if len(clients) >= MAX_PLAYERS:
                    conn.sendall(b"Server vol\n")
                    conn.close()
                    return
            
            game_state["players"][name] = {}
            clients[conn] = name
            client_last_seen[name] = time.time()
        print(f"{name} connected from {addr}")
>>>>>>> 181a6b0 (Initial commit: multiplayer server met networking)

        while True:
            data = conn.recv(4096)
            if not data:
                break
            try:
<<<<<<< HEAD
                # Receive full player state snapshot
                state = json.loads(data.decode())
                with lock:
                    game_state["players"][name] = state
=======
                msg = json.loads(data.decode())
                # Receive full player state snapshot
                with lock:
                    client_last_seen[name] = time.time()

                    if msg.get("type") == "heartbeat":
                        continue
                    
                    if msg.get("type") == "state":
                        state = msg.get("data", {})

                        old = game_state["players"].get(name, {})

                        old_x = old.get("x", 0)
                        old_y = old.get("y", 0)

                        new_x = state.get("x", old_x)
                        new_y = state.get("y", old_y)

                        MAX_MOVE = 5

                        if abs(new_x - old_x) > MAX_MOVE or abs(new_y - old_y) > MAX_MOVE:
                            print(f"{name} suspicious movement ignored")
                            continue
                        game_state["players"][name] = state
>>>>>>> 181a6b0 (Initial commit: multiplayer server met networking)
            except json.JSONDecodeError:
                pass
    finally:
        with lock:
            if conn in clients:
<<<<<<< HEAD
                print(f"{clients[conn]} disconnected")
                if clients[conn] in game_state["players"]:
                    del game_state["players"][clients[conn]]
                del client_inputs[clients[conn]]
                del clients[conn]
        conn.close()
=======
                name = clients[conn]
                print(f"{name} disconnected")
                del clients[conn] 
        conn.close() 
>>>>>>> 181a6b0 (Initial commit: multiplayer server met networking)

def game_loop():
    while True:
        time.sleep(TICK_RATE)
<<<<<<< HEAD
        with lock:
            # Simply broadcast the overall game state to all clients
            state_json = json.dumps(game_state).encode()
            for conn in clients:
=======

        with lock:
            now = time.time()

            # TIMEOUT CHECK
            to_remove = []
            for conn, name in list(clients.items()):
                last_seen = client_last_seen.get(name, 0)

                if now - last_seen > TIMEOUT:
                    print(f"{name} timed out")
                    to_remove.append(conn)

            for conn in to_remove:
                name = clients[conn]

                del clients[conn]
                if name in client_last_seen:
                    del client_last_seen[name]

                try:
                    conn.close()
                except:
                    pass

            # BROADCAST GAME STATE
            state_json = json.dumps({
                "type": "state",
                "players": game_state["players"],
                "timestamp": time.time()
            }).encode()

            for conn in list(clients.keys()):
>>>>>>> 181a6b0 (Initial commit: multiplayer server met networking)
                try:
                    conn.sendall(state_json + b"\n")
                except:
                    pass


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
<<<<<<< HEAD
=======
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
>>>>>>> 181a6b0 (Initial commit: multiplayer server met networking)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Server running on {HOST}:{PORT}")

    threading.Thread(target=game_loop, daemon=True).start()

    while True:
        conn, addr = server.accept()
<<<<<<< HEAD
=======
        conn.settimeout(10)
>>>>>>> 181a6b0 (Initial commit: multiplayer server met networking)
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()


            

                 
<<<<<<< HEAD
        
=======
        
>>>>>>> 181a6b0 (Initial commit: multiplayer server met networking)
