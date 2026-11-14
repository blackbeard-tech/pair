#!/usr/bin/env bash
# Release pair X.Y.Z end to end, as CLAUDE.md "Releasing" describes: version bump PR, tag, the release build,
# checksum pin PR, then this machine's plugin. Run it only with the owner's go: it is that go for every push and merge
# it makes (it sets PAIR_PUSH_OK for the pre-push hook), so it is allowlisted in .claude/settings.json.
#
# Usage: scripts/release.sh 0.1.17
# Needs: gh (signed in), git, perl; CHANGELOG.md with a filled-in "## Unreleased" section on origin/main.
set -euo pipefail

v=${1:?usage: scripts/release.sh X.Y.Z}
[[ $v =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "not a version: $v" >&2; exit 1; }
export PAIR_PUSH_OK=1
say() { printf '\n== %s\n' "$*"; }

repo=$(git rev-parse --show-toplevel)
git -C "$repo" fetch -q origin --tags
if git -C "$repo" rev-parse -q --verify "refs/tags/v$v" >/dev/null; then
  echo "v$v already exists" >&2
  exit 1
fi

# Work in a throwaway worktree off origin/main, so whatever is checked out here is left alone.
wt="$(mktemp -d)/release"
git -C "$repo" worktree add -q -b "release/$v" "$wt" origin/main
cleanup() {
  git -C "$repo" worktree remove --force "$wt" 2>/dev/null || true
  git -C "$repo" branch -D -q "release/$v" "release/pin-$v" 2>/dev/null || true
}
trap cleanup EXIT
cd "$wt"

# Open a PR for the current branch, wait for CI (rerunning failed jobs once: the e2e can flake), merge it.
ship() {
  local branch id
  branch=$(git branch --show-current)
  git push -q -u origin "$branch"
  gh pr create --base main --head "$branch" --title "$1" --body "$2"
  sleep 20 # let the checks register
  if ! gh pr checks "$branch" --watch --interval 30 >/dev/null; then
    echo "CI failed on $branch; rerunning the failed jobs once"
    for id in $(gh run list --branch "$branch" --json databaseId,conclusion \
      --jq '.[] | select(.conclusion == "failure") | .databaseId'); do
      gh run rerun "$id" --failed
    done
    sleep 20
    gh pr checks "$branch" --watch --interval 30 >/dev/null || { echo "CI failed twice on $branch; see its PR" >&2; exit 1; }
  fi
  gh pr merge "$branch" --rebase
}

say "1/3 version bump"
grep -q '^## Unreleased$' CHANGELOG.md || { echo "CHANGELOG.md has no '## Unreleased' section" >&2; exit 1; }
perl -0pi -e "s/^version = \"[^\"]*\"/version = \"$v\"/m" server/Cargo.toml
perl -0pi -e "s/(name = \"pair\"\\nversion = )\"[^\"]*\"/\${1}\"$v\"/" server/Cargo.lock
perl -0pi -e "s/^## Unreleased\$/## $v ($(date +%F))/m" CHANGELOG.md
git commit -q -am "Release $v"
ship "Release $v" "Version bump for $v: \`server/Cargo.toml\`, \`Cargo.lock\`, CHANGELOG. Made by \`scripts/release.sh\`."

say "2/3 tag and release build"
git fetch -q origin
tip=$(git rev-parse origin/main)
[ "$(git log -1 --format=%s "$tip")" = "Release $v" ] || { echo "origin/main isn't the 'Release $v' commit" >&2; exit 1; }
git tag "v$v" "$tip"
git push -q origin "v$v"
sleep 20 # let the run register
run=$(gh run list --workflow release.yml --branch "v$v" --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$run" --interval 60 --exit-status >/dev/null || { echo "release build failed: gh run view $run" >&2; exit 1; }

say "3/3 pin the checksums"
git switch -q -c "release/pin-$v" origin/main
dl=$(mktemp -d)
gh release download "v$v" -p checksums.txt -D "$dl"
{
  echo "# release v$v  (binaries the launchers fetch; they refuse any asset whose sha256 is not listed here)"
  cat "$dl/checksums.txt"
} >plugin/checksums.txt
perl -pi -e "s/\"version\": \"[^\"]*\"/\"version\": \"$v\"/" plugin/.claude-plugin/plugin.json
# The launcher fetches this machine's binary and refuses it unless its sha256 matches the pin.
PAIR_DATA="$dl/launcher" plugin/scripts/pair hook session-start </dev/null
ls "$dl/launcher/$v"/pair-* >/dev/null || { echo "the launcher didn't fetch the v$v binary" >&2; exit 1; }
git commit -q -am "Plugin $v: pin release v$v"
ship "Plugin $v: pin release v$v" "Pins the v$v release's checksums and sets \`plugin.json\` to $v; the launcher fetched and verified this machine's binary against the pin. Made by \`scripts/release.sh\`."

say "pair $v is live"
if command -v claude >/dev/null; then
  claude plugin marketplace update bbtech >/dev/null && claude plugin update pair@bbtech || true
fi
gh release view "v$v" --json body --jq '.body' | grep -E '^- (macOS|Windows)' || true
