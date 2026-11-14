/**
 * One row of the pane. `kind` is an inbox event's kind (message, file, pair_request, paired, connection, unpaired,
 * file_failed, outbox_failed, ...), or one the pane adds itself: `sent` (typed in the pane), `claude` (your Claude's
 * send_to_peer), `sent-file` (a file you or your Claude sent).
 */
export type PairEvent = {
  id: string
  kind: string
  /** Who it's from: the peer's name, or '' for your side. */
  peer: string
  text: string
  /** When the pane first saw it, ms. */
  at: number
  trust?: string
  via?: string
  /** Files: name, size in bytes, and where it was saved (received) or read from (sent). */
  name?: string
  size?: number
  path?: string
  /** A sent file the peer confirmed. */
  delivered?: boolean
  /** When you handed it to Claude, ms. */
  handedAt?: number
}

export type PairStatus = {
  phase: 'idle' | 'request' | 'paired' | 'reconnecting'
  /** The peer's identity as the server gives it: user@host · git name · git email. */
  peer?: string
  trust?: string
  via?: string
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
      /** Rows that arrived after this (ms) are new. */
      seenAt: number
      tab: 'chat' | 'files'
      /** The pane is placed on a surface (the band above the prompt shows while it isn't). */
      paneOpen: boolean
    }
  }
}
