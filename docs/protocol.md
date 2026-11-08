# pair wire protocol (v2)

What two `pair` peers send each other. Any implementation (the Rust server here, a future Python one)
must follow this to interoperate. The protocol version is `v` in the app versions and in `hello` /
`accept`; the app ID stays `blackbeard.tech/pair/v1`.

## Transport

Like the magic-wormhole CLI, the relay's mailbox is used only to set up; the conversation runs over **transit**.

1. **Mailbox** (`ws://relay.magic-wormhole.io:4000/v1`, app ID `blackbeard.tech/pair/v1`): the code (nameplate +
   two PGP words) runs SPAKE2 to agree a key; a wrong code fails on both sides. App versions:
   `{"v": 2, "name": "<display name>"}`. Then `hello` / `accept` (or `reject`), then each side sends
   `{"t": "transit", "hints": <magic-wormhole transit hints>}`.
2. **Transit**: magic-wormhole transit (`direct-tcp-v1` when the machines can reach each other, otherwise the transit
   relay `tcp://transit.magic-wormhole.io:4001`). The initiator is the Leader, the joiner the Follower. Key:
   the pairing key's subkey for purpose `"{app id}/transit-key"`, as magic-wormhole derives it. Records are
   encrypted and length-prefixed by transit itself.
3. **The mailbox is closed** as soon as transit is up. Everything below `accept` travels as transit records:
   one UTF-8 JSON object with a `t` field per record. Unknown `t` values must be ignored.

If the other side is on protocol v1 (pair 0.1.8 or older), pairing stops and the user is told to ask them to
update, rather than left waiting.

**Your own servers:** set `PAIR_RELAY` (mailbox URL, default `ws://relay.magic-wormhole.io:4000/v1`) and
`PAIR_TRANSIT_RELAY` (default `tcp://transit.magic-wormhole.io:4001`) in the environment Claude Code starts in.
Both sides must use the same mailbox. Only `ws://` and `tcp://` work for now; `wss://` (TLS) is not supported yet.

## Messages

| `t` | Sent by | Fields | Meaning |
|---|---|---|---|
| `hello` | joiner, first | `v` (2), `name`, `resume` (true, 0.1.11+) | Mailbox only. Asks to pair. The initiator's owner approves or rejects. |
| `accept` | initiator | `v` (2), `name`, `resume` (true, 0.1.11+) | Mailbox only. Approved. Both sides are now paired. |
| `reject` | initiator | | Mailbox only. Declined (or the joiner is on v1). The joiner closes. |
| `transit` | both, after `accept` | `hints` | Mailbox only. Direct-connection hints. Relay hints from the peer are ignored: each side uses only its own configured transit relay. |
| `msg` | either | `message`: an [A2A](https://a2a-protocol.org/) Message, `{"kind": "message", "role": "agent", "messageId", "parts": [{"kind": "text", "text"}]}` | Text for the other agent. Max 16 KiB of text. |
| `file` | either | `id`, `name`, `size`, `sha256` (hex), `seq` (0-based), `last` (bool), `data` (base64 chunk) | One chunk (64 KiB) of a file. Chunks of one `id` arrive in `seq` order. Max 100 MiB per file over a direct connection, 25 MiB through a relay; 4 at once. Streamed: the receiver writes chunks to a temp file and checks size and sha256 at the end. |
| `file_ok` | receiver | `name` | The whole file arrived and matched `size` and `sha256`. |
| `ping` | either | | Heartbeat: every 30 s when both sides sent `resume`, otherwise every 4 minutes. Keeps NAT and transit-relay paths open; ignored on receipt. With `resume`, a peer silent for 95 s counts as dropped. Any record the connection doesn't accept within 30 s counts as dropped. |
| `bye` | either | | Unpair. Both sides close. Also sent when the Claude Code session closes. |

On the mailbox, before `accept`, everything except `hello` / `accept` / `reject` / `bye` is dropped.

## Reconnecting

When both sides sent `resume: true`, a dropped transit connection (error, EOF, a send not accepted within 30 s,
or 95 s of silence) is reconnected instead of ending the pairing:

1. Before closing the mailbox after `accept`, both sides derive `R` = the pairing key's subkey for purpose
   `"blackbeard.tech/pair/resume"`. It stays in memory only.
2. Time is cut into 30 s slots (`slot = unix seconds / 30`). For a slot, the code is
   `"9" + 24 digits` (the first 16 bytes of R's subkey `"nameplate/{slot}"` as a big-endian integer, mod 10^24)
   + `-` + the hex of R's subkey `"password/{slot}"`. Both sides compute it without talking. The relay sees
   only the nameplate, which is unlinkable to the pairing and to the password.
3. Each side claims that nameplate on the mailbox (allocating it if absent), runs SPAKE2 with the code, and if
   it completes, swaps transit hints and opens transit as at first. No new approval: only the two original
   processes know R. Display names and trust levels carry over.
4. If the peer doesn't turn up by the end of the slot plus 5 s (clock skew allowance), or any step fails, the side
   tries the next slot. A slot's code is never used twice. After 10 minutes, the pairing ends.

Messages the user sends while reconnecting are queued and go out on the new connection. A file being sent or
received when the connection dropped is abandoned, and both owners are told. Records in flight at the moment of
the drop can be lost.

## Sending files

Before sending, the sender's owner confirms each file in Claude Code's own confirmation dialog (`send_file` is
marked `anthropic/requiresUserInteraction`). In clients that ignore that flag, the server asks through an MCP
elicitation dialog instead.
Secret-looking paths are refused regardless.

## Receiving files

- The name is reduced to a safe basename (no paths, control or bidi characters, leading dots, or Windows
  reserved names) and never overwrites: a clash becomes `name (2).ext`.
- Saved owner-only under `<plugin data>/received/`, never executable, and deleted after 7 days.
- Size and sha256 must match before the file is saved; otherwise it's discarded and the owner told.
