---
name: feedback
description: Report a bug, ask for a feature, or send feedback about pair as a GitHub issue on blackbeard-tech/pair. Use when the user says /pair:feedback, "report this", "file a bug", "this is broken", "pair should…", or complains about pair.
argument-hint: "[what happened or what you want]"
---

Turn the user's feedback into a GitHub issue that a maintainer can act on without asking anything back:
short, specific and complete. The user may give only a few words ($ARGUMENTS). Do the work for them.

## 1. Gather the facts

Find out what you can yourself; don't ask the user for it:
- **pair version:** the installed plugin's version.
- **Claude Code version** and **OS**.
- **Where it ran:** terminal, desktop app Code tab, VS Code or another IDE, `claude -p`, or a phone through Remote Control.
- **Permission mode**, and the trust level if paired.
- **What happened:** the exact error or message text, word for word, from this conversation or the tool results.
- **Steps:** what was done just before, from this conversation.

Ask the user only for what you still can't tell, usually what they expected instead, and ask everything in one
message. Don't guess at causes. If you checked something (read the code, reproduced it), say what you found and how.

## 2. One issue per problem

If the feedback covers several unrelated things, write a separate issue for each, and say so to the user. Before
writing, look for an existing open issue on the same thing. If there is one, draft a comment that adds only what's
new instead of a new issue.

## 3. Write it

**Title:** the symptom or the request in plain words, under 80 characters, for example `send_file times out on
files over 25 MB through the transit relay`. Not `Bug`, `Problem with pair` or `Feedback`.

**Bug body.** Use only the sections that have something in them:

```
**What happened:** one to three sentences, with the exact error quoted.
**Expected:** one sentence.
**Steps:**
1. …
**Environment:** pair 0.1.12 · Claude Code 2.1.309 · macOS 26.1 · desktop app Code tab · auto mode · trust read-only
**Logs:** only the lines that matter, in a code block.
```

**Feature or feedback body:** the problem it solves (one or two sentences, with the real situation it came from),
what they want, and anything they've already tried.

Leave out greetings, thanks, apologies, background the maintainer doesn't need, guesses presented as facts, and
any sentence that repeats another. If a sentence can go without losing information, take it out.

## 4. Keep private things out

The repo is public. Remove or replace with placeholders: people's names, email addresses, usernames and hostnames
(including inside paths, such as `/Users/<name>/`), pairing codes, the content of peer messages and files,
project names and code that aren't the user's to share, and anything that looks like a token, key or password.
Display names such as `user@host · name · email` count as private.

## 5. Confirm, then post

Show the user the exact title and body, and post only after they say yes. Post to
https://github.com/blackbeard-tech/pair/issues (with `gh issue create` if it's installed and signed in;
otherwise give the user a new-issue link with the title and body filled in). Give them the issue's link at the end.
