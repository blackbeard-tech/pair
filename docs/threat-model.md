# pair: threat model (pilot, P1)

Status: draft for IT/Security review, 2026-11-05. Items marked **[unverified]** are not yet tested.

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
| T3 | **Prompt injection from the peer.** Peer messages try to make your Claude act against you. | Inbound messages are marked as untrusted requests from the named peer, never as instructions from the owner. The owner picks a trust level at `/pair` time: **ask** (default; every action a peer triggers needs approval), **read-only** (reads run automatically, everything else asks) or **normal**. | Claude's judgment is the main defence in "normal" mode. Whether the trust level can tell peer-triggered tool calls from owner-triggered ones is an open design question (`pair-630.3`). The fallback is to apply it to the whole session while paired. |
| T4 | **Peer approves your tool use.** | `pair` never declares the channel permission-relay capability, so approvals always stay with the local owner. A test will check this (`pair-630.2`). | None identified. |
| T5 | **Data leaving the machine.** Your Claude includes secrets or confidential code in a reply. | The owner sees every outbound message in their session. The pilot runs on non-sensitive work only until this review signs off. | No technical filter yet. Options: scan outbound messages for secrets, or require owner approval to send in "ask" mode. **Decision needed.** |
| T6 | **Peer crashes your client.** | Found: magic-wormhole 0.8.1 panics on a message with a non-numeric phase label. We must patch or guard it before the pilot (`pair-630.4`). | Denial of service only; data is not exposed. |
| T7 | **Compromised binary or dependency.** | Locked dependencies, cargo-deny/audit, osv-scanner, CodeQL, build provenance on releases, and a checksum check before first run. | Binaries are unsigned in the pilot (macOS signing available later). |
| T8 | **Relay blocked or unavailable.** | Pairing fails cleanly with a message. | Corporate firewalls may block `ws://` on port 4000. A self-hosted `wss://` relay on port 443 is the fix (P2, possibly brought forward). |
| T9 | **Stale pairing.** | Pairing is session-scoped. Nothing is persisted, and K is discarded on unpair or exit. | A dropped connection can't be resumed in the current library, so the user has to pair again. |

## Asks of the reviewer

1. Is the public relay's metadata exposure (table above) acceptable for the pilot, or must the
   self-hosted relay come first?
2. Which data classes may be used in the pilot (see T5)?
3. Is the default trust level "ask" sufficient, or should outbound messages also need approval?
