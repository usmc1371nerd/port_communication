# Home Port Application TODO

## Preserve Existing Teaching Demos

- [x] Keep `port_demo.py` unchanged.
- [x] Keep `tcp_demo.py` unchanged.
- [x] Keep `udp_demo.py` unchanged.
- [x] Preserve the existing README explanations for the three demos.

## New Application

- [x] Add one new file: `home_port.py`.
- [x] Do not split the new application into multiple Python modules.
- [x] Support explicit command-line modes:
  - [x] `python3 home_port.py host`
  - [x] `python3 home_port.py client`

## Communication Protocol

- [x] Implement persistent TCP communication.
- [x] Use length-prefixed JSON messages.
- [x] Define registration messages.
- [x] Define registration acknowledgement messages.
- [x] Define heartbeat and response messages.
- [x] Define application message types.
- [x] Define disconnect and error messages.
- [x] Reject malformed messages safely.
- [x] Limit maximum message/frame size.

## Host Mode

- [x] Listen on a configurable LAN address and port.
- [x] Accept multiple clients concurrently.
- [x] Generate a registry entry for each connected client.
- [x] Track each client's stable ID.
- [x] Track each client's display name.
- [x] Track the host-observed source IP and port.
- [x] Track the client-reported local IP and port as metadata.
- [x] Track connection state.
- [x] Track last-seen and heartbeat timestamps.
- [x] Provide a command to list registered clients.
- [x] Provide a command to select a client.
- [x] Provide a command to send a message to the selected client.
- [x] Provide a command to test optional endpoint reachability.
- [x] Provide a command to shut down cleanly.
- [x] Remove or mark clients when they disconnect or time out.

## Client Mode

- [x] Accept the host IP and port as configuration.
- [x] Accept a human-readable client name.
- [x] Generate a random stable client ID on first run.
- [x] Persist the client ID locally.
- [x] Register the client with the host.
- [x] Report the client-declared local IP and port.
- [x] Receive messages from the host.
- [x] Send messages to the host.
- [x] Send regular heartbeat messages.
- [x] Detect a lost host connection.
- [x] Reconnect with bounded backoff.
- [x] Shut down cleanly on `/quit` or keyboard interrupt.

## Endpoint Mapping Rules

- [x] Treat the host-observed TCP endpoint as authoritative for the active connection.
- [x] Store the client-reported endpoint for display and diagnostics.
- [x] Clearly label reported endpoints as informational.
- [x] Do not assume NAT traversal or firewall traversal.
- [x] Do not claim that a reported port is reachable from the host.
- [x] Keep direct callback testing optional and diagnostic only.

## Documentation

- [x] Add a `home_port.py` section to `README.md`.
- [x] Document host startup.
- [x] Document client startup.
- [x] Document host commands.
- [x] Document client commands.
- [x] Explain the automatic client registry.
- [x] Explain observed versus reported endpoints.
- [x] Document LAN firewall requirements.
- [x] Document reconnect and identity behavior.
- [x] Document current limitations.
- [x] Keep the non-malicious-use disclaimer.
- [x] State that the software must only be used on systems and networks owned or authorized by the user.

## Verification

- [x] Run `python3 -m py_compile home_port.py port_demo.py tcp_demo.py udp_demo.py`.
- [x] Start one host locally.
- [x] Start at least two clients locally.
- [x] Verify each client receives a distinct stable ID.
- [x] Verify the host registry lists both clients.
- [x] Verify names, observed addresses, reported endpoints, and last-seen times.
- [x] Test host-to-client messaging.
- [x] Test client-to-host messaging.
- [x] Test heartbeat updates.
- [x] Stop a client and verify disconnect cleanup.
- [x] Test heartbeat timeout handling.
- [x] Restart a client and verify its ID is retained.
- [x] Send malformed frames and verify the host stays running.
- [x] Send oversized frames and verify bounded handling.
- [x] Confirm the three original demo files were not modified.
- [x] Review README commands against the actual CLI.
- [x] Run `git status` and confirm only intended files changed.

## Future Security Work

- [ ] Add authentication before use beyond a trusted LAN.
- [ ] Add TLS before transmitting sensitive data.
- [ ] Consider an authenticated relay or reverse tunnel for clients behind NAT.
- [ ] Do not expose the host directly to the Internet without additional security controls.
