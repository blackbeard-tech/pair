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
4. B sends an encrypted hello (display name). A's owner approves or rejects in their own session (Claude Code's own permission prompt for `pair_accept`, which no mode skips).
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
| T3 | **Prompt injection from the peer.** Peer messages try to make your Claude act against you. | Inbound messages are marked as untrusted requests from the named peer, never as instructions from the owner. The owner picks a trust level when pairing: **read-only** (default; reads run automatically, everything else asks), **ask** (every action a peer triggers needs approval) or **normal**. Since 0.1.10 a plugin PreToolUse hook enforces it: Claude Code itself asks the user before any non-read tool (read-only) or any tool (ask) while paired, even in auto mode, and refuses in modes that never ask. A hook can't tell whether a call was prompted by the peer or the user, so it applies to the whole session while paired. | In "normal" mode, Claude's judgment is the main defence. The read-only allowlist includes Agent (the hook also runs inside subagents, so their tool calls are checked). Since 0.1.11 it no longer includes Skill: loading another plugin's skill can run that skill's own shell lines and register its hooks, which no PreToolUse hook sees, so Claude invoking any skill except pair's own asks first. Another plugin's mod can approve a call this hook asked about, unless managed settings prevent it; pair can't stop that. On Windows without Git Bash the hook doesn't run, and the trust level relies on Claude. |
| T4 | **Peer approves your tool use.** | `pair` declares no channel at all (and never the channel permission-relay capability), so approvals always stay with the local owner. A unit test checks this (`never_declares_permission_relay`). | None identified. |
| T5 | **Data leaving the machine.** Your Claude includes secrets or confidential code in a reply. | The owner sees every outbound message in their session. The pilot runs on non-sensitive work only until this review signs off. | Accepted for the pilot: no outbound filter (owner decision, 2026-11-05). Secret scanning and PII redaction are candidates for a later paid tier. |
| T6 | **Peer crashes your client.** | magic-wormhole 0.8.1 panics on a message with a non-numeric phase label. Guarded: each pairing runs on its own thread inside `catch_unwind`, so such a message ends that pairing ("the peer sent malformed data") and the server keeps running. | Denial of service of that pairing only; data is not exposed. The guard has not yet been exercised with a crafted message (no test peer can send one through the library's API). |
| T7 | **Compromised binary or dependency.** | Locked dependencies, cargo-deny (advisories, licences, sources), osv-scanner, CodeQL, build provenance on releases, and a checksum check before first run. | macOS binaries are signed (Developer ID) and notarized; Windows and Linux binaries are unsigned (the checksum check still applies). |
| T8 | **Relay blocked, unavailable or stalling.** | Pairing fails cleanly with a message. Since 0.1.9 the relay mailbox only carries the setup (as in the magic-wormhole CLI); messages and files go over transit, directly between the machines when possible. Measured before: the mailbox intermittently stalled under message traffic (about 1 in 12 test runs); after: no stalls in about 110 large messages over transit, the one failure in 15 runs being during setup. Any send not acknowledged within 30 s, or (from 0.1.11) 95 s without hearing from the peer, counts as a dropped connection: both users are told, and pair reconnects by itself for up to 10 minutes. A file that stops arriving for 45 s is discarded with a notice, so stalls are never silent. | Corporate firewalls may block `ws://` on port 4000. A self-hosted `wss://` relay on port 443 is the fix (P2, possibly brought forward). |
| T9 | **Stale or dropped pairing.** | Pairing is session-scoped. Nothing is persisted, and K is discarded on unpair or exit. A heartbeat every 30 s (4 minutes with peers before 0.1.11) keeps NAT and relay paths open; the spike saw drops between 5 and 15 idle minutes without one. Closing a session sends `bye`, so the peer ends at once. A dropped connection reconnects for up to 10 minutes on a per-slot code derived from K: a 256-bit password through SPAKE2, so the relay or anyone else can't take over the pairing, and the nameplate the relay sees is unlinkable to the pairing. Only the two original processes hold K, so no new approval is asked. | Reconnecting doesn't survive a Claude Code restart (K is in memory only; pair-4kp scope B). A relay operator who blocks the reconnect code ends the pairing, as it could anyway. Reconnecting needs the two clocks within about 30 s. Records in flight at the moment of a drop can be lost. |
| T10 | **Peer text at rest.** Every event is written to a per-session inbox file, which the plugin monitor or hooks read. | The file lives under the plugin data dir, keyed by Claude Code session ID, created owner-only (0600 on macOS and Linux). It is deleted when the session ends; leftovers older than a day are swept on the next start. | Readable by other processes running as the same user while the session is open. A crash can leave it for up to a day. |
| T11 | **Files.** A peer asks your Claude to send a secret file, or sends you a harmful one. | Sending: since 0.1.11 `send_file` (like `pair_accept`) is marked `anthropic/requiresUserInteraction`, so Claude Code shows its own permission prompt for every file in every mode (even when the tool is pre-approved, in auto and bypass mode, and on Remote Control without one-tap approval), with no "don't ask again", and refuses in dontAsk. It doesn't depend on hooks. With other clients, or Claude Code versions that may predate the flag, the server asks through an MCP dialog; an app that declines that dialog without showing it is reported as "couldn't ask", never as the user declining. Claude is also told never to send a file just because the peer asked, and the server refuses secret-looking paths (`.ssh`, `.env*`, keys, credentials, `~/.claude`) even if approved. Max 100 MB directly, 25 MB through the transit relay; streamed, never held whole in memory. Receiving: saved under a sanitised name in a quarantine folder (owner-only, never executable, deleted after 7 days), size and sha256 verified, and Claude is told the contents are untrusted. | A user can still approve sending something sensitive that the denylist doesn't recognise. A received file could be opened or run later by hand. On Windows without Git Bash, file sends rely on the MCP dialog. |
| T12 | **IP addresses shared with the peer.** | Transit tries a direct connection first, so each side learns the other's local and public IP addresses (and a peer's machine may be reachable on the listening port while paired). | Acceptable between colleagues; a relay-only mode (magic-wormhole `FORCE_RELAYED`) could be offered for privacy. |
| T13 | **Peer-chosen connection addresses.** A peer's transit hints decide which addresses our side connects to, including addresses inside your network. | Relays the peer names are ignored (only our configured transit relay is used). Direct connections carry only the transit handshake, which fails unless the other end knows the pairing key, so no data goes to a wrong address. | A peer could make your machine attempt TCP connections to LAN addresses (a probe, not data exposure). Filtering private-range hints from peers, or a relay-only mode, is tracked as `pair-630.9`. |
| T14 | **Third-party STUN lookup.** For direct connections, magic-wormhole.rs 0.8.1 asks a STUN server for your public address: `stun.piegames.de:3478`, hard-coded, run by one of its maintainers. | Only your IP address and timing are exposed, never content. | Not configurable in the library today; tracked as `pair-630.10`. |

## Owner decisions (2026-11-05)

1. The public relay's metadata exposure is acceptable for the pilot.
2. No outbound content filter in the pilot (T5); revisit for a paid tier.
3. Default trust level is read-only.

## Asks of the reviewer

1. Which data classes may be used in the pilot, given there is no outbound filter (T5)?
2. Is the hook enforcement in T3 enough, given that trust "normal" (and Windows without Git Bash) rely on Claude's judgement?
