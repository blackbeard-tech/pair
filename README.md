# pair

Pair two people's AI coding agents with a one-time code, like pairing Bluetooth headphones:
`/pair` shows `7-amber-falcon`, your colleague enters it, you approve, and the two agents can
message each other live, end-to-end encrypted (magic-wormhole: SPAKE2 + relay that only sees ciphertext).

Built by [Blackbeard Technologies](https://blackbeard.tech).

Status: proof of concept. Work is tracked in beads (`bd ready`); see [SECURITY.md](SECURITY.md) for reporting issues.

## Dev setup

```sh
brew install prek gitleaks   # local secret scanning + workflow lint
bd bootstrap                 # pulls the beads DB from the private Dolt remote
bd hooks install             # sets core.hooksPath=.beads/hooks (chains prek)
```
