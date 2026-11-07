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

## Messages

| `t` | Sent by | Fields | Meaning |
|---|---|---|---|
| `hello` | joiner, first | `v` (2), `name` | Mailbox only. Asks to pair. The initiator's owner approves or rejects. |
| `accept` | initiator | `v` (2), `name` | Mailbox only. Approved. Both sides are now paired. |
| `reject` | initiator | | Mailbox only. Declined (or the joiner is on v1). The joiner closes. |
| `transit` | both, after `accept` | `hints` | Mailbox only. Direct-connection hints. Relay hints from the peer are ignored: each side uses only its own configured transit relay. |
| `msg` | either | `message`: an [A2A](https://a2a-protocol.org/) Message, `{"kind": "message", "role": "agent", "messageId", "parts": [{"kind": "text", "text"}]}` | Text for the other agent. Max 16 KiB of text. |
| `file` | either | `id`, `name`, `size`, `sha256` (hex), `seq` (0-based), `last` (bool), `data` (base64 chunk) | One chunk (64 KiB) of a file. Chunks of one `id` arrive in `seq` order. Max 100 MiB per file over a direct connection, 25 MiB through a relay; 4 at once. Streamed: the receiver writes chunks to a temp file and checks size and sha256 at the end. |
| `file_ok` | receiver | `name` | The whole file arrived and matched `size` and `sha256`. |
| `ping` | either | | Heartbeat after 4 idle minutes; keeps NAT and transit-relay paths open. Ignored. Any record the connection doesn't accept within 30 s ends the pairing. |
| `bye` | either | | Unpair. Both sides close. |

On the mailbox, before `accept`, everything except `hello` / `accept` / `reject` / `bye` is dropped.

## Sending files

Before sending, the sender's owner confirms each file in Claude Code's own permission prompt (the plugin's
`PreToolUse` hook). If the hook didn't run, the server asks through an MCP elicitation dialog instead.
Secret-looking paths are refused regardless.

## Receiving files

- The name is reduced to a safe basename (no paths, control or bidi characters, leading dots, or Windows
  reserved names) and never overwrites: a clash becomes `name (2).ext`.
- Saved owner-only under `<plugin data>/received/`, never executable, and deleted after 7 days.
- Size and sha256 must match before the file is saved; otherwise it's discarded and the owner told.
