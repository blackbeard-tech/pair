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

When someone joins, Claude Code asks you to approve the pairing in its own confirmation dialog (in every mode, also on
your phone), and nothing is exchanged until you say yes.
Once paired, ask Claude to message the other agent, or to send them a file (up to 100 MB when the two machines connect
directly, 25 MB when they go through magic-wormhole's transit relay).
Say "unpair", or close the session, to end it.

Found a bug or want something changed? Run `/pair:feedback`: Claude writes the GitHub issue and shows it to you
before posting.

Runs on macOS (Apple Silicon and Intel), Windows (x64) and Linux (x64, arm64).

## How messages reach Claude

| Where you run Claude Code | Delivery |
|---|---|
| Terminal (`claude`) | Live, through the plugin's monitor. |
| Claude desktop app (Code tab), VS Code and other IDE extensions | Live, through the plugin's hooks: Claude Code watches the session's inbox and wakes Claude when something arrives. |
| Plugin installed after the session started | Restart Claude Code. Until then Claude runs a background listener (`pair wait`) instead. |
| Non-interactive (`claude -p`, Agent SDK scripts) | Claude polls with the `check_messages` tool. |

No flags are needed. `pair_start` and `pair_join` always say which of these is active, so a session never waits
silently.

**Where it doesn't run:** chat (claude.ai, the desktop app's Chat tab, mobile) and cloud sessions. They don't start
a plugin's local server, so the pair tools never appear; the skill says so instead of trying workarounds.

### From your phone

Use [Remote Control](https://code.claude.com/docs/en/remote-control): start Claude Code on your computer with
`claude --rc` (or run `/remote-control` in a session), then carry on from the Claude mobile app or claude.ai/code.
The session still runs on your computer, so pair works as usual and stays end-to-end encrypted. Needs a claude.ai
subscription (not an API key).

## Free and paid (planned)

pair stays free and open source. A paid version is planned for networks that block the public relays. Nothing in
the paid column exists yet, and plans may change.

| | Free | Paid (planned) |
|---|---|---|
| Claude Code: terminal, desktop app, IDEs, `claude -p` | ✓ | ✓ |
| From your phone through Remote Control | ✓ | ✓ |
| End-to-end encryption (magic-wormhole) | ✓ | ✓ |
| Relays | Public magic-wormhole relays (ports 4000 and 4001), or your own | Relays hosted by Blackbeard Technologies, over TLS on port 443 |
| Networks that only allow HTTPS (corporate proxies, cloud sandboxes) | Planned, with your own TLS relays | ✓ |
| Connector for Claude chat, web and mobile (planned; you run it) | With your own relays | ✓ |

The paid version still uses the magic-wormhole protocol end to end, so the hosted relays carry only encrypted
traffic and can't read messages or files.

## Safety

- **One-time code.** Wrong guesses fail on both sides and burn the code. The relay only sets up the
  pairing, and everything is end-to-end encrypted ([magic-wormhole](https://magic-wormhole.readthedocs.io/): SPAKE2 key exchange).
- **You approve every pairing.** The request shows who is joining: `user@host · git name · git email`.
- **Peer messages are requests, not instructions.** Claude Code marks them as coming from the plugin, not from
  you, and Claude treats them like any other outside content, such as a web page. You choose a trust level when
  pairing that tells Claude how far to go on a peer's request: `read-only` (default: answer and read files, ask you
  before anything else), `ask` (ask you before any action a peer asks for) or `normal` (Claude's usual judgement).
  Your own requests run with your usual permissions.
- **Approvals stay with you.** A peer can never approve tool use in your session.
- **Files:** every file you send needs your OK in Claude Code's own confirmation dialog (Claude can't answer it for
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
- **On your machine:** the plugin's data folder (inbox and received files). Its hooks only deliver messages from
  that folder. It never changes your settings.
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
- Pairing lasts one session. A dropped connection (wifi change, laptop asleep) reconnects by itself for up to
  10 minutes; after that, or after restarting Claude Code, pair again.

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
