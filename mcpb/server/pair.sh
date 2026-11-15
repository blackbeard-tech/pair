#!/bin/sh
# macOS entry point of the Claude Desktop extension: run the release binary built for this Mac's chip.
d=$(dirname "$0")
case "$(uname -m)" in
  arm64) exec "$d/pair-macos-arm64" "$@" ;;
  *) exec "$d/pair-macos-x64" "$@" ;;
esac
