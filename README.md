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

## Home Port application

`home_port.py` adds a multi-client TCP host and client while keeping the three
teaching demos unchanged. It uses only Python's standard library (Python 3.10+).
Use it only on systems and networks you own or are authorized to use, on a trusted
LAN. It currently has **no authentication, encryption, or message integrity protection**.
Client IDs are labels, not proof of identity.

### Start the host

```bash
python3 home_port.py host --bind 0.0.0.0 --port 8765
```

The defaults are all local interfaces and port `8765`. For local-only testing,
use `--bind 127.0.0.1`. Use `--port 0` to request an available port, then give
clients the displayed port. Clients must use the host's actual LAN IP, not `0.0.0.0`.
Allow inbound TCP on the selected port in the host's firewall.

### Start clients

On each participating machine, use the host's LAN address:

```bash
python3 home_port.py client --host 192.168.1.20 --port 8765 --name laptop
python3 home_port.py client --host 192.168.1.20 --port 8765 --name desktop
```

For a test on one machine, run the host and both clients in separate terminals
and use `--host 127.0.0.1`. Without options, client mode connects to
`127.0.0.1:8765` with the name `client`.

A random UUID is generated on first use and stored in
`~/.home_port/<name-hash>.id`. The same name and file retain that identity across
restarts. Different names on the same machine get different files. To rename a
client while retaining its ID, or run multiple clients with the same display name,
specify an identity file explicitly:

```bash
python3 home_port.py client --host 192.168.1.20 --name laptop --identity ./laptop.id
```

Use a different identity file for each independent client. The host rejects a
second active connection claiming an already-connected ID. Invalid identity files
produce an error; they are not silently overwritten.

### Host commands

| Command | Action |
| --- | --- |
| `/list` | List connected IDs, names, state, endpoints, last-seen and last-heartbeat UTC timestamps. |
| `/select ID` | Select a client using its full UUID from `/list`. |
| `/send TEXT` | Send text to the selected client. |
| `/probe PORT` | Attempt a TCP connection to the selected client's observed IP and an explicitly supplied port. |
| `/quit` | Notify clients and stop the host. |

The registry is populated automatically during registration. Disconnected or
timed-out clients are removed, and a disconnected selection is cleared. The
registry is in memory; it is rebuilt as clients reconnect after host restart.

### Client commands

| Command | Action |
| --- | --- |
| `/status` | Show identity, name, connection state, host, and identity-file path. |
| `/send TEXT` or plain text | Send text to the host. |
| `/quit` | Disconnect and exit. |

Keyboard interrupt also shuts down either mode. Closing standard input exits the
process, so keep input open when running through a pipe or process supervisor.

### Connection behavior and endpoints

The **observed endpoint** is the source IP and port seen by the host on the active
TCP connection. It is authoritative for that connection. The **reported endpoint**
is the client's local socket address, supplied during registration and shown only
as informational metadata. Messages travel over the existing connection.

Neither endpoint implies a listening service or a reachable callback port. The
optional `/probe PORT` command tests only whether a TCP connection can be opened
at the observed IP on the port you explicitly specify. A separate listening
service and firewall permission are needed; Home Port clients do not open callback
listeners. Probing does not verify the service or the client's identity. There is
no NAT traversal, firewall traversal, or automatic port forwarding.

The host requests heartbeats every 5 seconds and removes clients after 20 seconds
without a heartbeat. Configure these with host options `--heartbeat SECONDS` and
`--timeout SECONDS` (timeout must exceed the heartbeat interval). Clients detect
missing responses and reconnect with exponential delays starting at 1 second,
capped by `--reconnect-max SECONDS` (default 30). After a connection lasts at least
30 seconds, retry delays reset. A reconnect registers the same saved ID with its
new endpoint. Messages sent while disconnected are rejected, not queued.

### Protocol and limitations

Each message is a four-byte unsigned big-endian length followed by a JSON object,
with a maximum JSON payload of 65,536 bytes. Message types are `register`,
`registered`, `heartbeat`, `heartbeat_ack`, `message`, `disconnect`, and `error`.
Registration includes `id`, `name`, and an `endpoint` object with `ip` and `port`.
The acknowledgement includes `id`, `heartbeat`, and `timeout`. Heartbeats and
responses carry an integer `seq`; application messages, disconnects, and errors
carry `text`. Registration has a five-second deadline; subsequent host reads are
bounded by the heartbeat deadline. Invalid frames or unexpected messages close
that connection. Text output escapes control characters before displaying peer data.

This is an interactive LAN application, not a production server. There is no
persistent message history, delivery acknowledgement, offline queue, or global
client-count limit. IDs and reported metadata can be impersonated by a network
peer. Add authentication before expanding beyond a trusted LAN, and TLS before
sending sensitive data. Do not expose the host directly to the Internet without
additional security controls. An authenticated relay or reverse tunnel is future
work for clients behind NAT.

Use `python3 home_port.py host --help` or `python3 home_port.py client --help`
for all options.
