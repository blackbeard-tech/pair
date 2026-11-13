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
    scroll: { offset: 0, bodyRows: 30 },
    view: {},
  },
} as const

const DATA = '/home/u/.claude/plugins/data'
const DIR = `${DATA}/pair-inline/sessions/S1`
const line = (kind: string, peer: string, content: string, trust?: string) =>
  `${JSON.stringify({ meta: { kind, peer, ...(trust ? { trust } : {}) }, content })}\n`

/** The engine beneath: a session id, a file system in memory, pair's MCP tools. */
function world(on: On) {
  const files: Record<string, string> = { [`${DIR}/inbox.jsonl`]: '' }
  const calls: { tool: string; args: unknown }[] = []
  const w = { files, calls, isUp: true } // isUp: pair has made this session's folder
  mock.env(on, { HOME: '/home/u' })
  const clock = mock.clock(on)
  on('session.id', () => ({ value: 'S1' }))
  on('command.register', () => ({ value: { command: 'pair-pane' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.toast', () => ({ value: undefined }))
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
    calls.push({ tool: e.tool, args: e.args })
    return { value: { content: [{ type: 'text', text: `${e.tool} ok` }], isError: false } }
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  return { ...w, w, clock }
}

test('a pairing request, Accept, then a message', async ($, on) => {
  const w = world(on)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  w.files[`${DIR}/inbox.jsonl`] += line('pair_request', 'u@h · Ann · a@x', 'Someone named …')
  await w.clock.advance(1000)

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Text', text: /Ann wants to pair/ }))?.text).toBe('Ann wants to pair.')
    expect(await ui.find({ key: 'accept' })).toBeDefined()
    await ui.unmount()
  }

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'accept' })
  expect(w.calls).toEqual([{ tool: 'pair_accept', args: {} }])
  expect((await ui.find({ type: 'Text', text: /Paired with Ann/ }))?.text).toBe('Paired with Ann · trust: read-only')

  w.files[`${DIR}/inbox.jsonl`] += line('message', 'u@h · Ann · a@x', 'hello there', 'ask')
  await w.clock.advance(1000)
  expect(await ui.find({ type: 'Text', text: /hello there/ })).toBeDefined()
  expect(await ui.find({ key: 'hand-in-1' })).toBeDefined()
  await ui.unmount()
})

test('chat goes to the outbox with an id, earlier lines kept', async ($, on) => {
  const w = world(on)
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  w.files[`${DIR}/inbox.jsonl`] += line('paired', 'u@h · Bo · b@x', 'Bo accepted.')
  await w.clock.advance(1000)

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.input({ key: 'chat', text: 'first' })
  await ui.input({ key: 'chat', text: 'second' })
  const sent = w.files[`${DIR}/outbox.jsonl`]!.trim().split('\n').map(l => JSON.parse(l))
  expect(sent.map(m => m.text)).toEqual(['first', 'second'])
  expect(new Set(sent.map(m => m.id)).size).toBe(2)
  expect(await ui.find({ type: 'Text', text: /You:.*second/ })).toBeDefined()
  await ui.unmount()
})

test('pair starts after the pane: it says so, then finds the session', async ($, on) => {
  const env = world(on)
  env.w.isUp = false
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await env.clock.advance(1000)

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /isn’t running in this session/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /Not paired/ })).toBeDefined()

  env.w.isUp = true
  env.files[`${DIR}/inbox.jsonl`] += line('pair_request', 'u@h · Cy · c@x', 'Someone named …')
  await env.clock.advance(1000)
  expect(await ui.find({ type: 'Text', text: /isn’t running in this session/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /Cy wants to pair/ })).toBeDefined()
  await ui.unmount()
})
