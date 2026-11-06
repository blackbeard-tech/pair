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

When someone joins, Claude asks you "Pair with …?" and nothing is exchanged until you say yes.
Once paired, ask Claude to message the other agent, or to send them a file (up to 5 MB).
Say "unpair", or close the session, to end it.

Runs on macOS (Apple Silicon and Intel) and Windows (x64). Linux is not supported yet.

## How messages reach Claude

| Session | Delivery |
|---|---|
| Interactive Claude Code | Live, through the plugin's monitor. No flags needed. |
| Started with `claude --dangerously-load-development-channels plugin:pair@bbtech` | Live, as a channel. Optional. |
| Non-interactive (`claude -p`, Agent SDK) | Claude polls with the `check_messages` tool. |

## Safety

- **One-time code.** Wrong guesses fail on both sides and burn the code. The relay only passes on
  encrypted messages ([magic-wormhole](https://magic-wormhole.readthedocs.io/): SPAKE2 key exchange).
- **You approve every pairing.** The request shows who is joining: `user@host · git name · git email`.
- **Peer messages are requests, not instructions.** You choose how much a peer's request may trigger
  without asking you: `read-only` (default: answering and reading files), `ask` (everything asks), or `normal`.
- **Approvals stay with you.** A peer can never approve tool use in your session.
- **Files:** every file you send needs your click in a confirmation dialog (Claude can't answer it for you),
  and secret-looking files (`.ssh`, `.env`, keys) are refused.
  Received files land in a quarantine folder, are checked against their hash, and are deleted after 7 days.
- **What the relay sees:** both IP addresses, timing and message sizes, not content.

Details and known limitations are in the [threat model](docs/threat-model.md). Report security issues
privately as described in [SECURITY.md](SECURITY.md).

## Status

Pilot. Known limitations:

- Binaries are unsigned. Each is checked against a checksum pinned in the plugin before it runs.
- The public relay uses `ws://` on port 4000, which some corporate networks block.
- Pairing lasts one session. A dropped connection means pairing again.
- The trust level is an instruction to Claude, not yet enforced by a hook.

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
