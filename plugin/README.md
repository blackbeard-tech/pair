# pair

Pair two people's Claude Code sessions with a one-time code, like pairing Bluetooth headphones. You run
`/pair:pair` and get a code like `7-amber-falcon`. Your colleague runs `/pair:pair 7-amber-falcon`, you approve,
and the two agents can message each other and exchange files you approve, end-to-end encrypted with
[magic-wormhole](https://magic-wormhole.readthedocs.io/).

Built by [Blackbeard Technologies](https://blackbeard.tech). Source, full documentation and threat model:
[github.com/blackbeard-tech/pair](https://github.com/blackbeard-tech/pair).

## Use

- `/pair:pair` gives you a code to share (it works once and expires in 2 minutes).
- `/pair:pair <code>` joins a colleague's session. The other side approves before anything is exchanged.
- Pick a trust level when pairing: `read-only` (default), `ask` or `normal`. While paired, Claude Code itself asks
  you before actions the level doesn't allow.
- Say "unpair", or close the session, to end it.

Works in the Claude Code terminal, desktop app (Code tab) and IDE extensions, on macOS, Windows (needs Git for
Windows for the desktop app and IDEs) and Linux. It doesn't run in chat or cloud sessions, which don't start a
plugin's local server.

## What it runs and connects to

- **First run:** the launcher (`scripts/pair`, or `scripts/pair.cmd` + `scripts/fetch.ps1` on Windows) downloads
  this version's `pair` binary from the repository's GitHub releases, using `gh` if installed, otherwise `curl` or
  PowerShell. It runs the binary only if its sha256 matches the value pinned in `checksums.txt`. The binary is built
  from the repository's `server/` folder by its release workflow, with build provenance attestations; macOS
  binaries are signed and notarized.
- **When pairing:** `relay.magic-wormhole.io:4000` to set up the pairing, then a direct TCP connection to the other
  machine or `transit.magic-wormhole.io:4001`. The magic-wormhole library also asks `stun.piegames.de:3478` for this
  machine's public address when trying a direct connection.
- **Sent to the other side:** your messages, files you approve, and the name you appear as
  (`user@host · git name · git email` unless you set another).
- **On your machine:** the plugin data folder (inbox, received files, pairing state). Hooks: `SessionStart` and
  `FileChanged` deliver messages; `PreToolUse` adds permission prompts while paired and before accepting a pairing
  or sending a file. It never changes your settings. No analytics, no other servers.

## License

Apache-2.0. Release binaries include [magic-wormhole.rs](https://github.com/magic-wormhole/magic-wormhole.rs)
(EUPL-1.2); each release lists all third-party licences in `THIRD_PARTY_LICENSES.md`.
