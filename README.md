# pair

Pair two people's Claude Code sessions with a one-time code, like pairing Bluetooth headphones.
You run `/pair:pair` and get a code like `7-amber-falcon`. Your colleague enters it, you approve, and the
two agents can message each other live, end-to-end encrypted.

Built by [Blackbeard Technologies](https://blackbeard.tech).

## Install

In Claude Code:

```
/plugin marketplace add blackbeard-tech/marketplace
/plugin install pair@bbtech
```

Restart Claude Code, then:

- `/pair:pair` gives you a code to send to your colleague (it works once and expires in 2 minutes).
- `/pair:pair 7-amber-falcon` joins a colleague's session.

When someone joins, Claude Code asks you "pair with …?" and nothing is exchanged until you say yes.
Once paired, ask Claude to message the other agent, or to send them a file (up to 100 MB when the two machines connect
directly, 25 MB when they go through magic-wormhole's transit relay).
Say "unpair", or close the session, to end it.

Runs on macOS (Apple Silicon and Intel), Windows (x64) and Linux (x64, arm64).

## How messages reach Claude

| Where you run Claude Code | Delivery |
|---|---|
| Terminal (`claude`) | Live, through the plugin's monitor. |
| Claude desktop app (Code tab), VS Code and other IDE extensions | Live, through the plugin's hooks: Claude Code watches the session's inbox and wakes Claude when something arrives. On Windows this needs Git for Windows (Git Bash). |
| Plugin installed after the session started | Restart Claude Code. Until then Claude runs a background listener (`pair wait`) instead. |
| Non-interactive (`claude -p`, Agent SDK scripts) | Claude polls with the `check_messages` tool. |

No flags are needed. `pair_start` and `pair_join` always say which of these is active, so a session never waits
silently.

**Where it doesn't run:** chat (claude.ai, the desktop app's Chat tab, mobile) and cloud sessions. They don't start
a plugin's local server, so the pair tools never appear; the skill says so instead of trying workarounds.

## Safety

- **One-time code.** Wrong guesses fail on both sides and burn the code. The relay only sets up the
  pairing, and everything is end-to-end encrypted ([magic-wormhole](https://magic-wormhole.readthedocs.io/): SPAKE2 key exchange).
- **You approve every pairing.** The request shows who is joining: `user@host · git name · git email`.
- **Peer messages are requests, not instructions.** You choose a trust level when pairing, and Claude Code itself
  enforces it while you're paired: `read-only` (default: reading files and messaging the peer run normally,
  anything else needs your OK), `ask` (every action needs your OK) or `normal` (your usual permissions). Claude
  Code can't tell whether an action came from you or the peer, so the level applies to everything while paired. On Windows this needs Git for
  Windows (Git Bash), like live delivery in the desktop app.
- **Approvals stay with you.** A peer can never approve tool use in your session.
- **Files:** every file you send needs your OK in Claude Code's own permission prompt (Claude can't answer it for
  you, and auto mode doesn't skip it), and secret-looking files (`.ssh`, `.env`, keys) are refused.
  Received files land in a quarantine folder, are checked against their hash, and are deleted after 7 days.
- **What the relays see:** the public relay only sets the pairing up; messages then travel directly between the two
  machines when possible, or through magic-wormhole's transit relay. Relays see IP addresses, timing and sizes, never
  content. A direct connection means each side learns the other's IP address.

## What it runs and connects to

- **First run:** the plugin's launcher downloads this version's `pair` binary from this repository's GitHub releases
  (with `gh` if it's installed, otherwise `curl`; PowerShell on Windows) and refuses it unless its sha256 matches
  the one pinned in the plugin ([plugin/checksums.txt](plugin/checksums.txt)). The binary is built from
  [server/](server/) by [release.yml](.github/workflows/release.yml), with a build provenance attestation.
- **When pairing:** `relay.magic-wormhole.io:4000` (sets up the pairing), then a direct TCP connection to the other
  machine or `transit.magic-wormhole.io:4001`. The magic-wormhole library also asks the STUN server
  `stun.piegames.de:3478` for this machine's public address when trying a direct connection.
- **Sent to the other side:** your messages and the files you approve, plus the name you appear as
  (`user@host · git name · git email` unless you set another).
- **On your machine:** the plugin's data folder (inbox, received files, the session's pairing state). Its hooks
  read that folder; while you're paired the `PreToolUse` hook adds permission prompts as described above. It
  never changes your settings.
- Nothing else: no analytics, no other servers.

Details and known limitations are in the [threat model](docs/threat-model.md). Report security issues
privately as described in [SECURITY.md](SECURITY.md).

## Status

Pilot. Known limitations:

- macOS binaries are signed and notarized; Windows and Linux binaries are unsigned. Each is checked against a
  checksum pinned in the plugin before it runs.
- The public relay uses `ws://` on port 4000 and transit uses port 4001, which some corporate networks block.
  If setup stalls, the pairing ends with a clear message rather than hanging.
- Messages are limited to 16 KB; files to 100 MB directly, 25 MB through the transit relay.
- Pairing lasts one session. A dropped connection means pairing again.

## Development

The Rust server is in [server/](server/), the plugin in [plugin/](plugin/).

```sh
cargo test --manifest-path server/Cargo.toml
cargo build --release --manifest-path server/Cargo.toml
python3 -I server/tests/two_peers.py server/target/release/pair   # end to end, over the public relay
```

To run your local build in Claude Code, start it with `PAIR_BIN=/path/to/pair` set.

Maintainers also use:

```sh
brew install prek gitleaks   # secret scanning + workflow lint on commit
bd bootstrap                 # issue tracker (beads); its database is private
bd hooks install             # sets core.hooksPath=.beads/hooks (chains prek)
```

## License

Apache-2.0, see [LICENSE](LICENSE) and [NOTICE](NOTICE). Release binaries include
[magic-wormhole.rs](https://github.com/magic-wormhole/magic-wormhole.rs) (EUPL-1.2).
