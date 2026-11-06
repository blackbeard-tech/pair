# pair wire protocol (v1)

What two `pair` peers send each other. Any implementation (the Rust server here, a future Python one)
must follow this to interoperate.

## Transport

- [magic-wormhole](https://magic-wormhole.readthedocs.io/) mailbox protocol, relay
  `ws://relay.magic-wormhole.io:4000/v1`.
- App ID `blackbeard.tech/pair/v1`. Peers with a different app ID can't see each other.
- Code: nameplate number plus two words from the PGP word list, e.g. `7-amber-falcon`. SPAKE2 turns it into
  the session key. A wrong code fails the key exchange on both sides.
- App versions (exchanged by magic-wormhole after SPAKE2): `{"v": 1, "name": "<display name>"}`.
- After the key exchange every message is one magic-wormhole app message, encrypted per phase: a UTF-8 JSON
  object with a `t` field. Unknown `t` values must be ignored.

## Messages

| `t` | Sent by | Fields | Meaning |
|---|---|---|---|
| `hello` | joiner, first | `v` (1), `name` | Asks to pair. The initiator's owner approves or rejects. |
| `accept` | initiator | `name` | Approved. Both sides are now paired. |
| `reject` | initiator | | Declined. The joiner closes. |
| `msg` | either | `message`: an [A2A](https://a2a-protocol.org/) Message, `{"kind": "message", "role": "agent", "messageId", "parts": [{"kind": "text", "text"}]}` | Text for the other agent. Max 16 KiB of text. |
| `file` | either | `id`, `name`, `size`, `sha256` (hex), `seq` (0-based), `last` (bool), `data` (base64 chunk) | One chunk (8 KiB) of a file. Chunks of one `id` arrive in `seq` order. Max 5 MiB per file, 4 at once. |
| `file_ok` | receiver | `name` | The whole file arrived and matched `size` and `sha256`. |
| `ping` | either | | Heartbeat after 4 idle minutes; keeps the relay connection open. Ignored. Any message the relay does not acknowledge within 30 s ends the pairing. |
| `bye` | either | | Unpair. Both sides close. |

Before `accept`, everything except `hello` / `accept` / `reject` / `bye` is dropped.

## Sending files

Before sending, the sender's owner confirms in a dialog shown by their client (MCP elicitation).
Secret-looking paths are refused regardless.

## Receiving files

- The name is reduced to a safe basename (no paths, control or bidi characters, leading dots, or Windows
  reserved names) and never overwrites: a clash becomes `name (2).ext`.
- Saved owner-only under `<plugin data>/received/`, never executable, and deleted after 7 days.
- Size and sha256 must match before the file is saved; otherwise it's discarded and the owner told.
