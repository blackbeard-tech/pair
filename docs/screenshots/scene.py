"""Drive a real Claude Code session with the local pair build through the README scenes (docs/img).

Needs: a release build (cargo build --release --manifest-path server/Cargo.toml), a local mailbox server on
port 4777 (pip install magic-wormhole-mailbox-server; twist wormhole-mailbox --port tcp:4777:interface=127.0.0.1),
and pyte + pillow (pip install pyte pillow). Then: python3 docs/screenshots/scene.py. Frames (PNG and the screen
text, to check for anything personal) go to $TMPDIR/pair-shots; copy the ones you want to docs/img.

The colleague is a scripted pair server with a made-up identity; the project is a throwaway /tmp/acme-api.
"""

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from term import Term

REPO = os.path.dirname(os.path.dirname(HERE))
BIN = f"{REPO}/server/target/release/pair"
RELAY = "ws://127.0.0.1:4777/v1"
OUT = os.path.join(tempfile.gettempdir(), "pair-shots")
os.makedirs(OUT, exist_ok=True)


class Peer:
    """The colleague: a pair server driven over MCP stdio, as Claude Code would."""

    def __init__(self, name):
        env = dict(os.environ, PAIR_DATA=tempfile.mkdtemp(), CLAUDE_CODE_SESSION_ID="demo-sam", PAIR_RELAY=RELAY)
        env = {k: v for k, v in env.items() if not k.startswith("CLAUDE") or k == "CLAUDE_CODE_SESSION_ID"}
        self.inbox = os.path.join(env["PAIR_DATA"], "sessions", "demo-sam", "inbox.jsonl")
        self.p = subprocess.Popen([BIN], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
        self.q, self.n, self.name = queue.Queue(), 0, name
        threading.Thread(target=self._read, daemon=True).start()
        self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "demo"}})

    def _read(self):
        for line in self.p.stdout:
            self.q.put(json.loads(line))

    def rpc(self, method, params=None):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}}) + "\n")
        self.p.stdin.flush()
        while True:
            m = self.q.get(timeout=60)
            if m.get("id") == self.n:
                return m["result"]["content"][0]["text"] if "content" in m.get("result", {}) else m["result"]

    def tool(self, tool, **args):
        return self.rpc("tools/call", {"name": tool, "arguments": args})

    def wait_event(self, kind, timeout=90):
        end = time.time() + timeout
        while time.time() < end:
            if os.path.exists(self.inbox):
                for line in open(self.inbox):
                    if json.loads(line)["meta"]["kind"] == kind:
                        return
            time.sleep(0.3)
        raise TimeoutError(kind)


def idle(t, quiet=3, timeout=120):
    """Wait until Claude has stopped working (no 'esc to interrupt') for `quiet` seconds."""
    end, calm = time.time() + timeout, 0
    while time.time() < end:
        calm = calm + 1 if "esc to interrupt" not in t.text() else 0
        if calm >= quiet * 2:
            return
        time.sleep(0.5)
    raise TimeoutError("still busy")


def snap(t, name):
    open(os.path.join(OUT, f"{name}.txt"), "w").write(t.text())
    t.png(os.path.join(OUT, f"{name}.png"))
    print("snap", name, flush=True)


# A copy: a --plugin-dir the session watches gets .claude-plugin/types written into it.
plugin = os.path.join(OUT, "plugin")
shutil.rmtree(plugin, ignore_errors=True)
shutil.copytree(f"{REPO}/plugin", plugin)

env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
env.update(TERM="xterm-256color", COLORTERM="truecolor", PAIR_BIN=BIN, PAIR_RELAY=RELAY, DISABLE_AUTOUPDATER="1")

# A small project with a real bug for Claude to find: minutes compared with seconds.
PROJECT = {
    "auth/__init__.py": "",
    "auth/session.py": 'import time\n\n# Sessions expire after this long without activity.\nSESSION_TIMEOUT = 30  # minutes\n\n\n'
    "def is_expired(last_seen: float, now: float | None = None) -> bool:\n"
    "    now = time.time() if now is None else now\n    return now - last_seen > SESSION_TIMEOUT\n",
    "tests/test_login.py": "from auth.session import is_expired\n\n\ndef test_login_session_survives_ten_minutes():\n"
    "    last_seen = 1_000_000.0\n    assert not is_expired(last_seen, now=last_seen + 10 * 60)\n",
}
for path, text in PROJECT.items():
    os.makedirs(os.path.dirname(f"/tmp/acme-api/{path}"), exist_ok=True)
    open(f"/tmp/acme-api/{path}", "w").write(text)
allowed = ",".join(f"mcp__plugin_pair_pair__{t}" for t in ("pair_start", "check_messages", "send_to_peer", "unpair"))
t = Term(["claude", "--plugin-dir", plugin, "--allowedTools", allowed], env, "/tmp/acme-api")

try:
    end = time.time() + 60
    while "to manage" not in t.text() and time.time() < end:  # footer: "auto mode on · 1 monitor · ↓ to manage"
        if "Yes, I trust this folder" in t.text():  # first run in this folder only
            t.send("\x1bOB")
            time.sleep(0.5)
            t.send("\r")
        time.sleep(0.5)
    t.wait_for("to manage", 5)
    time.sleep(4)
    snap(t, "00-start")

    t.send("/pair:pair", delay=0.08)
    time.sleep(1)
    t.send("\r")
    t.wait_for("expires in 2 minutes", 120)
    idle(t)
    snap(t, "01-code")
    code = re.findall(r"\b\d+-[a-z]+-[a-z]+\b", t.text())[-1]
    print("code", code, flush=True)

    sam = Peer("sam")
    print(sam.tool("pair_join", code=code, name="sam@laptop · Sam Rivera · sam@example.com"), flush=True)
    t.wait_for("Sam", 120)
    time.sleep(8)
    snap(t, "02-request")
    t.wait_for("Do you want to proceed", 120)
    time.sleep(2)
    snap(t, "03-dialog")
    t.send("\r")  # Yes
    sam.wait_event("paired")
    idle(t)

    sam.tool("send_to_peer", text="Hi! test_login started failing on main after the session-timeout change. "
                                   "Could your Claude check auth/session.py and tell me what you find?")
    t.wait_for("test_login", 120)
    idle(t)
    snap(t, "04-message")

    t.send("/pair-pane", delay=0.08)
    time.sleep(1)
    t.send("\r")
    time.sleep(5)
    snap(t, "05-pane")
finally:
    snap(t, "99-last")
    os.kill(t.pid, 9)
