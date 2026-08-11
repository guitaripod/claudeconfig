/** @jsxImportSource @opentui/solid */
import { createMemo, createSignal } from "solid-js"
import type { TuiPlugin } from "@opencode-ai/plugin/tui"

const [clock, setClock] = createSignal(Date.now())
setInterval(() => {
  try {
    const { appendFileSync } = require("node:fs")
    appendFileSync("/tmp/usage-dbg.log", `${new Date().toISOString()} tick\n`)
  } catch {}
  setClock(Date.now())
}, 1000)

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 3 })
const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 })

function fmtTokens(n: number): string {
  return compact.format(n).toLowerCase()
}

function fmtElapsed(secs: number): string {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  const mm = h > 0 ? String(m).padStart(2, "0") : String(m)
  const ss = String(s).padStart(2, "0")
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

function UsageView(props: { api: Parameters<TuiPlugin>[0]; session_id: string }) {
  const api = props.api

  const session = createMemo(() => api.state.session.get(props.session_id))
  const messages = createMemo(() => api.state.session.messages(props.session_id))
  const status = createMemo(() => api.state.session.status(props.session_id))

  const completed = createMemo(() => {
    const msg = messages()
    return msg?.findLast((m) => m.role === "assistant" && m.tokens?.output > 0)
  })

  const context = createMemo(() => {
    const last = completed()
    if (!last) return null
    const tokens =
      last.tokens.input + last.tokens.output + last.tokens.reasoning + last.tokens.cache.read + last.tokens.cache.write
    const model = api.state.provider.find((p) => p.id === last.providerID)?.models[last.modelID]
    const base = fmtTokens(tokens)
    if (!model?.limit?.context) return base
    return `${base}/${fmtTokens(model.limit.context)} (${Math.round((tokens / model.limit.context) * 100)}%)`
  })

  const timer = createMemo(() => {
    if (status()?.type !== "busy") return null
    const msg = messages()
    const running = msg?.findLast((m) => m.role === "assistant" && !m.time.completed)
    if (!running) return null
    return fmtElapsed(Math.max(0, Math.floor((clock() - running.time.created) / 1000)))
  })

  const cost = createMemo(() => session()?.cost ?? 0)

  return (
    <text fg={api.theme.current.textMuted} wrapMode="none">
      USAGE·{timer() !== null ? `${timer()} · ` : ""}
      {context() !== null ? `${context()} · ` : ""}
      {money.format(cost())} · c:{Math.floor(clock() / 1000) % 1000}
    </text>
  )
}

const tui: TuiPlugin = async (api) => {
  api.slots.register({
    order: 100,
    slots: {
      session_prompt_right(_ctx, props) {
        return <UsageView api={api} session_id={props.session_id} />
      },
    },
  })
}

export default { id: "usage", tui }
