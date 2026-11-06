# Changelog

What changed in each release of pair, newest first. Install or update in Claude Code with
`/plugin update pair@bbtech`, then restart Claude Code.

From 0.1.6 the plugin and its binary always share one version number. Before that they were numbered
separately; each early entry names the plugin versions that used that binary.

## Unreleased

- **Bigger files.** Files stream instead of being held in memory: up to 100 MB when the two machines connect
  directly, 25 MB when they go through the public relay (was 5 MB).
- **Clear message where pair can't run.** In chat, claude.ai and cloud sessions the plugin's local server never
  starts; the `/pair:pair` skill now says so instead of trying workarounds.
- Threat model: peer-chosen connection addresses (T13) and the third-party STUN server the Rust library uses (T14).

## 0.1.9 (2026-11-06)

- **Messages and files no longer go through the relay's mailbox.** Like magic-wormhole's own command-line tool,
  pair now uses the public relay only to set up the pairing, then talks over a direct connection between the two
  machines (or magic-wormhole's transit relay when they can't reach each other). This fixes the stalls that ended
  pairings. Both sides need 0.1.9 or later; an older side is told to update.
- **Sending a file asks you in every app.** Claude Code shows its own permission prompt for each file, including
  in the desktop app, in auto mode and when the tool is pre-approved. Modes that never ask (bypass, dontAsk) can't
  send files. An app that answers a confirmation dialog without showing it is no longer reported as you declining.
- Long messages show a preview in notifications, with a pointer to the full text (Claude Code cuts notifications at
  about 500 characters). Event lines use a short sender name.
- Linux builds (x64 and arm64), e.g. for Claude Code on Linux.
- Wording fix after accepting a pairing.

## 0.1.8 (2026-11-06)

- **Live delivery in the desktop app (Code tab) and IDE extensions.** Those apps don't run plugin monitors; the
  plugin now uses Claude Code hooks there to wake Claude when something arrives. `pair_start` and `pair_join`
  check this works and say which delivery method is active, or that it isn't set up yet (for example when the
  plugin was installed mid-session) and what to do.
- Claude is told to always show you what the other person's agent said.

## 0.1.7 (2026-11-06)

- **macOS binaries are signed** (Developer ID, Blackbeard Technologies Ltd) and submitted to Apple for
  notarization.
- First fallback for the desktop app and IDEs: Claude runs a background listener (`pair wait`).
- Stalls on the public relay end the pairing with a clear message instead of hanging; a file that stops arriving is
  discarded with a notice. Smaller messages on the relay (16 KB max).
- Releases keep each stage's files (build, sign, notarize) and publish without waiting for Apple.

## 0.1.6 (2026-11-06)

- **Send files** to the person you're paired with (up to 5 MB at the time), each confirmed by you. Secret-looking
  files (`.ssh`, `.env`, keys) are refused; received files go to a quarantine folder and are checked against their
  hash.
- Windows: works when Claude Code was started from PowerShell 7.
- First run: the binary downloads correctly when `gh` is signed in to a GitHub Enterprise server, and when two
  parts of the plugin start at once.
- From this release the plugin and the binary share one version number.
- (0.1.5 was tagged but never released.)

## 0.1.4 (2026-11-05), used by plugin 0.1.5

- Windows: live delivery fixed (the monitor's heartbeat wasn't updating), and events can no longer be lost.
- Claude no longer polls for messages by itself.

## 0.1.3 (2026-11-05), used by plugin 0.1.4

- **Live delivery without the channel flag**, through a plugin monitor in the terminal.
- `check_messages` for sessions where nothing is delivered automatically.

## 0.1.2 (2026-11-05), used by plugin 0.1.3

- The approval prompt shows who is joining: `user@host · git name · git email`.

## 0.1.1 (2026-11-05), used by plugins 0.1.1 and 0.1.2

- New relay namespace `blackbeard.tech/pair/v1` (doesn't pair with 0.1.0).
- Windows: native launcher (cmd and PowerShell) instead of bash.

## 0.1.0 (2026-11-05)

- First release: pair two Claude Code sessions with a one-time code, end-to-end encrypted over magic-wormhole,
  with your approval before anything is exchanged. Messages arrive as channel events (needs
  `--dangerously-load-development-channels`). macOS and Windows.
