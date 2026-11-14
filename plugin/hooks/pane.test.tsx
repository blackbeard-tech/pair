import type { On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'

const PANE = {
  plugin: 'pair',
  component: 'Pane',
  requestId: 'pair',
  props: {
    title: 'pair',
    isFocused: false,
    bodyColumns: 60,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
} as const
const BAND = {
  plugin: 'pair',
  component: 'AbovePrompt',
  props: { bodyColumns: 120, hasSurvey: false, isWorking: false, maxRows: 3, scroll: { offset: 0, bodyRows: 3 }, view: {} },
} as const

const DATA = '/home/u/.claude/plugins/data'
const DIR = `${DATA}/pair-inline/sessions/S1`
const ANN = 'u@h · Ann · a@x'
const line = (kind: string, content: string, meta: Record<string, unknown> = {}) =>
  `${JSON.stringify({ meta: { kind, peer: ANN, ...meta }, content })}\n`

/** The engine beneath: a session id, a file system in memory, pair's MCP tools, the pane's placement. */
function world(on: On) {
  const files: Record<string, string> = { [`${DIR}/inbox.jsonl`]: '' }
  const w = {
    files,
    calls: [] as { tool: string; args: unknown }[],
    prompts: [] as string[],
    opened: 0,
    isUp: true, // pair has made this session's folder
    isPlaced: true, // a surface places the pane when opened
  }
  mock.env(on, { HOME: '/home/u' })
  const clock = mock.clock(on, { now: Date.UTC(2026, 10, 14, 14, 2) })
  on('session.id', () => ({ value: 'S1' }))
  on('command.register', () => ({ value: { command: 'pair-pane' } }))
  on('process.run', () => ({
    value: { exitCode: 0, stdout: 'Darwin\n', stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
  }))
  on('ui.open', () => {
    w.opened++
    return { value: w.isPlaced ? { isPlaced: true as const } : { isPlaced: false as const, reason: '144 columns' } }
  })
  on('ui.toast', () => ({ value: undefined }))
  on('ui.status', () => ({ value: undefined }))
  on('fs.exists', (_, e) => ({ value: e.path === DATA || (w.isUp && (e.path === DIR || e.path in files)) }))
  on('fs.list', () => ({
    value: ['other-plugin', 'pair-inline'].map(name => ({ name, kind: 'dir' as const, size: 0, mtimeMs: 0, isLink: false })),
  }))
  on('fs.read', (_, e) => {
    const text = w.isUp ? files[e.path] : undefined
    if (text === undefined) throw new Error('missing')
    return { value: text }
  })
  on('fs.write', (_, e) => {
    files[e.path] = e.text
    return { value: undefined }
  })
  on('mcp.call', (_, e) => {
    w.calls.push({ tool: e.tool, args: e.args })
    return { value: { content: [{ type: 'text', text: `${e.tool} ok` }], isError: false } }
  })
  on('prompt.submit', (_, e) => {
    w.prompts.push(e.text)
    return { text: e.text }
  })
  on('tool.call', () => ({ result: {} }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  return { w, clock, inbox: (s: string) => (files[`${DIR}/inbox.jsonl`] += s) }
}

test('a pairing request, Accept, then a message handed to Claude', async ($, on) => {
  const { w, clock, inbox } = world(on)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  inbox(line('pair_request', 'Someone named …'))
  await clock.advance(1000)

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect(await ui.find({ type: 'Text', text: /Ann wants to pair/ })).toBeDefined()
    expect(await ui.find({ key: 'accept' })).toBeDefined()
    await ui.unmount()
  }

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'accept' })
  expect(w.calls).toEqual([{ tool: 'pair_accept', args: {} }])
  expect(await ui.find({ type: 'Text', text: /trust: read-only/ })).toBeDefined()

  inbox(line('message', 'hello there', { trust: 'ask', via: 'direct' }))
  await clock.advance(1000)
  expect(await ui.find({ type: 'Text', text: /hello there/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /· direct/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^ new$/ })).toBeDefined()
  await ui.press({ key: 'hand-in-1' })
  expect(w.prompts[0]).toMatch(/^pair · message from Ann, handed to Claude by you\nhello there/)
  expect(await ui.find({ type: 'Text', text: /handed to Claude \d\d:\d\d/ })).toBeDefined()
  await ui.unmount()
})

test('chat goes to the outbox with an id, earlier lines kept', async ($, on) => {
  const { w, clock, inbox } = world(on)
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  inbox(line('paired', 'Ann accepted.'))
  await clock.advance(1000)

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /sent as you, not via Claude/ })).toBeDefined()
  await ui.input({ key: 'chat', text: 'first' })
  await ui.input({ key: 'chat', text: 'second' })
  const sent = w.files[`${DIR}/outbox.jsonl`]!.trim().split('\n').map(l => JSON.parse(l))
  expect(sent.map(m => m.text)).toEqual(['first', 'second'])
  expect(new Set(sent.map(m => m.id)).size).toBe(2)
  expect(await ui.find({ type: 'Text', text: /^second$/ })).toBeDefined()
  await ui.unmount()
})

test("Claude's own messages and files show as yours", async ($, on) => {
  const { clock, inbox } = world(on)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  inbox(line('paired', 'Ann accepted.'))
  await clock.advance(1000)
  await $.tool.call({ tool: 'mcp__plugin_pair_pair__send_to_peer', text: 'patch incoming' })

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /^your Claude$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^patch incoming$/ })).toBeDefined()
  await ui.unmount()
})

test('Files tab: received file with Open, Reveal and → Claude; f switches to it', async ($, on) => {
  const { clock, inbox } = world(on)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  inbox(line('paired', 'Ann accepted.'))
  inbox(line('file', 'Ann sent a file …', { name: 'upload-fail.har', size: 2_200_000, path: '/r/upload-fail.har' }))
  await clock.advance(1000)

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'tab-files' })
  expect(await ui.find({ type: 'Text', text: /Received from Ann/ })).toBeDefined()
  for (const key of ['open-in-1', 'reveal-in-1', 'hand-in-1']) expect(await ui.find({ key })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /Shared files/ })).toBeDefined()
  await ui.unmount()
})

test('pane closed: the band shows what is new; Open pane opens it and the band goes', async ($, on) => {
  const { w, clock, inbox } = world(on)
  w.isPlaced = false // too narrow to dock: the band is how the person hears
  // The engine's own band, drawn when pair has nothing to show there.
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  inbox(line('paired', 'Ann accepted.'))
  await clock.advance(1000)
  inbox(line('message', 'No rush on the retry one.'))
  await clock.advance(1000)

  const band = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await band.find({ type: 'Text', text: /^1 new$/ })).toBeDefined()
  expect(await band.find({ type: 'Text', text: /No rush on the retry one/ })).toBeDefined()
  w.isPlaced = true
  const before = w.opened // the paired event already tried once, unasked
  await band.press({ key: 'open' })
  expect(w.opened).toBe(before + 1)
  expect(await band.find({ key: 'open' })).toBeUndefined()
  expect(await band.find({ type: 'Text', text: 'engine' })).toBeDefined()
  await band.unmount()
})

test('pair starts after the pane: it says so, then finds the session; mobile has no input', async ($, on) => {
  const { w, clock, inbox } = world(on)
  w.isUp = false
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await clock.advance(1000)

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /isn’t running in this session/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^Not paired\.$/ })).toBeDefined()

  w.isUp = true
  inbox(line('pair_request', 'Someone named …'))
  await clock.advance(1000)
  expect(await ui.find({ type: 'Text', text: /isn’t running in this session/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /Ann wants to pair/ })).toBeDefined()
  await ui.unmount()

  inbox(line('paired', 'Ann accepted.'))
  await clock.advance(1000)
  const phone = await $.ui.mount({ ...PANE, surface: 'mobile' })
  expect(await phone.find({ key: 'chat' })).toBeUndefined()
  await phone.unmount()
})
