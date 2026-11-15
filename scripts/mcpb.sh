#!/usr/bin/env bash
# Build the Claude Desktop extension (dist/pair-X.Y.Z.mcpb) from release vX.Y.Z's binaries: the signed macOS ones and
# the Windows one, each checked against that release's checksums.txt. Nothing is built here.
# Usage: scripts/mcpb.sh 0.1.17
# Needs: gh, npx (for @anthropic-ai/mcpb, which validates and packs).
set -euo pipefail

v=${1:?usage: scripts/mcpb.sh X.Y.Z}
[[ $v =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "not a version: $v" >&2; exit 1; }
repo=$(git rev-parse --show-toplevel)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

cp -R "$repo/mcpb/." "$stage/"
cp "$repo/plugin/.claude-plugin/icon.png" "$stage/icon.png"
perl -pi -e "s/\"version\": \"0.0.0\"/\"version\": \"$v\"/" "$stage/manifest.json"

assets=(pair-macos-arm64 pair-macos-x64 pair-windows-x64.exe)
gh release download "v$v" -R blackbeard-tech/pair -D "$stage/server" -p checksums.txt "${assets[@]/#/-p}"
sum=(shasum -a 256)
command -v sha256sum >/dev/null && sum=(sha256sum)
(cd "$stage/server" && grep -E " ($(IFS='|'; echo "${assets[*]}"))\$" checksums.txt | "${sum[@]}" -c -) \
  || { echo "checksum mismatch: refusing to pack" >&2; exit 1; }
rm "$stage/server/checksums.txt"
chmod +x "$stage/server/pair.sh" "$stage/server"/pair-macos-*

mkdir -p "$repo/dist"
mcpb=@anthropic-ai/mcpb@2.1.2 # pinned: it builds what users install
npx --yes "$mcpb" validate "$stage/manifest.json"
npx --yes "$mcpb" pack "$stage" "$repo/dist/pair-$v.mcpb"
echo "$repo/dist/pair-$v.mcpb"
