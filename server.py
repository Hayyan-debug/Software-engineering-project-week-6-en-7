import socket
import threading
import json
import time

HOST = '0.0.0.0'
PORT = 12345
MAX_PLAYERS = 4
TICK_RATE = 0.1

clients = {}
client_inputs = {}
game_state = {
    "players": {}
}

lock = threading.Lock()

def handle_client(conn, addr):
    try:
        conn.sendall(b"Welkom! Stuur je naam:\n")
        name_data = conn.recv(1024).decode().strip()
        if not name_data:
            conn.close()
            return
        
        name = name_data
        with lock:
            if len(clients) >= MAX_PLAYERS:
                conn.sendall(b"Server vol\n")
                conn.close()
                return
            clients[conn] = name
            game_state["players"][name] = {}
            client_inputs[name] = None
            print(f"{name} connected from {addr}")

        while True:
            data = conn.recv(4096)
            if not data:
                break
            try:
                # Receive full player state snapshot
                state = json.loads(data.decode())
                with lock:
                    game_state["players"][name] = state
            except json.JSONDecodeError:
                pass
    finally:
        with lock:
            if conn in clients:
                print(f"{clients[conn]} disconnected")
                if clients[conn] in game_state["players"]:
                    del game_state["players"][clients[conn]]
                del client_inputs[clients[conn]]
                del clients[conn]
        conn.close()

def game_loop():
    while True:
        time.sleep(TICK_RATE)
        with lock:
            # Simply broadcast the overall game state to all clients
            state_json = json.dumps(game_state).encode()
            for conn in clients:
                try:
                    conn.sendall(state_json + b"\n")
                except:
                    pass


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Server running on {HOST}:{PORT}")

    threading.Thread(target=game_loop, daemon=True).start()

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()


            

                 
        
