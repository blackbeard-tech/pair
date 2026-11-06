## What's new

{{WHATSNEW}}

## Install or update

In Claude Code, first time: `/plugin marketplace add blackbeard-tech/marketplace`, then `/plugin install pair@bbtech`.
Already installed: `/plugin update pair@bbtech`. Then restart Claude Code.

The plugin downloads the right file below by itself and checks it against `checksums.txt`, so you rarely need
these files directly.

## Files

| File | For |
|---|---|
| `pair-macos-arm64` | macOS on Apple Silicon (M1 and later) |
| `pair-macos-x64` | macOS on Intel |
| `pair-windows-x64.exe` | Windows 10 and 11, x64 (also runs on Windows on Arm) |
| `pair-linux-x64` | Linux, x64 (static, any distribution) |
| `pair-linux-arm64` | Linux, arm64 (static, any distribution) |
| `checksums.txt` | SHA-256 of each file |

## Signing

- {{MACOS}}
- Windows, Linux: unsigned.

## Verify a download

```sh
shasum -a 256 -c checksums.txt --ignore-missing                     # macOS, Linux
codesign --verify --strict --verbose=2 pair-macos-arm64             # macOS: signature
spctl -a -vvv -t open --context context:primary-signature pair-macos-arm64   # macOS: notarized?
```

On Windows: `Get-FileHash pair-windows-x64.exe -Algorithm SHA256`, then compare with `checksums.txt`.

Built by [Blackbeard Technologies](https://blackbeard.tech) from tag {{TAG}}; see the
[changelog](https://github.com/blackbeard-tech/pair/blob/main/CHANGELOG.md) for earlier releases.
