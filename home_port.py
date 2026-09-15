"""Trusted-LAN host/client messaging. Standard library only; no authentication or TLS."""

import argparse
import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import math
from pathlib import Path
import queue
import struct
import sys
import threading
import time
import uuid

MAX_FRAME = 65536
IO_TIMEOUT = 5


class ProtocolError(ValueError):
    pass


def log(message):
    # Escape control characters supplied by peers before printing to a terminal.
    print(str(message).encode('unicode_escape').decode('ascii'), flush=True)


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def validate(message):
    if not isinstance(message, dict):
        raise ProtocolError('Message must be an object')
    kind = message.get('type')
    if not isinstance(kind, str) or kind not in {
        'register', 'registered', 'heartbeat', 'heartbeat_ack',
        'message', 'disconnect', 'error',
    }:
        raise ProtocolError('Unknown message type')
    if kind in {'register', 'registered'}:
        try:
            if str(uuid.UUID(message['id'])) != message['id']:
                raise ValueError()
        except (KeyError, ValueError, TypeError, AttributeError):
            raise ProtocolError('Invalid client ID') from None
    if kind == 'register':
        name = message.get('name')
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise ProtocolError('Name must contain 1–100 characters')
        endpoint = message.get('endpoint')
        if not isinstance(endpoint, dict):
            raise ProtocolError('Missing reported endpoint')
        try:
            if not isinstance(endpoint['ip'], str):
                raise ValueError()
            ipaddress.ip_address(endpoint['ip'])
            port = endpoint['port']
            if type(port) is not int or not 1 <= port <= 65535:
                raise ValueError()
        except (KeyError, ValueError, TypeError):
            raise ProtocolError('Invalid reported endpoint') from None
    if kind in {'message', 'error', 'disconnect'}:
        if not isinstance(message.get('text'), str):
            raise ProtocolError('Missing text')
    if kind in {'heartbeat', 'heartbeat_ack'}:
        if type(message.get('seq')) is not int or not 0 <= message['seq'] < 2**63:
            raise ProtocolError('Invalid heartbeat sequence')
    if kind == 'registered':
        for field in ('heartbeat', 'timeout'):
            value = message.get(field)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ProtocolError('Invalid heartbeat settings')
        if message['timeout'] <= message['heartbeat']:
            raise ProtocolError('Timeout must exceed heartbeat interval')
    return message


async def receive(reader, timeout):
    async def frame():
        size = struct.unpack('!I', await reader.readexactly(4))[0]
        if not 0 < size <= MAX_FRAME:
            raise ProtocolError('Frame size must be 1–65536 bytes')
        try:
            message = json.loads(await reader.readexactly(size))
        except (ValueError, UnicodeError, RecursionError):
            raise ProtocolError('Invalid JSON') from None
        return validate(message)
    return await asyncio.wait_for(frame(), timeout)


async def send(writer, kind, **fields):
    payload = json.dumps(validate(dict(type=kind, **fields)), ensure_ascii=True).encode()
    if len(payload) > MAX_FRAME:
        raise ProtocolError('Message exceeds 65536 bytes')
    writer.write(struct.pack('!I', len(payload)) + payload)
    await asyncio.wait_for(writer.drain(), IO_TIMEOUT)


async def close(writer):
    writer.close()
    with contextlib.suppress(OSError, asyncio.TimeoutError):
        await asyncio.wait_for(writer.wait_closed(), IO_TIMEOUT)


async def goodbye(writer, kind, text):
    with contextlib.suppress(OSError, asyncio.TimeoutError, ProtocolError):
        await send(writer, kind, text=text)


async def console(callback):
    lines = queue.Queue()

    def read_input():
        for line in sys.stdin:
            lines.put(line.rstrip('\n'))
        lines.put('/quit')

    threading.Thread(target=read_input, daemon=True).start()
    while True:
        try:
            line = lines.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.05)
            continue
        if line.strip() == '/quit':
            return
        try:
            await callback(line)
        except (ValueError, OSError, asyncio.TimeoutError) as exc:
            log(f'Command failed: {exc}')


@dataclass
class ClientEntry:
    id: str
    name: str
    observed: tuple
    reported: dict
    writer: asyncio.StreamWriter
    last_seen: str
    last_heartbeat: str = '-'
    state: str = 'connected'


class Host:
    def __init__(self, args):
        self.args = args
        self.clients = {}
        self.selected = None
        self.tasks = set()

    async def connection(self, reader, writer):
        task = asyncio.current_task()
        self.tasks.add(task)
        entry = None
        try:
            message = await receive(reader, IO_TIMEOUT)
            if message['type'] != 'register':
                raise ProtocolError('Register first')
            if message['id'] in self.clients:
                raise ProtocolError('Client ID already connected; use a separate identity file')
            entry = ClientEntry(message['id'], message['name'], writer.get_extra_info('peername'),
                                message['endpoint'], writer, stamp())
            self.clients[entry.id] = entry
            await send(writer, 'registered', id=entry.id, heartbeat=self.args.heartbeat,
                       timeout=self.args.timeout)
            log(f'Registered {entry.name} {entry.id} observed={entry.observed}')
            heartbeat_deadline = time.monotonic() + self.args.timeout
            while True:
                message = await receive(reader, max(0.001, heartbeat_deadline - time.monotonic()))
                entry.last_seen = stamp()
                kind = message['type']
                if kind == 'heartbeat':
                    entry.last_heartbeat = entry.last_seen
                    heartbeat_deadline = time.monotonic() + self.args.timeout
                    await send(writer, 'heartbeat_ack', seq=message['seq'])
                elif kind == 'message':
                    log(f'{entry.name} ({entry.id}): {message["text"]}')
                elif kind == 'disconnect':
                    break
                else:
                    raise ProtocolError('Unexpected message after registration')
        except ProtocolError as exc:
            log(f'Protocol rejected: {exc}')
            await goodbye(writer, 'error', str(exc))
        except asyncio.TimeoutError:
            log(f'Timeout: {entry.id if entry else "unregistered connection"}')
        except (OSError, asyncio.IncompleteReadError) as exc:
            log(f'Connection closed: {type(exc).__name__}')
        finally:
            if entry is not None:
                entry.state = 'disconnected'
                self.clients.pop(entry.id, None)
                if self.selected == entry.id:
                    self.selected = None
                log(f'Removed {entry.id}')
            await close(writer)
            self.tasks.discard(task)

    async def command(self, line):
        command, _, argument = line.partition(' ')
        if command == '/list':
            log(f'Clients: {len(self.clients)}')
            for entry in list(self.clients.values()):
                log(f'{entry.id} name={entry.name} state={entry.state} observed={entry.observed} '
                    f'reported(informational)={entry.reported} last_seen={entry.last_seen} '
                    f'last_heartbeat={entry.last_heartbeat}')
        elif command == '/select':
            if argument not in self.clients:
                raise ValueError('Use a full connected client ID from /list')
            self.selected = argument
            log(f'Selected {argument}')
        elif command in {'/send', '/probe'}:
            entry = self.clients.get(self.selected)
            if entry is None:
                raise ValueError('Select a connected client first')
            if command == '/send':
                if not argument:
                    raise ValueError('Usage: /send TEXT')
                await send(entry.writer, 'message', text=argument)
                log(f'Sent to {entry.id}')
            else:
                # Require a port explicitly: never assume the reported ephemeral port listens.
                port = int(argument)
                if not 1 <= port <= 65535:
                    raise ValueError('Usage: /probe PORT (1–65535)')
                ip = entry.observed[0]
                log(f'Diagnostic TCP probe to observed IP {ip}, explicit port {port}')
                _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), IO_TIMEOUT)
                await close(writer)
                log('TCP connection succeeded; this does not verify an application or identity')
        elif line:
            log('Commands: /list, /select ID, /send TEXT, /probe PORT, /quit')

    async def run(self):
        server = await asyncio.start_server(self.connection, self.args.bind, self.args.port)
        log(f'Listening on {server.sockets[0].getsockname()}')
        log('Commands: /list, /select ID, /send TEXT, /probe PORT, /quit')
        try:
            await console(self.command)
        finally:
            server.close()
            await asyncio.gather(*(goodbye(e.writer, 'disconnect', 'Host shutting down')
                                   for e in list(self.clients.values())))
            tasks = list(self.tasks)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await server.wait_closed()
            log('Host stopped')


def identity(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x', encoding='utf-8') as file:
            value = str(uuid.uuid4())
            file.write(value + '\n')
    except FileExistsError:
        value = path.read_text(encoding='utf-8').strip()
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError()
    except ValueError:
        raise ValueError(f'Invalid identity file: {path}; choose a new --identity path') from None
    return value


class Client:
    def __init__(self, args):
        self.args = args
        self.id = identity(args.identity)
        self.writer = None

    async def command(self, line):
        if line == '/status':
            log(f'id={self.id} name={self.args.name} connected={self.writer is not None} '
                f'host={self.args.host}:{self.args.port} identity={self.args.identity}')
        elif line:
            if line.startswith('/') and not line.startswith('/send '):
                log('Commands: /status, /send TEXT (or plain text), /quit')
                return
            if self.writer is None:
                raise ValueError('Disconnected; messages are not queued')
            await send(self.writer, 'message', text=line[6:] if line.startswith('/send ') else line)
            log('Sent to host')

    async def session(self, reader, writer, ack):
        interval, timeout = ack['heartbeat'], ack['timeout']
        pending = {}

        async def heartbeat():
            seq = 0
            while True:
                if pending and time.monotonic() - min(pending.values()) >= timeout:
                    raise asyncio.TimeoutError('Heartbeat response overdue')
                pending[seq] = time.monotonic()
                await send(writer, 'heartbeat', seq=seq)
                seq += 1
                await asyncio.sleep(interval)

        async def listen():
            while True:
                message = await receive(reader, timeout)
                kind = message['type']
                if kind == 'heartbeat_ack':
                    if message['seq'] not in pending:
                        raise ProtocolError('Unexpected heartbeat acknowledgement')
                    pending.pop(message['seq'])
                elif kind == 'message':
                    log(f'Host: {message["text"]}')
                elif kind in {'disconnect', 'error'}:
                    log(f'Host {kind}: {message["text"]}')
                    return
                else:
                    raise ProtocolError('Unexpected host message')

        tasks = [asyncio.create_task(heartbeat()), asyncio.create_task(listen())]
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def connect(self):
        delay = 1
        while True:
            writer = None
            connected_at = None
            try:
                log(f'Connecting to {self.args.host}:{self.args.port}')
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.args.host, self.args.port), IO_TIMEOUT)
                local = writer.get_extra_info('sockname')
                await send(writer, 'register', id=self.id, name=self.args.name,
                           endpoint={'ip': local[0], 'port': local[1]})
                ack = await receive(reader, IO_TIMEOUT)
                if ack['type'] != 'registered' or ack['id'] != self.id:
                    raise ProtocolError(ack.get('text', 'Invalid registration acknowledgement'))
                self.writer = writer
                connected_at = time.monotonic()
                log(f'Connected as {self.id}; local endpoint (informational)={local}')
                await self.session(reader, writer, ack)
            except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError, ProtocolError) as exc:
                log(f'Connection lost/unavailable: {type(exc).__name__}: {exc}')
            finally:
                self.writer = None
                if writer is not None:
                    await goodbye(writer, 'disconnect', 'Client disconnecting')
                    await close(writer)
            if connected_at is not None and time.monotonic() - connected_at >= 30:
                delay = 1
            log(f'Reconnecting in {delay}s')
            await asyncio.sleep(delay)
            delay = min(delay * 2, self.args.reconnect_max)

    async def run(self):
        log(f'Client ID: {self.id}; identity file: {self.args.identity}')
        log('Commands: /status, /send TEXT (or plain text), /quit')
        task = asyncio.create_task(self.connect())
        try:
            await console(self.command)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            log('Client stopped')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    host = modes.add_parser('host', help='Accept and manage LAN clients')
    host.add_argument('--bind', default='0.0.0.0')
    host.add_argument('--port', type=int, default=8765)
    host.add_argument('--heartbeat', type=float, default=5)
    host.add_argument('--timeout', type=float, default=20)
    client = modes.add_parser('client', help='Connect to a host')
    client.add_argument('--host', default='127.0.0.1')
    client.add_argument('--port', type=int, default=8765)
    client.add_argument('--name', default='client')
    client.add_argument('--identity', type=Path)
    client.add_argument('--reconnect-max', type=float, default=30)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535 or (args.mode == 'client' and args.port == 0):
        parser.error('Port must be 1–65535 (host also accepts 0 for automatic allocation)')
    if args.mode == 'host':
        if not all(math.isfinite(v) for v in (args.heartbeat, args.timeout)) or not 0 < args.heartbeat < args.timeout:
            parser.error('Require finite 0 < heartbeat < timeout')
    else:
        if not args.name.strip() or len(args.name) > 100:
            parser.error('Name must contain 1–100 characters')
        if not math.isfinite(args.reconnect_max) or args.reconnect_max < 1:
            parser.error('Reconnect maximum must be finite and at least 1 second')
        if args.identity is None:
            key = hashlib.sha256(args.name.encode()).hexdigest()[:16]
            args.identity = Path.home() / '.home_port' / f'{key}.id'
    try:
        asyncio.run((Host(args) if args.mode == 'host' else Client(args)).run())
    except KeyboardInterrupt:
        log('Stopped')
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
