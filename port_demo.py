import socket
import threading
from datetime import datetime

BIND_HOST = "0.0.0.0"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Ask the OS for an available ephemeral UDP port
sock.bind((BIND_HOST, 0))

bind_ip, local_port = sock.getsockname()

peer_ip = None
peer_port = None


def timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def get_local_ip():
    """
    Determine the primary LAN IP used by this machine.
    No traffic actually needs to be sent.
    """
    temp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        temp.connect(("8.8.8.8", 80))
        return temp.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        temp.close()


local_ip = get_local_ip()


def receive_messages():
    while True:
        try:
            data, address = sock.recvfrom(65535)

            source_ip, source_port = address

            print()
            print(
                f"[{timestamp()}] RECEIVE "
                f"{source_ip}:{source_port} --> {local_ip}:{local_port}"
            )

            print(f"    DATA: {data.decode(errors='replace')}")

            print("> ", end="", flush=True)

        except OSError:
            break

        except Exception as e:
            print(f"\nReceive error: {e}")
            break


thread = threading.Thread(
    target=receive_messages,
    daemon=True
)

thread.start()


print("=" * 70)
print(" UDP PORT COMMUNICATION DEMO")
print("=" * 70)

print("\nLocal listener:")
print(f"    {BIND_HOST}:{local_port}")

print("\nLAN endpoint:")
print(f"    {local_ip}:{local_port}")

print(
    "\nCommands:\n"
    "    /peer IP:PORT     Set destination endpoint\n"
    "    /status           Show endpoints\n"
    "    /quit             Exit\n"
    "\nAnything else will be sent as a UDP message."
)


while True:

    try:
        message = input("> ").strip()

        if not message:
            continue


        if message == "/quit":
            break


        if message == "/status":

            print(f"\nListener : {BIND_HOST}:{local_port}")
            print(f"Local LAN: {local_ip}:{local_port}")

            if peer_ip and peer_port:
                print(f"Remote   : {peer_ip}:{peer_port}")
            else:
                print("Remote   : NOT SET")

            continue


        if message.startswith("/peer "):

            try:

                endpoint = message.split(maxsplit=1)[1]

                ip, port = endpoint.rsplit(":", 1)

                peer_ip = ip.strip()
                peer_port = int(port)

                print("\nPeer set:")
                print(
                    f"    {local_ip}:{local_port}"
                    f" --> "
                    f"{peer_ip}:{peer_port}"
                )

            except Exception:
                print("Usage:")
                print("    /peer IP:PORT")
                print()
                print("Example:")
                print("    /peer 10.10.10.159:45676")

            continue


        if peer_ip is None or peer_port is None:

            print("Set a peer first:")
            print("    /peer IP:PORT")

            continue


        payload = message.encode()

        sock.sendto(
            payload,
            (peer_ip, peer_port)
        )

        print(
            f"[{timestamp()}] SEND    "
            f"{local_ip}:{local_port} --> "
            f"{peer_ip}:{peer_port}"
        )

        print(f"    DATA: {message}")


    except KeyboardInterrupt:
        break


sock.close()

print("\nSocket closed.")