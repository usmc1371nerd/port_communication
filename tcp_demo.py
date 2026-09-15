import socket
import threading
import sys
from datetime import datetime

BUFFER_SIZE = 4096

server_socket = None
conn = None
running = True


def timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def receive_loop(sock):
    global running

    while running:
        try:
            data = sock.recv(BUFFER_SIZE)

            if not data:
                print()
                print(f"[{timestamp()}] PEER DISCONNECTED")
                print("Remote side closed the TCP connection.")
                running = False
                break

            message = data.decode(errors="replace")

            print()
            print(f"[{timestamp()}] RECEIVE")
            print(f"    DATA: {message}")
            print("> ", end="", flush=True)

        except ConnectionResetError:
            print()
            print(f"[{timestamp()}] CONNECTION RESET")
            print("The remote side disappeared unexpectedly.")
            running = False
            break

        except OSError:
            running = False
            break


def run_server():
    global server_socket
    global conn
    global running

    host = "0.0.0.0"

    server_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    # Port 0 means:
    # ask the OS for an available ephemeral port
    server_socket.bind((host, 0))

    server_socket.listen(1)

    local_ip, local_port = server_socket.getsockname()

    print()
    print("=" * 70)
    print(" TCP SERVER")
    print("=" * 70)

    print()
    print("Listening on:")
    print(f"    {local_ip}:{local_port}")

    print()
    print("Give the other machine your LAN IP and this port.")
    print()

    conn, addr = server_socket.accept()

    remote_ip, remote_port = addr

    print(f"[{timestamp()}] CONNECTED")
    print(f"    Remote: {remote_ip}:{remote_port}")

    local_ip, local_port = conn.getsockname()

    print(f"    Local : {local_ip}:{local_port}")
    print()

    receiver = threading.Thread(
        target=receive_loop,
        args=(conn,),
        daemon=True
    )

    receiver.start()

    while running:
        try:
            message = input("> ").strip()

            if not message:
                continue

            if message == "/quit":
                break

            conn.sendall(message.encode())

            print(
                f"[{timestamp()}] SEND "
                f"{local_ip}:{local_port} -> "
                f"{remote_ip}:{remote_port}"
            )

        except (BrokenPipeError, ConnectionResetError):
            print()
            print("Connection lost.")
            break

    running = False

    try:
        conn.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass

    try:
        conn.close()
    except Exception:
        pass

    try:
        server_socket.close()
    except Exception:
        pass

    print("TCP connection closed.")


def run_client():
    global conn
    global running

    target = input(
        "Enter server IP:PORT\n> "
    ).strip()

    try:
        ip, port = target.rsplit(":", 1)
        port = int(port)

    except ValueError:
        print("Invalid format.")
        print("Use:")
        print("    10.10.10.159:45676")
        return

    conn = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    print()
    print(f"Connecting to {ip}:{port}...")

    try:
        conn.connect((ip, port))

    except ConnectionRefusedError:
        print("Connection refused.")
        return

    except TimeoutError:
        print("Connection timed out.")
        return

    local_ip, local_port = conn.getsockname()
    remote_ip, remote_port = conn.getpeername()

    print()
    print(f"[{timestamp()}] CONNECTED")

    print(f"    Local : {local_ip}:{local_port}")
    print(f"    Remote: {remote_ip}:{remote_port}")
    print()

    receiver = threading.Thread(
        target=receive_loop,
        args=(conn,),
        daemon=True
    )

    receiver.start()

    while running:
        try:
            message = input("> ").strip()

            if not message:
                continue

            if message == "/quit":
                break

            conn.sendall(message.encode())

            print(
                f"[{timestamp()}] SEND "
                f"{local_ip}:{local_port} -> "
                f"{remote_ip}:{remote_port}"
            )

        except (BrokenPipeError, ConnectionResetError):
            print()
            print("Connection lost.")
            break

    running = False

    try:
        conn.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass

    try:
        conn.close()
    except Exception:
        pass

    print("TCP connection closed.")


def main():
    print()
    print("=" * 70)
    print(" TCP COMMUNICATION DEMO")
    print("=" * 70)

    print()
    print("Choose mode:")
    print("    1 = Server / Listener")
    print("    2 = Client / Connector")
    print()

    choice = input("> ").strip()

    if choice == "1":
        run_server()

    elif choice == "2":
        run_client()

    else:
        print("Invalid selection.")


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print()
        print("Closing...")
        sys.exit(0)