# Home Port Application TODO

## Preserve Existing Teaching Demos

- [ ] Keep `port_demo.py` unchanged.
- [ ] Keep `tcp_demo.py` unchanged.
- [ ] Keep `udp_demo.py` unchanged.
- [ ] Preserve the existing README explanations for the three demos.

## New Application

- [ ] Add one new file: `home_port.py`.
- [ ] Do not split the new application into multiple Python modules.
- [ ] Support explicit command-line modes:
  - [ ] `python3 home_port.py host`
  - [ ] `python3 home_port.py client`

## Communication Protocol

- [ ] Implement persistent TCP communication.
- [ ] Use length-prefixed JSON messages.
- [ ] Define registration messages.
- [ ] Define registration acknowledgement messages.
- [ ] Define heartbeat and response messages.
- [ ] Define application message types.
- [ ] Define disconnect and error messages.
- [ ] Reject malformed messages safely.
- [ ] Limit maximum message/frame size.

## Host Mode

- [ ] Listen on a configurable LAN address and port.
- [ ] Accept multiple clients concurrently.
- [ ] Generate a registry entry for each connected client.
- [ ] Track each client's stable ID.
- [ ] Track each client's display name.
- [ ] Track the host-observed source IP and port.
- [ ] Track the client-reported local IP and port as metadata.
- [ ] Track connection state.
- [ ] Track last-seen and heartbeat timestamps.
- [ ] Provide a command to list registered clients.
- [ ] Provide a command to select a client.
- [ ] Provide a command to send a message to the selected client.
- [ ] Provide a command to test optional endpoint reachability.
- [ ] Provide a command to shut down cleanly.
- [ ] Remove or mark clients when they disconnect or time out.

## Client Mode

- [ ] Accept the host IP and port as configuration.
- [ ] Accept a human-readable client name.
- [ ] Generate a random stable client ID on first run.
- [ ] Persist the client ID locally.
- [ ] Register the client with the host.
- [ ] Report the client-declared local IP and port.
- [ ] Receive messages from the host.
- [ ] Send messages to the host.
- [ ] Send regular heartbeat messages.
- [ ] Detect a lost host connection.
- [ ] Reconnect with bounded backoff.
- [ ] Shut down cleanly on `/quit` or keyboard interrupt.

## Endpoint Mapping Rules

- [ ] Treat the host-observed TCP endpoint as authoritative for the active connection.
- [ ] Store the client-reported endpoint for display and diagnostics.
- [ ] Clearly label reported endpoints as informational.
- [ ] Do not assume NAT traversal or firewall traversal.
- [ ] Do not claim that a reported port is reachable from the host.
- [ ] Keep direct callback testing optional and diagnostic only.

## Documentation

- [ ] Add a `home_port.py` section to `README.md`.
- [ ] Document host startup.
- [ ] Document client startup.
- [ ] Document host commands.
- [ ] Document client commands.
- [ ] Explain the automatic client registry.
- [ ] Explain observed versus reported endpoints.
- [ ] Document LAN firewall requirements.
- [ ] Document reconnect and identity behavior.
- [ ] Document current limitations.
- [ ] Keep the non-malicious-use disclaimer.
- [ ] State that the software must only be used on systems and networks owned or authorized by the user.

## Verification

- [ ] Run `python3 -m py_compile home_port.py port_demo.py tcp_demo.py udp_demo.py`.
- [ ] Start one host locally.
- [ ] Start at least two clients locally.
- [ ] Verify each client receives a distinct stable ID.
- [ ] Verify the host registry lists both clients.
- [ ] Verify names, observed addresses, reported endpoints, and last-seen times.
- [ ] Test host-to-client messaging.
- [ ] Test client-to-host messaging.
- [ ] Test heartbeat updates.
- [ ] Stop a client and verify disconnect cleanup.
- [ ] Test heartbeat timeout handling.
- [ ] Restart a client and verify its ID is retained.
- [ ] Send malformed frames and verify the host stays running.
- [ ] Send oversized frames and verify bounded handling.
- [ ] Confirm the three original demo files were not modified.
- [ ] Review README commands against the actual CLI.
- [ ] Run `git status` and confirm only intended files changed.

## Future Security Work

- [ ] Add authentication before use beyond a trusted LAN.
- [ ] Add TLS before transmitting sensitive data.
- [ ] Consider an authenticated relay or reverse tunnel for clients behind NAT.
- [ ] Do not expose the host directly to the Internet without additional security controls.
