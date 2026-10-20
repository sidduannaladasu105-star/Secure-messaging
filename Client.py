
import socket
import ssl
import threading
import json

HOST = "localhost"
PORT = 5050


def send_message(conn, data):
    conn.sendall(
        (json.dumps(data) + "\n").encode("utf-8")
    )


def receive_messages(reader):
    try:
        for line in reader:
            if not line:
                break

            data = json.loads(line)

            if data.get("type") == "message":
                print(
                    f"\n{data['username']}: {data['text']}"
                )
            else:
                print(
                    f"\n[{data.get('type', 'info')}] "
                    f"{data.get('text', '')}"
                )

        print("\nServer closed the connection.")

    except Exception as error:
        print("\nReceive error:", error)


def main():
    username = input("Enter username: ").strip()

    if not username or len(username) > 24:
        print("Username must be 1-24 characters")
        return

    context = ssl.create_default_context(cafile="cert.pem")
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    try:
        with socket.create_connection(
            (HOST, PORT), timeout=10
        ) as raw:

            with context.wrap_socket(
                raw, server_hostname=HOST
            ) as conn:

                conn.settimeout(None)
                reader = conn.makefile(
                    "r", encoding="utf-8"
                )

                send_message(conn, {
                    "type": "login",
                    "username": username
                })

                threading.Thread(
                    target=receive_messages,
                    args=(reader,),
                    daemon=True
                ).start()

                print("Connected securely!")
                print("Type /quit to exit.")

                while True:
                    message = input("> ")

                    send_message(conn, {
                        "type": "message",
                        "text": message
                    })

                    if message.strip() == "/quit":
                        break

    except (OSError, ssl.SSLError) as error:
        print("Connection error:", error)


if __name__ == "__main__":
    main()
