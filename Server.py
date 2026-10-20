
import socket
import ssl
import threading
import json
import os

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "5050"))

clients = {}
lock = threading.Lock()


def send_message(conn, data):
    conn.sendall(
        (json.dumps(data) + "\n").encode("utf-8")
    )


def broadcast(data):
    with lock:
        for conn in list(clients.keys()):
            try:
                send_message(conn, data)
            except OSError:
                pass


def handle_client(conn):
    username = None

    try:
        reader = conn.makefile("r", encoding="utf-8")

        login = json.loads(reader.readline())
        username = str(login.get("username", "")).strip()

        if not username or len(username) > 24:
            send_message(conn, {
                "type": "error",
                "text": "Username must be 1-24 characters"
            })
            return

        with lock:
            if any(
                name.lower() == username.lower()
                for name in clients.values()
            ):
                send_message(conn, {
                    "type": "error",
                    "text": "Username already exists"
                })
                return

            clients[conn] = username

        send_message(conn, {
            "type": "system",
            "text": "Welcome, " + username
        })

        broadcast({
            "type": "system",
            "text": username + " joined the chat"
        })

        for line in reader:
            if not line:
                break

            data = json.loads(line)

            if data.get("type") != "message":
                continue

            message = str(data.get("text", "")).strip()

            if message == "/quit":
                break

            if not message or len(message) > 2000:
                continue

            broadcast({
                "type": "message",
                "username": username,
                "text": message
            })

    except (OSError, ValueError, ssl.SSLError):
        pass

    finally:
        with lock:
            old_name = clients.pop(conn, None)

        try:
            conn.close()
        except OSError:
            pass

        if old_name:
            broadcast({
                "type": "system",
                "text": old_name + " left the chat"
            })


def main():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    context.load_cert_chain(
        certfile="cert.pem",
        keyfile="key.pem"
    )

    with socket.socket(
        socket.AF_INET, socket.SOCK_STREAM
    ) as server:

        server.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        server.bind((HOST, PORT))
        server.listen()

        print("Secure Chat Server Started")
        print(f"Listening on {HOST}:{PORT}")

        try:
            while True:
                raw_conn, address = server.accept()

                try:
                    conn = context.wrap_socket(
                        raw_conn,
                        server_side=True
                    )
                except ssl.SSLError:
                    raw_conn.close()
                    continue

                print("Connection from:", address)

                threading.Thread(
                    target=handle_client,
                    args=(conn,),
                    daemon=True
                ).start()

        except KeyboardInterrupt:
            print("\nServer stopped")


if __name__ == "__main__":
    main()
S