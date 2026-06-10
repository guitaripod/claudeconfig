export const meta = {
  name: 'wwdc',
  description: 'Search WWDC session knowledge base and answer questions about Apple frameworks and APIs',
  phases: [
    { title: 'Search', detail: 'topic index lookup, then full-text fallback' },
    { title: 'Read', detail: 'fetch session READMEs, transcripts for detail queries' },
    { title: 'Synthesize', detail: 'compile answer' },
  ],
}

const query = typeof args === 'string' && args.trim() ? args.trim() : 'what is new'

const isRecentQuery = /new|latest|wwdc\s*2[0-9]|this year|2026/i.test(query)
const isDetailQuery = /how (do|to|can)|show me|example|code|implement|use/i.test(query)

const SESSION_SCHEMA = {
  type: 'object',
  properties: {
    sessions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          path: { type: 'string' },
          title: { type: 'string' },
        },
        required: ['path', 'title'],
      },
    },
    usedTopicIndex: { type: 'boolean' },
  },
  required: ['sessions', 'usedTopicIndex'],
}

const READ_SCHEMA = {
  type: 'object',
  properties: {
    content: { type: 'string' },
    needsTranscript: { type: 'boolean' },
  },
  required: ['content', 'needsTranscript'],
}

phase('Search')

const found = await agent(
  `Search the GitHub repo guitaripod/wwdc-sessions for sessions related to: ${query}

STEP 1 — Topic index lookup (preferred):
Fetch one or more of these curated topic index files that are relevant to the query:
- https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/topics/swift.md
- https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/topics/app-services.md
- https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/topics/developer-tools.md
- https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/topics/essentials.md
- https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/events/wwdc2026/index.md

If a topic file contains relevant session links, extract up to 5 session paths from it (format: sessions/wwdcYEAR/ID-slug). Set usedTopicIndex to true.
${isRecentQuery ? 'The user is asking about recent/new content — strongly prefer wwdc2026 sessions.' : ''}

STEP 2 — Full-text fallback (only if step 1 found nothing relevant):
Run: gh search code ${JSON.stringify(query)} --repo guitaripod/wwdc-sessions --limit 30
Extract unique session directory paths from lines matching "sessions/wwdcYEAR/ID-slug/". Set usedTopicIndex to false.
${isRecentQuery ? 'Prefer sessions/wwdc2026 paths.' : ''}

Return up to 5 most relevant sessions. Derive each title from its slug (e.g. "274-what-s-new-in-swiftdata" → "What's New in SwiftData").`,
  { label: 'search', phase: 'Search', model: 'claude-haiku-4-5-20251001', schema: SESSION_SCHEMA }
)

if (!found.sessions.length) return `No WWDC sessions found for: ${query}`

phase('Read')

const contents = await pipeline(
  found.sessions.slice(0, 5),
  async (s, _orig, i) => {
    const readmeUrl = `https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/${s.path}/README.md`
    const result = await agent(
      `Fetch this URL and return its content:
${readmeUrl}

Return the full content in the "content" field.
Set "needsTranscript" to true if${isDetailQuery ? ' true (the user wants code examples or implementation detail)' : ' the README is very thin (under ~200 words) and a deeper transcript would help answer a how-to or code question'}.`,
      { label: `read:${i}`, phase: 'Read', model: 'claude-haiku-4-5-20251001', schema: READ_SCHEMA }
    )
    if (!result) return null

    let content = result.content
    if (result.needsTranscript) {
      const transcriptUrl = `https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/${s.path}/transcript.md`
      const transcript = await agent(
        `Fetch this URL and return its full content verbatim:\n${transcriptUrl}`,
        { label: `transcript:${i}`, phase: 'Read', model: 'claude-haiku-4-5-20251001' }
      )
      if (transcript) content = content + '\n\n### Full Transcript\n\n' + transcript
    }

    return { title: s.title, content }
  }
)

const valid = contents.filter(Boolean)
if (!valid.length) return 'Could not fetch any session content.'

phase('Synthesize')

return await agent(
  `The user asked: "${query}"

Here are the relevant WWDC session contents:

${valid.map(c => `## ${c.title}\n\n${c.content}`).join('\n\n---\n\n')}

Write a clear, well-organized answer. Include concrete API changes, new features, and code examples where present. Use markdown.`,
  { label: 'synthesize', phase: 'Synthesize', model: 'claude-haiku-4-5-20251001' }
)
