# pair privacy notice

pair is a Claude Code plugin by Blackbeard Technologies that connects two people's Claude Code sessions.
Blackbeard Technologies runs no server for it and collects nothing: no accounts, analytics, telemetry or logs.

## What goes where

| Data | Who gets it | Why |
|---|---|---|
| Your messages and the files you approve | Only the colleague you paired with, end-to-end encrypted ([magic-wormhole](https://magic-wormhole.readthedocs.io/)) | That's the point of pairing |
| The name you appear as (`user@host · git name · git email`, unless you set another) | Your colleague | So they can see who is asking to pair |
| IP address, timing and size of traffic, the pairing code's number (never the words or content) | The public magic-wormhole relay (`relay.magic-wormhole.io`), and `transit.magic-wormhole.io` when the two machines can't connect directly | Setting up the connection and carrying encrypted traffic |
| IP address | Your colleague's machine, when the two connect directly | A direct connection |
| IP address | The STUN server `stun.piegames.de`, when trying a direct connection | Finding this machine's public address |
| IP address (download of the `pair` binary on first run) | GitHub | Fetching the release that matches the plugin version |

The magic-wormhole relays and the STUN server are run by third parties under their own terms. Relays never see
content: everything is encrypted with keys only the two of you hold.

## What stays on your machine

In the plugin's data folder:

- The session's inbox of pairing events and messages. Deleted when the Claude Code session ends; anything left by
  a crash is removed after a day.
- Files your colleague sent you. Deleted after 7 days.
- The session's pairing state (who you're paired with and at what trust level). Deleted when the session ends.

Nothing is kept after you unpair or close the session, and pairings aren't remembered.

## Contact

Questions: open an issue at [github.com/blackbeard-tech/pair](https://github.com/blackbeard-tech/pair/issues).
Security issues: report privately as described in [SECURITY.md](../SECURITY.md).
