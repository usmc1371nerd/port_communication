# Port Communication Demos

Small, interactive Python socket examples for experimenting with TCP and UDP communication between two trusted machines.

## Disclaimer

This code is written for **non-malicious use only**. Use it only on systems and networks that you own or are explicitly authorized to test. Do not use these examples to access, probe, disrupt, or communicate with systems without permission.

These demos do not provide encryption, authentication, or message integrity. Use them only for learning and controlled testing on a trusted network.

## Requirements

- Python 3
- Network access between the participating machines
- Firewall rules that allow the selected UDP or TCP port

No third-party packages are required.

## Examples

### TCP communication

Run the script on both machines:

```bash
python3 tcp_demo.py
```

1. On one machine, choose `1` for **Server / Listener**.
2. Share that machine's LAN IP and the displayed port.
3. On the other machine, choose `2` for **Client / Connector** and enter `IP:PORT`.
4. Type messages in either terminal. Enter `/quit` to close the connection.

The TCP server listens on all local interfaces and requests an available ephemeral port from the operating system.

### Basic UDP communication

Run the script on both machines:

```bash
python3 port_demo.py
```

Use the local LAN endpoint printed by each process to configure the other process:

```text
/peer 192.168.1.20:45678
```

Use `/status` to display the local and remote endpoints, and `/quit` to exit.

### UDP session communication

Run the script on both machines:

```bash
python3 udp_demo.py
```

Configure a peer with:

```text
/peer 192.168.1.20:45678
```

This version adds HELLO/HELLO_ACK handshaking, heartbeat messages, round-trip timing, peer timeout detection, and graceful disconnect messages. Use `/status` for session details and `/quit` to disconnect.

## Notes

- Each demo binds to port `0`, so the operating system chooses an available ephemeral port at startup.
- Replace the example IP addresses with the actual LAN address of the other machine.
- TCP provides a connection-oriented byte stream; UDP sends independent datagrams and does not guarantee delivery.