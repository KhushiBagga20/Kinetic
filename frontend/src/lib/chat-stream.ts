/**
 * Reads the agent's Server-Sent Event stream.
 *
 * `fetch` is used rather than EventSource because the request is a POST, and
 * because the body has to be consumed incrementally for the answer to appear
 * as it is written.
 */

import type { AgentEvent } from "./types"

export async function streamChat(
  message: string,
  onEvent: (event: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    signal,
  })

  if (!response.ok || !response.body) {
    throw new Error(`Chat stream failed: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split("\n\n")
    buffer = frames.pop() ?? ""

    for (const frame of frames) {
      const line = frame.trim()
      if (!line.startsWith("data:")) continue
      const payload = line.slice(5).trim()
      if (payload === "[DONE]") return
      try {
        onEvent(JSON.parse(payload) as AgentEvent)
      } catch {
        // A partial frame can arrive mid-chunk; the next read completes it.
      }
    }
  }
}
