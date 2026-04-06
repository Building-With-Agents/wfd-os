import React, { useState } from 'react'

const SUGGESTED_QUERIES = [
  'Top skills this week',
  'How many job-ready students?',
  'Which programs match demand?',
  'Fastest growing skills?',
  'Skills gap by region',
]

export default function QueryInterface() {
  const [query, setQuery] = useState('')
  const [response, setResponse] = useState<string | null>(null)

  const handleSubmit = (q: string) => {
    setQuery(q)
    setResponse('AI query interface -- activates when Claude API credits are added. Query received: "' + q + '"')
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">AI</div>
        <h2 className="text-lg font-semibold text-slate-800">Ask Waifinder</h2>
        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">Pending API credits</span>
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && query && handleSubmit(query)}
          placeholder="Ask a question about the labor market, talent pipeline, or skills gaps..."
          className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm text-slate-700 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <button
          onClick={() => query && handleSubmit(query)}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          disabled={!query}
        >
          Ask
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {SUGGESTED_QUERIES.map((sq) => (
          <button
            key={sq}
            onClick={() => handleSubmit(sq)}
            className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
          >
            {sq}
          </button>
        ))}
      </div>

      {response && (
        <div className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-600 italic">
          {response}
        </div>
      )}
    </div>
  )
}
