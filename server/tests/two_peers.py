"""End-to-end: two `pair` MCP servers pair over the relay and exchange messages.

Usage: python3 -I server/tests/two_peers.py server/target/release/pair
Stdlib only. Talks to the public relay, so it needs network.
"""

import json
import queue
import subprocess
import sys
import threading

BIN = sys.argv[1]


class Peer:
    def __init__(self, label, env=None):
        self.label, self.n = label, 0
        self.answer = "accept"  # reply to elicitation dialogs (the human's yes/no)
        self.p = subprocess.Popen([BIN], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
        self.q = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()
        r = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {"elicitation": {}}, "clientInfo": {"name": "t"}})
        assert r["capabilities"]["experimental"] == {"claude/channel": {}}, r

    def _read(self):
        for line in self.p.stdout:
            m = json.loads(line)
            if m.get("method") == "elicitation/create":  # play the human
                self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": m["id"],
                    "result": {"action": self.answer, "content": {"confirm": True}}}) + "\n")
                self.p.stdin.flush()
                continue
            self.q.put(m)

    def rpc(self, method, params=None):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}}) + "\n")
        self.p.stdin.flush()
        while True:
            m = self.q.get(timeout=30)
            if m.get("id") == self.n:
                return m["result"]
            self.q.put(m)  # a notification raced the response; requeue

    def tool(self, tool, **args):
        r = self.rpc("tools/call", {"name": tool, "arguments": args})
        return r["content"][0]["text"], r["isError"]

    def event(self, kind, timeout=30):
        while True:
            m = self.q.get(timeout=timeout)
            if m.get("method") == "notifications/claude/channel":
                print(f"  {self.label} <- {m['params']['meta']}: {m['params']['content'][:80]!r}")
                assert m["params"]["meta"]["kind"] == kind, m
                return m["params"]


def code_of(text):
    return text.split("Pairing code: ")[1].split()[0]


# Happy path
a, b = Peer("A"), Peer("B")
text, err = a.tool("pair_start", name="Alice")
assert not err, text
assert text.startswith("pair · Brought to you by Blackbeard Technologies · https://blackbeard.tech\n"), text
code = code_of(text)
print("code", code)
assert b.tool("send_to_peer", text="too early")[1], "send before pairing must fail"
assert b.tool("send_file", path=__file__)[1], "send_file before pairing must fail"
assert "trust: ask" in b.tool("pair_join", code=code, name="Bob <script>", trust="ask")[0]
assert a.event("pair_request")["meta"]["peer"] == "Bob script"
assert b.tool("send_to_peer", text="before approval")[1], "joiner can't send before approval"
assert not a.tool("pair_accept")[1]
assert b.event("paired")["meta"]["peer"] == "Alice"
IDLE = int(__import__("os").environ.get("PAIR_E2E_IDLE", "0"))  # e.g. 1200 to prove the heartbeat
if IDLE:
    print(f"  idling {IDLE}s")
    __import__("time").sleep(IDLE)
assert not b.tool("send_to_peer", text="hello from bob\u202e")[1]
msg = a.event("message")
assert msg["content"] == "hello from bob" and msg["meta"]["trust"] == "read-only", msg
inbox = a.tool("check_messages")[0]  # no-channel fallback: same events, queued
assert "[pair_request]" in inbox and "hello from bob" in inbox and "State: Paired" in inbox, inbox
assert "No new events" in a.tool("check_messages")[0]
assert not a.tool("send_to_peer", text="hi bob")[1]
msg = b.event("message")
assert msg["content"] == "hi bob" and msg["meta"]["trust"] == "ask", msg
# Files: B sends to A; A saves to its quarantine dir; B hears it was delivered.
import os, tempfile
tmp = tempfile.mkdtemp()
blob = os.urandom(150_000)  # several chunks
src = os.path.join(tmp, "report.bin")
open(src, "wb").write(blob)
text, err = b.tool("send_file", path=src)
assert not err, text
got = a.event("file")
path = got["content"].split("Saved to ")[1].split(". It came")[0]
assert open(path, "rb").read() == blob, "file bytes differ"
if os.name != "nt":
    assert os.stat(path).st_mode & 0o777 == 0o600
assert "report.bin" in b.event("file_delivered")["content"]
b.tool("send_file", path=src)  # same name again: kept, not overwritten
path2 = a.event("file")["content"].split("Saved to ")[1].split(". It came")[0]
assert path2 != path and os.path.exists(path), (path, path2)
b.event("file_delivered")
b.answer = "decline"  # the human says no: nothing is sent
text, err = b.tool("send_file", path=src)
assert not err and "declined" in text, text
b.answer = "accept"
os.makedirs(os.path.join(tmp, ".ssh"))
open(os.path.join(tmp, ".ssh", "id_rsa"), "w").write("not a real key")
text, err = b.tool("send_file", path=os.path.join(tmp, ".ssh", "id_rsa"))
assert err and "secret" in text, text
big = os.path.join(tmp, "big.bin")
open(big, "wb").write(b"x" * (6 * 1024 * 1024))
text, err = b.tool("send_file", path=big)
assert err and "limit" in text, text
for f in (path, path2):
    os.remove(f)
assert not a.tool("unpair")[1]
assert "other side unpaired" in b.event("unpaired")["content"]
assert "you unpaired" in a.event("unpaired")["content"]

# Wrong code burns it on both sides
c, d = Peer("C"), Peer("D")
code = code_of(c.tool("pair_start", name="Carol")[0])
nameplate = code.split("-")[0]
assert not d.tool("pair_join", code=f"{nameplate}-wrong-guess", name="Mallory")[1]
assert "wrong code" in d.event("unpaired")["content"]
assert "wrong code" in c.event("unpaired")["content"]

# Decline
e, f = Peer("E"), Peer("F")
code = code_of(e.tool("pair_start", name="Erin")[0])
f.tool("pair_join", code=code)  # no name: server sends user@host · git name · git email
assert "@" in e.event("pair_request")["meta"]["peer"]
assert not e.tool("pair_reject")[1]
assert "declined" in f.event("unpaired")["content"]

# Monitor path (works without channels): with a live `pair watch` for G's session, G's events go to
# its session inbox and come out of the watcher as single lines, not as channel notifications.
import os, tempfile, time
data = tempfile.mkdtemp()
genv = dict(os.environ, PAIR_DATA=data, CLAUDE_CODE_SESSION_ID="test-session-g")
sdir = os.path.join(data, "sessions", "test-session-g")
w = subprocess.Popen([BIN, "watch", data], env=genv, stdout=subprocess.PIPE, text=True)
wq = queue.Queue()
threading.Thread(target=lambda: [wq.put(l.rstrip("\n")) for l in w.stdout], daemon=True).start()
time.sleep(1)  # first heartbeat
g, h = Peer("G", env=genv), Peer("H")
code = code_of(g.tool("pair_start", name="Gina")[0])
h.tool("pair_join", code=code, name="Hal")
line = wq.get(timeout=30)
print("  watch <-", line[:90])
assert line.startswith('pair pair_request from "Hal": '), line
assert not g.tool("pair_accept")[1]
h.event("paired")
assert not h.tool("send_to_peer", text="line1\nline2")[1]
line = wq.get(timeout=30)
print("  watch <-", line)
assert line == 'pair message from "Hal" (trust: read-only): "line1\\nline2"', line
assert not any(m.get("method") == "notifications/claude/channel" for m in list(g.q.queue)), "G got a channel notification too"
if os.name != "nt":
    assert os.stat(os.path.join(sdir, "inbox.jsonl")).st_mode & 0o777 == 0o600
g.tool("unpair")
h.event("unpaired")
g.p.stdin.close()
g.p.wait(10)
assert not os.path.exists(sdir), "session dir not removed at session end"
w.kill()

print("PASS")
