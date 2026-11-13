/** One row of the pane: an inbox event, or a message typed in the pane (`kind: 'sent'`). */
export type PairEvent = { id: string; kind: string; peer: string; text: string; trust?: string }

export type PairStatus = {
  phase: 'idle' | 'request' | 'paired' | 'reconnecting'
  peer?: string
  trust?: string
}

declare module 'claude-code' {
  interface PluginState {
    pair: {
      events: Shaped<PairEvent[]>
      status: Shaped<PairStatus>
      /** Complete inbox lines already read. */
      seen: number
      /** This session's pair folder (inbox.jsonl, outbox.jsonl), or '' when pair isn't running here. */
      dir: string
    }
  }
}
