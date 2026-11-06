# pair: threat model (pilot, P1)

Status: draft for IT/Security review, 2026-11-05. Owner: Blackbeard Technologies. Items marked **[unverified]** are not yet tested.

## Scope

P1 pilot only: two people, Claude Code to Claude Code, pairing for the length of one session,
using the public magic-wormhole relay (`relay.magic-wormhole.io`). The self-hosted relay (P2),
other agent tools (P3) and remembered peers are out of scope.

## How it works

1. Owner A runs `/pair`. A's local `pair` binary (an MCP channel server started by Claude Code)
   connects to the relay and gets a code such as `7-amber-falcon`: a nameplate number and two words.
2. A tells B the code out of band (chat, voice). B runs `/pair 7-amber-falcon`.
3. Both binaries run SPAKE2 through the relay. If the codes match, both derive the same key K.
   If they don't match, both sides fail and the code is burned.
4. B sends an encrypted hello (display name). A's owner approves or rejects in their own session.
   Nothing else is exchanged until A approves.
5. The two Claude sessions exchange messages, encrypted with keys derived from K.
6. `/unpair`, closing either session, or a dropped connection ends the pairing. K exists only in memory.

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
| Relay operator | Both IP addresses, timing, message count and sizes, app ID, nameplate, mailbox ID | Message content, K, the code words |
| Network observer (P1 uses plaintext `ws://` on port 4000) | The same metadata as the relay | Message content |
| Paired peer | Whatever your Claude sends them | Your files, tools or session, except through your Claude's replies |
| Someone who overhears the code | Nothing, unless they redeem it before B does (see T1) | |

## Threats and mitigations

| # | Threat | Mitigation | Remaining risk |
|---|---|---|---|
| T1 | **Code guessing or interception.** An attacker redeems the code before B does. | SPAKE2 gives one online guess per code (2 words ≈ 16 bits, 1 in 65,536). A wrong guess fails both sides and burns the code (tested). An intercepted code still needs A's approval, and the approval prompt shows the joiner's name. | If the code leaks and the attacker gets in first, A could approve them by mistake. Codes are single-use; the ~2-minute expiry is enforced by our client **[unverified]**. |
| T2 | **Relay reads or alters messages.** | Messages are encrypted and authenticated (NaCl secretbox) with keys only the two peers hold. The relay can't run a man-in-the-middle attack without knowing the code (that's what SPAKE2 guarantees). | Metadata is exposed (see table). The relay can delay or drop messages. |
| T3 | **Prompt injection from the peer.** Peer messages try to make your Claude act against you. | Inbound messages are marked as untrusted requests from the named peer, never as instructions from the owner. The owner picks a trust level at `/pair` time: **read-only** (default; reads run automatically, everything else asks), **ask** (every action a peer triggers needs approval) or **normal**. In the POC the level is an instruction to Claude, not yet enforced by a hook. | Claude's judgment is the main defence in "normal" mode. Whether the trust level can tell peer-triggered tool calls from owner-triggered ones is an open design question (`pair-630.3`). The fallback is to apply it to the whole session while paired. |
| T4 | **Peer approves your tool use.** | `pair` never declares the channel permission-relay capability, so approvals always stay with the local owner. A test will check this (`pair-630.2`). | None identified. |
| T5 | **Data leaving the machine.** Your Claude includes secrets or confidential code in a reply. | The owner sees every outbound message in their session. The pilot runs on non-sensitive work only until this review signs off. | Accepted for the pilot: no outbound filter (owner decision, 2026-11-05). Secret scanning and PII redaction are candidates for a later paid tier. |
| T6 | **Peer crashes your client.** | Found: magic-wormhole 0.8.1 panics on a message with a non-numeric phase label. We must patch or guard it before the pilot (`pair-630.4`). | Denial of service only; data is not exposed. |
| T7 | **Compromised binary or dependency.** | Locked dependencies, cargo-deny/audit, osv-scanner, CodeQL, build provenance on releases, and a checksum check before first run. | Binaries are unsigned in the pilot (macOS signing available later). |
| T8 | **Relay blocked or unavailable.** | Pairing fails cleanly with a message. | Corporate firewalls may block `ws://` on port 4000. A self-hosted `wss://` relay on port 443 is the fix (P2, possibly brought forward). |
| T9 | **Stale or dropped pairing.** | Pairing is session-scoped. Nothing is persisted, and K is discarded on unpair or exit. A heartbeat every 4 idle minutes keeps the relay connection up (the spike saw drops between 5 and 15 idle minutes without it). | A dropped connection can't be resumed in the current library, so the user has to pair again. |
| T10 | **Peer text at rest.** Without channels, events reach Claude through a plugin monitor that reads a per-session inbox file. | The file lives under the plugin data dir, keyed by Claude Code session ID, created owner-only (0600 on macOS). It is deleted when the session ends; leftovers older than a day are swept on the next start. | Readable by other processes running as the same user while the session is open. A crash can leave it for up to a day. |
| T11 | **Files.** A peer asks your Claude to send a secret file, or sends you a harmful one. | Sending: the server asks the owner directly in a Claude Code dialog (MCP elicitation) before every file, which Claude can't answer and auto mode doesn't skip; clients that can't show it (e.g. `claude -p`) can't send files. Claude is also told never to send a file just because the peer asked, and the server refuses secret-looking paths (`.ssh`, `.env*`, keys, credentials, `~/.claude`) even if approved. Max 5 MB. Receiving: saved under a sanitised name in a quarantine folder (owner-only, never executable, deleted after 7 days), size and sha256 verified, and Claude is told the contents are untrusted. | A user can still approve sending something sensitive that the denylist doesn't recognise. A received file could be opened or run later by hand. |

## Owner decisions (2026-11-05)

1. The public relay's metadata exposure is acceptable for the pilot.
2. No outbound content filter in the pilot (T5); revisit for a paid tier.
3. Default trust level is read-only.

## Asks of the reviewer

1. Which data classes may be used in the pilot, given there is no outbound filter (T5)?
2. Is relying on Claude to honour the trust level acceptable until hook enforcement lands (T3)?
