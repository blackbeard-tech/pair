"""Claude Desktop runs two pair servers for one chat: Claude's calls reach one, the pair pane's the other. This starts
two servers as Desktop would (MCP Apps announced, a shared temp dir), starts a pairing on one, and checks the other
sees it (pair_inbox) and can end it (unpair): one runs pairings, the other forwards to it.
Usage: python3 -I server/tests/desktop_two_servers.py server/target/release/pair"""
import json, os, subprocess, sys, tempfile, time

exe = sys.argv[1]
tmp = tempfile.mkdtemp()
env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_SESSION_ID", "PAIR_DATA")}
env.update(TMPDIR=tmp, TEMP=tmp, TMP=tmp, PAIR_DESKTOP="1")  # a temp dir of its own: never the real Desktop's
INIT = {"protocolVersion": "2025-06-18", "clientInfo": {"name": "claude-ai", "version": "1"},
        "capabilities": {"extensions": {"io.modelcontextprotocol/ui": {"mimeTypes": ["text/html;profile=mcp-app"]}}}}


class Server:
    def __init__(self):
        self.p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  text=True, env=env)
        self.n = 0
        self.rpc("initialize", INIT)

    def rpc(self, method, params=None):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}}) + "\n")
        self.p.stdin.flush()
        while True:
            m = json.loads(self.p.stdout.readline())
            if m.get("id") == self.n:
                return m["result"]

    def tool(self, name, args=None):
        return self.rpc("tools/call", {"name": name, "arguments": args or {}})


a, b = Server(), Server()
time.sleep(2.5)  # the engine heartbeat settles on one of them
r = a.tool("pair_start")
text = r["content"][0]["text"]
assert not r.get("isError"), text
print("A started:", text.splitlines()[1][:80])
for s, name in ((a, "A"), (b, "B")):
    st = s.tool("pair_inbox", {"since": 0})["structuredContent"]
    assert st["state"] == "Waiting", (name, st)
print("both servers see Waiting")
r = b.tool("unpair")
assert not r.get("isError"), r
time.sleep(0.5)
assert a.tool("pair_inbox", {"since": 0})["structuredContent"]["state"] == "Idle"
print("unpair from B ended A's pairing")
r = b.tool("reveal_file", {"path": "/etc/hosts"})
assert r["isError"] and "Only received files" in r["content"][0]["text"], r
print("reveal_file refuses a path outside the received folder")
# Without PAIR_DESKTOP (any other pair server of this user) a server never joins Desktop's pairing.
env.pop("PAIR_DESKTOP")
c = Server()
assert c.tool("pair_start")["isError"] is False
assert c.tool("pair_inbox", {"since": 0})["structuredContent"]["state"] == "Waiting"
assert a.tool("pair_inbox", {"since": 0})["structuredContent"]["state"] == "Idle", "a non-Desktop server joined Desktop's pairing"
c.tool("unpair")
c.p.stdin.close()
print("a server without PAIR_DESKTOP stays out")
for s in (a, b):
    s.p.stdin.close()
    s.p.wait(timeout=10)
print("PASS")
