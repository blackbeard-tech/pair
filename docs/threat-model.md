# pair: threat model (pilot, P1)

Status: draft for IT/Security review, 2026-11-05. Owner: Blackbeard Technologies.

## Scope

P1 pilot only: two people, Claude Code to Claude Code, pairing for the length of one session,
using the public magic-wormhole relay (`relay.magic-wormhole.io`). The self-hosted relay (P2),
other agent tools (P3) and remembered peers are out of scope.

## How it works

1. Owner A runs `/pair:pair`. A's local `pair` binary (an MCP server started by Claude Code)
   connects to the relay and gets a code such as `7-amber-falcon`: a nameplate number and two words.
2. A tells B the code out of band (chat, voice). B runs `/pair:pair 7-amber-falcon`.
3. Both binaries run SPAKE2 through the relay. If the codes match, both derive the same key K.
   If they don't match, both sides fail and the code is burned.
4. B sends an encrypted hello (display name). A's owner approves or rejects in their own session (Claude Code's own confirmation dialog for `pair_accept`, which no mode skips).
   Nothing else is exchanged until A approves.
5. The two Claude sessions exchange messages, encrypted with keys derived from K.
6. Saying "unpair" (the `unpair` tool) or closing either session ends the pairing. A dropped connection reconnects by
   itself for up to 10 minutes on a code both sides derive from K (see docs/protocol.md, Reconnecting), then ends.
   K exists only in memory.

## Assets

| Asset | Where it lives |
|---|---|
| Session context (code, files read, conversation) | Each owner's Claude Code session |
| Local tools (file write, shell, web, MCP) | Each owner's machine |
| Message content | In transit between the two binaries |
| Pairing code and key K | In the binaries' memory; the code is also wherever it was shared |

## Who can see what

| Party | Can see | Cannot see |
|---|---|---|
| Mailbox relay operator | Both IP addresses, timing of setup, app ID, nameplate, mailbox ID | Message content, K, the code words |
| Transit relay operator (only when the machines can't connect directly) | Both IP addresses, timing, message and file sizes | Message content, K |
| Network observer (P1 uses plaintext `ws://` on port 4000) | The same metadata as the relay | Message content |
| Paired peer | Whatever your Claude sends them | Your files, tools or session, except through your Claude's replies |
| Someone who overhears the code | Nothing, unless they redeem it before B does (see T1) | |

## Threats and mitigations

| # | Threat | Mitigation | Remaining risk |
|---|---|---|---|
| T1 | **Code guessing or interception.** An attacker redeems the code before B does. | SPAKE2 gives one online guess per code (2 words ≈ 16 bits, 1 in 65,536). A wrong guess fails both sides and burns the code (tested). An intercepted code still needs A's approval, and the approval prompt shows the joiner's name. | If the code leaks and the attacker gets in first, A could approve them by mistake. Codes are single-use; the ~2-minute expiry is enforced by our client (not yet covered by a test). |
| T2 | **Relay reads or alters messages.** | Messages are encrypted and authenticated (NaCl secretbox) with keys only the two peers hold. The relay can't run a man-in-the-middle attack without knowing the code (that's what SPAKE2 guarantees). | Metadata is exposed (see table). The relay can delay or drop messages. |
| T3 | **Prompt injection from the peer.** Peer messages try to make your Claude act against you. | Inbound messages are marked as untrusted requests from the named peer, never as instructions from the owner. Claude Code delivers them as harness notices (hook output inside a `<system-reminder>`, or a "Monitor event"), which its system prompt says don't come from the user, and it records them with a non-user origin. In a 2026-11-08 test (auto mode, Sonnet), Claude declined peer requests to run a command that it ran at once when the user typed the same request. The owner picks a trust level when pairing: **read-only** (default; for peer requests, answer and read, ask before anything else), **ask** (ask before any action a peer requests) or **normal**. The server instructions and each message carry it to Claude as guidance for peer-requested actions. Since 0.1.12 pair no longer enforces it with a PreToolUse hook: the hook couldn't tell the owner's requests from a peer's, so it asked about the owner's own work too (GitHub #5). Tool calls follow the owner's permission mode, as they do for any other untrusted content such as a fetched web page. | Claude's judgement and the owner's permission mode are the defence; pair adds no gate of its own, except that with the pair pane's "Hand messages to Claude automatically" option off (default on), the peer's messages and files reach Claude only when the owner hands one over, framed as the peer's request. The pane refreshes that choice every 10 s and the server treats an older one as on, so a switched-off mod never hides messages. Accepting a pairing and sending a file still need the owner's yes in Claude Code's own dialog (T11). Not tested: whether auto mode's classifier blocks a peer-requested action that Claude does attempt. |
| T4 | **Peer approves your tool use.** | `pair` declares no channel at all (and never the channel permission-relay capability), so approvals always stay with the local owner. A unit test checks this (`never_declares_permission_relay`). | None identified. |
| T5 | **Data leaving the machine.** Your Claude includes secrets or confidential code in a reply. | The owner sees every outbound message in their session. The pilot runs on non-sensitive work only until this review signs off. | Accepted for the pilot: no outbound filter (owner decision, 2026-11-05). Secret scanning and PII redaction are candidates for a later paid tier. |
| T6 | **Peer crashes your client.** | magic-wormhole 0.8.1 panics on a message with a non-numeric phase label. Guarded: each pairing runs on its own thread inside `catch_unwind`, so such a message ends that pairing ("the peer sent malformed data") and the server keeps running. | Denial of service of that pairing only; data is not exposed. The guard has not yet been exercised with a crafted message (no test peer can send one through the library's API). |
| T7 | **Compromised binary or dependency.** | Locked dependencies, cargo-deny (advisories, licences, sources), osv-scanner, CodeQL, build provenance on releases, and a checksum check before first run. | macOS binaries are signed (Developer ID) and notarized; Windows and Linux binaries are unsigned (the checksum check still applies). |
| T8 | **Relay blocked, unavailable or stalling.** | Pairing fails cleanly with a message. Since 0.1.9 the relay mailbox only carries the setup (as in the magic-wormhole CLI); messages and files go over transit, directly between the machines when possible. Measured before: the mailbox intermittently stalled under message traffic (about 1 in 12 test runs); after: no stalls in about 110 large messages over transit, the one failure in 15 runs being during setup. Any send not acknowledged within 30 s, or (from 0.1.11) 95 s without hearing from the peer, counts as a dropped connection: both users are told, and pair reconnects by itself for up to 10 minutes. A file that stops arriving for 45 s is discarded with a notice, so stalls are never silent. | Corporate firewalls may block `ws://` on port 4000. A self-hosted `wss://` relay on port 443 is the fix (P2, possibly brought forward). |
| T9 | **Stale or dropped pairing.** | Pairing is session-scoped. Nothing is persisted, and K is discarded on unpair or exit. A heartbeat every 30 s (4 minutes with peers before 0.1.11) keeps NAT and relay paths open; the spike saw drops between 5 and 15 idle minutes without one. Closing a session sends `bye`, so the peer ends at once. A dropped connection, or (from 0.1.14) a first connection that fails after approval, reconnects for up to 10 minutes on a per-slot code derived from K: a 256-bit password through SPAKE2, so the relay or anyone else can't take over the pairing, and the nameplate the relay sees is unlinkable to the pairing. Only the two original processes hold K, so no new approval is asked. | Reconnecting doesn't survive a Claude Code restart (K is in memory only; pair-4kp scope B). A relay operator who blocks the reconnect code ends the pairing, as it could anyway. Reconnecting needs the two clocks within about 30 s. Records in flight at the moment of a drop can be lost. |
| T10 | **Peer text at rest.** Every event is written to a per-session inbox file, which the plugin monitor or hooks read. | The file lives under the plugin data dir, keyed by Claude Code session ID, created owner-only (0600 on macOS and Linux). It is deleted when the session ends; leftovers older than a day are swept on the next start. | Readable by other processes running as the same user while the session is open. A crash can leave it for up to a day. |
| T11 | **Files.** A peer asks your Claude to send a secret file, or sends you a harmful one. | Sending: since 0.1.11 `send_file` (like `pair_accept`) is marked `anthropic/requiresUserInteraction`, so Claude Code shows its own confirmation dialog for every file in every mode (even when the tool is pre-approved, in auto and bypass mode, and on Remote Control without one-tap approval), with no "don't ask again", and refuses in dontAsk. It doesn't depend on hooks. With other clients, or Claude Code versions that may predate the flag, the server asks through an MCP dialog; an app that declines that dialog without showing it is reported as "couldn't ask", never as the user declining. Claude is also told never to send a file just because the peer asked, and the server refuses secret-looking paths (`.ssh`, `.env*`, keys, credentials, `~/.claude`) even if approved. Max 100 MB directly, 25 MB through the transit relay; streamed, never held whole in memory. Receiving: saved under a sanitised name in a quarantine folder (owner-only, never executable, deleted after 7 days), size and sha256 verified, and Claude is told the contents are untrusted. | A user can still approve sending something sensitive that the denylist doesn't recognise. A received file could be opened or run later by hand. The pair pane's Open does what a double-click does, except for types that run when opened (scripts, apps, installers), which it shows in their folder instead; that list is best effort. |
| T12 | **IP addresses shared with the peer.** | Transit tries a direct connection first, so each side learns the other's local and public IP addresses (and a peer's machine may be reachable on the listening port while paired). | Acceptable between colleagues; a relay-only mode (magic-wormhole `FORCE_RELAYED`) could be offered for privacy. |
| T13 | **Peer-chosen connection addresses.** A peer's transit hints decide which addresses our side connects to, including addresses inside your network. | Relays the peer names are ignored (only our configured transit relay is used). Direct connections carry only the transit handshake, which fails unless the other end knows the pairing key, so no data goes to a wrong address. | A peer could make your machine attempt TCP connections to LAN addresses (a probe, not data exposure). Filtering private-range hints from peers, or a relay-only mode, is tracked as `pair-630.9`. |
| T14 | **Third-party STUN lookup.** For direct connections, magic-wormhole.rs 0.8.1 asks a STUN server for your public address: `stun.piegames.de:3478`, hard-coded, run by one of its maintainers. | Only your IP address and timing are exposed, never content. | Not configurable in the library today; tracked as `pair-630.10`. |

| T15 | **Outbox file.** The pair pane (a Claude Code mod) sends chat by appending lines to `outbox.jsonl` in the session dir, and the server sends each one to the peer. A file is used because Claude Code denies a mod's MCP calls in auto mode. | Same location and lifetime as the inbox (T10), though the mod writes it with the default file permissions, not 0600 (no mod API sets them; the session folder is the user's). Only lines written after the server starts are sent, only while paired, each at most 16 KB, and each `id` once (a mod can only rewrite the whole file, so a read caught mid-rewrite starts over without resending); anything else is reported as `outbox_failed`. | Any process running as the same user, including Claude through a plain file write, can send the peer a message without calling `send_to_peer`. Such a process can already read the inbox (T10) and act as the user, and `send_to_peer` has no confirmation of its own, so this adds no new capability for Claude. Accepted for now (owner decision 2026-11-11). |
| T16 | **Codex wake.** In Codex, pair runs `codex queue` to wake the chat that started the pairing, and Codex adds the queued text to the chat as a user message. | The text is a fixed notice (call `check_messages`), never peer content, so peer text never reaches Codex as the user's words; it arrives through `check_messages`, marked as the peer's. One wake until `check_messages` runs, so a chatty peer can't flood the chat. The thread ID comes from Codex's own `_meta.threadId` and only UUID characters reach the command line; `codex queue` output never touches the MCP stream. Codex sends pair's events only to its log, so this is the only way to wake an idle chat (GitHub #17 tracks Codex's own agent mail). | Codex runs no pair hooks, so trust levels are guidance only, as in T3. Any process running as the same user can queue text into any Codex chat; pair adds no new capability there. Not yet tested in a live Codex session: whether Codex shows pair's own confirmation dialog for `pair_accept` / `send_file` (if Codex declines it unseen, pair asks in chat for the pairing and refuses the file). |

## Owner decisions (2026-11-05)

1. The public relay's metadata exposure is acceptable for the pilot.
2. No outbound content filter in the pilot (T5); revisit for a paid tier.
3. Default trust level is read-only.

## Owner decisions (2026-11-08)

1. Trust levels are guidance to Claude. pair doesn't gate tool calls with a PreToolUse hook, and there is no option to make it (T3).

## Owner decisions (2026-11-11)

1. The pair pane may send chat through an outbox file in the session dir, unauthenticated, for now (T15).

## Asks of the reviewer

1. Which data classes may be used in the pilot, given there is no outbound filter (T5)?
2. Is relying on Claude's judgement and the owner's permission mode for peer requests (T3) acceptable, as for other untrusted content?
