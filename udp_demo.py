import socket
import threading
import time
import sys
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

BIND_IP = "0.0.0.0"

HEARTBEAT_INTERVAL = 2
PEER_TIMEOUT = 6


# ============================================================
# STATE
# ============================================================

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Port 0 = ask OS for an available ephemeral port
sock.bind((BIND_IP, 0))

_, local_port = sock.getsockname()

peer_ip = None
peer_port = None

connected = False
running = True

last_seen = 0
last_rtt = None

heartbeat_sent = {}

state_lock = threading.Lock()


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def get_local_ip():
    """
    Determine the LAN IP this system normally uses.
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


def endpoint():
    if peer_ip and peer_port:
        return f"{peer_ip}:{peer_port}"

    return "NOT SET"


def show_banner():
    print()
    print("=" * 70)
    print(" UDP SESSION COMMUNICATION DEMO")
    print("=" * 70)

    print()
    print("LOCAL LISTENER")
    print(f"  {BIND_IP}:{local_port}")

    print()
    print("LAN ENDPOINT")
    print(f"  {local_ip}:{local_port}")

    print()
    print("Commands:")
    print("  /peer IP:PORT      Connect to remote peer")
    print("  /status            Show session status")
    print("  /quit              Gracefully disconnect")
    print()
    print("Anything else will be sent as a message.")
    print()


def show_status():

    with state_lock:

        print()
        print("=" * 50)
        print(" STATUS")
        print("=" * 50)

        print(f"Local : {local_ip}:{local_port}")
        print(f"Remote: {endpoint()}")

        if connected:
            print("State : CONNECTED")
        else:
            print("State : DISCONNECTED")

        if last_seen:
            ago = time.time() - last_seen
            print(f"Peer last seen: {ago:.1f} seconds ago")

        if last_rtt is not None:
            print(f"Heartbeat RTT: {last_rtt:.1f} ms")

        print("=" * 50)
        print()


# ============================================================
# NETWORK FUNCTIONS
# ============================================================

def send_packet(message):
    """
    Internal packet sender.
    """

    if peer_ip is None or peer_port is None:
        return

    try:

        sock.sendto(
            message.encode(),
            (peer_ip, peer_port)
        )

    except OSError:
        pass


def send_user_message(message):

    if not connected:
        print("[ERROR] No active peer session.")
        return

    packet = f"MSG|{message}"

    send_packet(packet)

    print(
        f"[{timestamp()}] SEND "
        f"{local_ip}:{local_port} -> "
        f"{peer_ip}:{peer_port}"
    )

    print(f"    DATA: {message}")


# ============================================================
# RECEIVE LOOP
# ============================================================

def receive_loop():

    global connected
    global last_seen
    global last_rtt
    global peer_ip
    global peer_port

    while running:

        try:

            data, address = sock.recvfrom(65535)

        except OSError:
            break

        except Exception:
            continue

        remote_ip, remote_port = address

        message = data.decode(errors="replace")

        now = time.time()

        # ----------------------------------------------------
        # HELLO
        # ----------------------------------------------------

        if message == "HELLO":

            with state_lock:

                peer_ip = remote_ip
                peer_port = remote_port

                connected = True
                last_seen = now

            print()
            print(
                f"[{timestamp()}] CONNECTION REQUEST"
            )

            print(
                f"    {remote_ip}:{remote_port}"
            )

            send_packet("HELLO_ACK")

            print("[CONNECTED]")
            print("> ", end="", flush=True)

            continue

        # ----------------------------------------------------
        # HELLO ACK
        # ----------------------------------------------------

        if message == "HELLO_ACK":

            with state_lock:

                connected = True
                last_seen = now

            print()
            print(
                f"[{timestamp()}] HANDSHAKE COMPLETE"
            )

            print(
                f"    Connected to {remote_ip}:{remote_port}"
            )

            print("> ", end="", flush=True)

            continue

        # ----------------------------------------------------
        # HEARTBEAT
        # ----------------------------------------------------

        if message.startswith("PING|"):

            with state_lock:
                last_seen = now

            packet_id = message.split("|", 1)[1]

            send_packet(f"PONG|{packet_id}")

            continue

        # ----------------------------------------------------
        # HEARTBEAT ACK
        # ----------------------------------------------------

        if message.startswith("PONG|"):

            packet_id = message.split("|", 1)[1]

            with state_lock:

                last_seen = now

                if packet_id in heartbeat_sent:

                    sent_time = heartbeat_sent.pop(packet_id)

                    last_rtt = (
                        time.time() - sent_time
                    ) * 1000

            continue

        # ----------------------------------------------------
        # USER MESSAGE
        # ----------------------------------------------------

        if message.startswith("MSG|"):

            with state_lock:
                last_seen = now

            payload = message.split("|", 1)[1]

            print()

            print(
                f"[{timestamp()}] RECEIVE "
                f"{remote_ip}:{remote_port} -> "
                f"{local_ip}:{local_port}"
            )

            print(f"    DATA: {payload}")

            print("> ", end="", flush=True)

            continue

        # ----------------------------------------------------
        # GOODBYE
        # ----------------------------------------------------

        if message == "GOODBYE":

            print()

            print(
                f"[{timestamp()}] PEER DISCONNECTED"
            )

            print(
                f"    {remote_ip}:{remote_port}"
            )

            print()
            print("Closing local socket...")

            shutdown()

            return


# ============================================================
# HEARTBEAT LOOP
# ============================================================

def heartbeat_loop():

    counter = 0

    while running:

        time.sleep(HEARTBEAT_INTERVAL)

        if not connected:
            continue

        counter += 1

        packet_id = str(counter)

        heartbeat_sent[packet_id] = time.time()

        send_packet(
            f"PING|{packet_id}"
        )


# ============================================================
# CONNECTION WATCHDOG
# ============================================================

def watchdog_loop():

    global connected

    while running:

        time.sleep(1)

        with state_lock:

            if not connected:
                continue

            if last_seen == 0:
                continue

            elapsed = time.time() - last_seen

            if elapsed > PEER_TIMEOUT:

                print()
                print("=" * 60)
                print("[PEER LOST]")
                print("=" * 60)

                print(
                    f"No response from "
                    f"{peer_ip}:{peer_port}"
                )

                print(
                    f"Timeout after {elapsed:.1f} seconds."
                )

                print()
                print("Closing local listener...")

                connected = False

                shutdown()

                return


# ============================================================
# CONNECTION HANDSHAKE
# ============================================================

def connect_peer(target):

    global peer_ip
    global peer_port
    global last_seen

    try:

        ip, port = target.rsplit(":", 1)

        port = int(port)

        if port < 1 or port > 65535:
            raise ValueError

    except ValueError:

        print()
        print("Usage:")
        print("  /peer IP:PORT")
        print()
        print("Example:")
        print("  /peer 10.10.10.159:45676")
        print()

        return

    peer_ip = ip
    peer_port = port

    last_seen = time.time()

    print()
    print(
        f"[{timestamp()}] CONNECTING"
    )

    print(
        f"    {local_ip}:{local_port}"
        f" -> "
        f"{peer_ip}:{peer_port}"
    )

    send_packet("HELLO")

    print("HELLO sent. Waiting for response...")
    print()


# ============================================================
# SHUTDOWN
# ============================================================

def shutdown():

    global running
    global connected

    if not running:
        return

    running = False
    connected = False

    try:
        sock.close()
    except Exception:
        pass

    print("Socket closed.")


def graceful_shutdown():

    global running

    if connected:

        print()
        print(
            f"[{timestamp()}] Sending GOODBYE..."
        )

        try:
            send_packet("GOODBYE")

            # Give UDP a tiny opportunity to leave
            time.sleep(0.2)

        except Exception:
            pass

    shutdown()


# ============================================================
# START BACKGROUND THREADS
# ============================================================

receive_thread = threading.Thread(
    target=receive_loop,
    daemon=True
)

heartbeat_thread = threading.Thread(
    target=heartbeat_loop,
    daemon=True
)

watchdog_thread = threading.Thread(
    target=watchdog_loop,
    daemon=True
)

receive_thread.start()
heartbeat_thread.start()
watchdog_thread.start()


# ============================================================
# USER INTERFACE
# ============================================================

show_banner()


try:

    while running:

        command = input("> ").strip()

        if not command:
            continue

        if command == "/quit":

            graceful_shutdown()
            break

        if command == "/status":

            show_status()
            continue

        if command.startswith("/peer "):

            target = command.split(
                maxsplit=1
            )[1]

            connect_peer(target)

            continue

        send_user_message(command)


except KeyboardInterrupt:

    print()
    graceful_shutdown()


except EOFError:

    graceful_shutdown()


sys.exit(0)