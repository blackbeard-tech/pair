"""End-to-end: two `pair` MCP servers pair (setup over the relay mailbox,
then transit) and exchange messages and files.

Usage: python3 -I server/tests/two_peers.py server/target/release/pair
Stdlib only. Uses the public relay (needs network) unless PAIR_RELAY points at a local mailbox server.
"""

import json
import os
import queue
import subprocess
import tempfile
import sys
import threading
import time

BIN = sys.argv[1]


class Peer:
    def __init__(self, label, env=None, client="t"):
        self.label, self.n = label, 0
        # Events go to <PAIR_DATA>/sessions/<session id>/inbox.jsonl (what the monitor, hooks and pair wait read).
        env = env or dict(os.environ, PAIR_DATA=tempfile.mkdtemp(), CLAUDE_CODE_SESSION_ID=f"test-{label}")
        if "PAIR_DATA" in env and "CLAUDE_CODE_SESSION_ID" in env:  # Codex passes neither: no inbox file
            self.inbox = os.path.join(env["PAIR_DATA"], "sessions", env["CLAUDE_CODE_SESSION_ID"], "inbox.jsonl")
        self.seen = 0
        self.answer = "accept"  # reply to elicitation dialogs (the human's yes/no)
        self.p = subprocess.Popen([BIN], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
        self.q = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()
        r = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {"elicitation": {}}, "clientInfo": {"name": client}})
        assert r["capabilities"] == {"tools": {}}, r  # no channel, no permission relay

    def _read(self):
        for line in self.p.stdout:
            m = json.loads(line)
            if m.get("method") == "elicitation/create":  # play the human
                if self.answer == "decline-slow":
                    time.sleep(2)  # a person reading the dialog
                action = "decline" if self.answer.startswith("decline") else self.answer
                self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": m["id"],
                    "result": {"action": action, "content": {}}}) + "\n")
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

    def tool(self, tool, meta=None, **args):
        r = self.rpc("tools/call", {"name": tool, "arguments": args, **({"_meta": meta} if meta else {})})
        return r["content"][0]["text"], r["isError"]

    def event(self, kind, timeout=30):
        """The next event in this peer's inbox (skipping the hook probe); it must be `kind`."""
        end = time.time() + timeout
        while time.time() < end:
            try:
                lines = open(self.inbox).read().splitlines()
            except FileNotFoundError:
                lines = []
            for line in lines[self.seen:]:
                self.seen += 1
                e = json.loads(line)
                if e["meta"]["kind"] == "probe":
                    continue
                print(f"  {self.label} <- {e['meta']}: {e['content'][:80]!r}")
                assert e["meta"]["kind"] == kind, e
                return e
            time.sleep(0.1)
        raise TimeoutError(f"{self.label}: no {kind} event within {timeout}s")


def code_of(text):
    return text.split("Pairing code: ")[1].split()[0]


# Happy path
a, b = Peer("A"), Peer("B")
text, err = a.tool("pair_start", name="Alice")
assert not err, text
assert text.startswith("pair · By Blackbeard Technologies · https://blackbeard.tech\n"), text
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
inbox = a.tool("check_messages")[0]  # claude -p fallback: same events, queued
assert "[pair_request]" in inbox and "hello from bob" in inbox and "State: Paired" in inbox, inbox
assert "No new events" in a.tool("check_messages")[0]
assert not a.tool("send_to_peer", text="hi bob")[1]
msg = b.event("message")
assert msg["content"] == "hi bob" and msg["meta"]["trust"] == "ask", msg
# The pair pane (mod) sends chat by appending to the session's outbox (pair-cvl.7)
ob = os.path.join(os.path.dirname(a.inbox), "outbox.jsonl")
with open(ob, "a") as f:
    f.write(json.dumps({"id": "p0", "text": "from the pane"}) + "\n")
msg = b.event("message")
assert msg["content"] == "from the pane", msg
# A mod can only rewrite the whole file; a rewrite caught half-way (empty file) must not resend earlier lines.
old = open(ob).read()
open(ob, "w").close()
time.sleep(1.5)
open(ob, "w").write(old + json.dumps({"id": "p1", "text": "pane again"}) + "\n")
assert b.event("message")["content"] == "pane again"  # not "from the pane" a second time
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
b.answer = "decline-slow"  # the human says no: nothing is sent
text, err = b.tool("send_file", path=src)
assert not err and "declined" in text, text
b.answer = "decline"  # declined faster than anyone can click: the app answered, nobody was asked
text, err = b.tool("send_file", path=src)
assert err and "Couldn't ask" in text, text
b.answer = "accept"
os.makedirs(os.path.join(tmp, ".ssh"))
open(os.path.join(tmp, ".ssh", "id_rsa"), "w").write("not a real key")
text, err = b.tool("send_file", path=os.path.join(tmp, ".ssh", "id_rsa"))
assert err and "secret" in text, text
mid = os.path.join(tmp, "mid.bin")  # over the old 5 MB limit: streams now
mblob = os.urandom(6 * 1024 * 1024)
open(mid, "wb").write(mblob)
assert not b.tool("send_file", path=mid)[1]
got = a.event("file", timeout=90)["content"].split("Saved to ")[1].split(". It came")[0]
assert open(got, "rb").read() == mblob, "6 MB file differs"
b.event("file_delivered", timeout=90)
os.remove(got)
big = os.path.join(tmp, "big.bin")  # sparse: over the 100 MB direct limit without writing 100 MB
with open(big, "wb") as f:
    f.truncate(101 * 1024 * 1024)
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

# Unpair while waiting for the other side ends it at once, so pair_start works straight after (GitHub #7)
w = Peer("W")
w.tool("pair_start")
text, err = w.tool("unpair")
assert not err and text == "Unpaired.", text
assert "you unpaired" in w.event("unpaired")["content"]
inbox = w.tool("check_messages")[0]
assert "[unpaired]:" in inbox and "from :" not in inbox, inbox  # no peer yet: no "from" (GitHub #8)
with open(os.path.join(os.path.dirname(w.inbox), "outbox.jsonl"), "a") as f:
    f.write(json.dumps({"text": "nobody to send to"}) + "\n")
assert "not paired" in w.event("outbox_failed")["content"]
assert not w.tool("pair_start")[1], "pair_start right after unpair must work"
w.tool("unpair")

# Codex: no hooks or monitor, so pair runs `codex queue` to wake the chat that started the pairing. Fixed text,
# never peer content, once until check_messages. A fake codex records its arguments. (GitHub #6)
if os.name != "nt":
    cdir = tempfile.mkdtemp()
    fake, log = os.path.join(cdir, "codex"), os.path.join(cdir, "codex.log")
    open(fake, "w").write("#!/usr/bin/env python3\nimport json, os, sys\n"
                          "open(os.environ['FAKE_CODEX_LOG'], 'a').write(json.dumps(sys.argv[1:]) + '\\n')\n")
    os.chmod(fake, 0o755)

    def wakes(n):
        """Wait for the nth wake, then make sure no extra one follows."""
        end = time.time() + 15
        while time.time() < end:
            got = [json.loads(l) for l in open(log)] if os.path.exists(log) else []
            if len(got) >= n:
                time.sleep(1)
                got = [json.loads(l) for l in open(log)]
                assert len(got) == n, got
                return got
            time.sleep(0.1)
        raise TimeoutError(f"no wake #{n}")

    # Codex passes HOME and PATH but not CLAUDE_CODE_SESSION_ID or a plugin data dir.
    cenv = {k: v for k, v in os.environ.items() if k not in ("PAIR_DATA", "CLAUDE_CODE_SESSION_ID")}
    cx = Peer("CX", env=dict(cenv, PAIR_CODEX_BIN=fake, FAKE_CODEX_LOG=log), client="codex-mcp-client")
    thread = "0199a0c4-7b1e-7f00-8000-123456789abc"
    text, err = cx.tool("pair_start", meta={"threadId": thread}, name="Cody")
    assert not err and "[pair] notice" in text, text
    cl = Peer("CL")
    cl.tool("pair_join", code=code_of(text), name="Cleo")
    w = wakes(1)[0]
    assert w[:4] == ["queue", "--thread", thread, "--message"] and "check_messages" in w[4], w
    assert "[pair_request] from Cleo" in cx.tool("check_messages")[0]
    assert not cx.tool("pair_accept")[1]
    cl.event("paired")
    assert not cl.tool("send_to_peer", text="secret one")[1]
    assert not cl.tool("send_to_peer", text="secret two")[1]
    got = wakes(2)  # two messages, one wake
    assert not any("secret" in a for w in got for a in w), got
    inbox = cx.tool("check_messages")[0]
    assert "secret one" in inbox and "secret two" in inbox, inbox
    cl.tool("unpair")
    wakes(3)  # woken again after check_messages
    assert "other side unpaired" in cx.tool("check_messages")[0]

# Monitor path: with a live `pair watch` for G's session, G's events go to its session inbox and
# come out of the watcher as single lines.
import os, tempfile, time
data = tempfile.mkdtemp()
genv = dict(os.environ, PAIR_DATA=data, CLAUDE_CODE_SESSION_ID="test-session-g")
sdir = os.path.join(data, "sessions", "test-session-g")
w = subprocess.Popen([BIN, "watch", data], env=genv, stdout=subprocess.PIPE, text=True)
wq = queue.Queue()
threading.Thread(target=lambda: [wq.put(l.rstrip("\n")) for l in w.stdout], daemon=True).start()
time.sleep(1)  # first heartbeat
g, h = Peer("G", env=genv), Peer("H")
text = g.tool("pair_start", name="Gina")[0]
assert "Live delivery: active" in text, text
code = code_of(text)
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
if os.name != "nt":
    assert os.stat(os.path.join(sdir, "inbox.jsonl")).st_mode & 0o777 == 0o600
g.tool("unpair")
h.event("unpaired")
w.kill()  # first: its 10 s heartbeat recreates the session dir (with only watch.alive in it)
w.wait(10)
g.p.stdin.close()
g.p.wait(10)
assert not os.path.exists(sdir), "session dir not removed at session end"

# No monitor (desktop app / IDE hosts): pair_start says so and hands Claude a `pair wait` command that
# exits with the next event(s); nothing sent while no wait is running is lost.
import re, shlex
kenv = dict(os.environ, PAIR_DATA=tempfile.mkdtemp(), CLAUDE_CODE_SESSION_ID="test-session-k")
k, l = Peer("K", env=kenv), Peer("L")
text = k.tool("pair_start", name="Kim")[0]
assert "Live delivery: NOT set up" in text, text
cmd = shlex.split(re.search(r'(".+?" wait ".+?")', text).group(1))
def wait_once(timeout=30):
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip().splitlines()
    print("  wait ->", [o[:70] for o in out])
    return out
waiter = threading.Thread(target=lambda: setattr(waiter, "out", wait_once()))
waiter.start()
l.tool("pair_join", code=code_of(text), name="Lou")
waiter.join(40)
assert waiter.out and waiter.out[0].startswith('pair pair_request from "Lou"'), waiter.out
assert not k.tool("pair_accept")[1]
l.event("paired")
assert not l.tool("send_to_peer", text="one")[1]
assert not l.tool("send_to_peer", text="two")[1]
time.sleep(3)  # both land while no wait is running
out = wait_once()
assert [o.rsplit(": ", 1)[1] for o in out] == ['"one"', '"two"'], out
text, err = k.tool("send_to_peer", text="hi")
assert not err and "Nothing is listening" in text, text
assert l.event("message")["content"] == "hi"
k.tool("unpair")
l.event("unpaired")

# Plugin hooks (desktop app / IDEs): emulate Claude Code. SessionStart names the inbox to watch; on each
# change, FileChanged runs `pair hook inbox`, and exit code 2 wakes Claude with its stderr.
hdata, hsid = tempfile.mkdtemp(), "test-session-hooks"
out = subprocess.run([BIN, "hook", "session-start", hdata], input=json.dumps({"session_id": hsid}),
                     capture_output=True, text=True, timeout=10)
watched = json.loads(out.stdout)["hookSpecificOutput"]["watchPaths"][0]
assert watched.endswith(os.path.join("sessions", hsid, "inbox.jsonl")), watched
wakes = queue.Queue()
def fire(path):
    r = subprocess.run([BIN, "hook", "inbox", hdata], capture_output=True, text=True, timeout=30,
                       input=json.dumps({"session_id": hsid, "file_path": path, "event": "change"}))
    return r.returncode, r.stderr.strip().splitlines()
def file_watcher():
    size = 0
    while True:
        n = os.path.getsize(watched) if os.path.exists(watched) else 0
        if n != size:
            size = n
            rc, lines = fire(watched)
            if rc == 2:
                wakes.put(lines)
        time.sleep(0.1)
threading.Thread(target=file_watcher, daemon=True).start()
henv = dict(os.environ, PAIR_DATA=hdata, CLAUDE_CODE_SESSION_ID=hsid)
m, n = Peer("M", env=henv), Peer("N")
text = m.tool("pair_start", name="Mia")[0]
assert "Live delivery: active (plugin hooks" in text, text
n.tool("pair_join", code=code_of(text), name="Ned")
w = wakes.get(timeout=30)
print("  hook wake ->", [x[:60] for x in w])
assert w[0].startswith('pair pair_request from "Ned"'), w
# pair_accept and send_file are confirmed through their requiresUserInteraction flag.
flagged = {t["name"] for t in m.rpc("tools/list")["tools"] if t.get("_meta", {}).get("anthropic/requiresUserInteraction") is True}
assert flagged == {"pair_accept", "send_file"}, flagged
assert not m.tool("pair_accept")[1]
n.event("paired")
n.tool("send_to_peer", text="one")
assert wakes.get(timeout=30) == ['pair message from "Ned" (trust: read-only): "one"']
sdir = os.path.dirname(watched)
open(os.path.join(sdir, "watch.alive"), "w").close()  # a terminal monitor is delivering
n.tool("send_to_peer", text="two")
time.sleep(3)
assert wakes.empty(), "hook must stay silent while the monitor delivers"
os.remove(os.path.join(sdir, "watch.alive"))
n.tool("send_to_peer", text="three")
assert wakes.get(timeout=30) == ['pair message from "Ned" (trust: read-only): "three"'], "no re-delivery of two"
assert fire(os.path.join(tempfile.mkdtemp(), "inbox.jsonl"))[0] == 0  # a project-folder inbox.jsonl is ignored
m.tool("unpair")
n.event("unpaired")
time.sleep(1)

# Resume: a stalled connection reconnects by itself on a code both sides derive, with no new approval.
# A frozen process (SIGSTOP) stands in for a laptop asleep or off the network. PAIR_TEST_FAST shortens the timers.
if os.name != "nt":
    import signal
    fenv = lambda label: dict(os.environ, PAIR_DATA=tempfile.mkdtemp(), CLAUDE_CODE_SESSION_ID=f"test-{label}",
                              PAIR_TEST_FAST="1")
    r, s = Peer("R", env=fenv("R")), Peer("S", env=fenv("S"))
    s.tool("pair_join", code=code_of(r.tool("pair_start", name="Rae")[0]), name="Sol")
    r.event("pair_request")
    assert not r.tool("pair_accept")[1]
    s.event("paired")
    os.kill(s.p.pid, signal.SIGSTOP)
    assert "dropped" in r.event("connection", timeout=20)["content"]
    text, err = r.tool("send_to_peer", text="while you were away")
    assert not err and text.startswith("queued"), text
    time.sleep(2)
    os.kill(s.p.pid, signal.SIGCONT)
    assert "dropped" in s.event("connection", timeout=20)["content"]
    assert "Reconnected" in s.event("connection", timeout=40)["content"]
    assert "Reconnected" in r.event("connection", timeout=40)["content"]
    assert s.event("message")["content"] == "while you were away"
    assert not s.tool("send_to_peer", text="back")[1]
    assert r.event("message")["content"] == "back"
    # Claude Code closing a session says bye, so the peer ends at once instead of trying to reconnect.
    r.p.stdin.close()
    assert "other side unpaired" in s.event("unpaired", timeout=10)["content"]

print("PASS")
