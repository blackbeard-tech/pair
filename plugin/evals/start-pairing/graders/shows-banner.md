---
type: regex
target: trace
# Claude's own text (the tool result also contains the banner, on a "user" line)
pattern: '"role":"assistant"[^\n]*By Blackbeard Technologies'
---
