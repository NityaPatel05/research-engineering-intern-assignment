import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Scatter
} from 'recharts'

export default function TimeSeriesPage({ spamThreshold }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [keyword, setKeyword] = useState('')
  const [subreddit, setSubreddit] = useState('')
  // Committed filter values — only updated after debounce or button click
  const [committed, setCommitted] = useState({ keyword: '', subreddit: '' })

  const fetchData = useCallback(async (kw, sub) => {
    setLoading(true)
    try {
      const p = new URLSearchParams({ spam_threshold: spamThreshold })
      if (kw) p.append('keyword', kw)
      if (sub) p.append('subreddit', sub)
      const res = await axios.get(`http://127.0.0.1:8000/timeseries?${p.toString()}`)
      setData(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [spamThreshold])

  // Initial load and when spam threshold changes
  useEffect(() => {
    fetchData(committed.keyword, committed.subreddit)
  }, [committed, spamThreshold])

  // Debounce keyword/subreddit inputs — commits after 600ms of no typing
  useEffect(() => {
    const timer = setTimeout(() => {
      setCommitted({ keyword, subreddit })
    }, 600)
    return () => clearTimeout(timer)
  }, [keyword, subreddit])

  // The API returns: { daily: [...], hourly: [...], weekly: [...], anomalies: {...}, summary: "..." }
  const daily = data?.daily ?? []
  const anomalies = data?.anomalies?.anomalies ?? []
  const changepoints = data?.anomalies?.changepoints ?? []

  const chartData = daily.map((d) => {
    const dateStr = typeof d.date === 'string' ? d.date : String(d.date)
    const isAnomaly = anomalies.find((a) => a.date === dateStr)
    const isChangepoint = changepoints.includes(dateStr)
    return {
      ...d,
      date: dateStr,
      anomalyValue: isAnomaly ? d.count : null,
      changepointValue: isChangepoint ? d.count : null
    }
  })

  // Compute recent growth rate from last two daily entries
  const recentGrowth = daily.length >= 2
    ? (() => {
        const prev = daily[daily.length - 2]?.count || 0
        const curr = daily[daily.length - 1]?.count || 0
        return prev > 0 ? ((curr - prev) / prev) : 0
      })()
    : null

  return (
    <div className="flex flex-col gap-6 max-w-6xl mx-auto">
      <div className="flex gap-4">
        <input
          type="text"
          placeholder="Filter by keyword… (auto-searches after typing stops)"
          className="bg-gray-800 text-white px-4 py-2 rounded flex-1 border border-gray-700"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
        <input
          type="text"
          placeholder="Filter by subreddit…"
          className="bg-gray-800 text-white px-4 py-2 rounded flex-1 border border-gray-700"
          value={subreddit}
          onChange={(e) => setSubreddit(e.target.value)}
        />
        <button
          onClick={() => setCommitted({ keyword, subreddit })}
          className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded font-medium transition"
        >
          Search
        </button>
      </div>

      {/* Active filter badges */}
      {(committed.keyword || committed.subreddit) && (
        <div className="flex gap-2 flex-wrap">
          {committed.keyword && (
            <span className="bg-blue-900/50 text-blue-300 text-xs px-3 py-1 rounded-full border border-blue-700/50">
              keyword: <strong>{committed.keyword}</strong>
            </span>
          )}
          {committed.subreddit && (
            <span className="bg-purple-900/50 text-purple-300 text-xs px-3 py-1 rounded-full border border-purple-700/50">
              subreddit: <strong>{committed.subreddit}</strong>
            </span>
          )}
          <button
            onClick={() => { setKeyword(''); setSubreddit(''); setCommitted({ keyword: '', subreddit: '' }) }}
            className="text-gray-400 text-xs hover:text-white underline"
          >
            Clear filters
          </button>
        </div>
      )}

      {loading ? (
        <div className="h-96 bg-gray-800 animate-pulse rounded border border-gray-700"></div>
      ) : data?.empty ? (
        <div className="h-48 bg-gray-800 rounded border border-gray-700 flex items-center justify-center text-gray-400">
          {data.message || 'No data for the selected filters.'}
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="bg-gray-800 p-6 rounded border border-gray-700">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold">Post Volume Over Time</h3>
              {recentGrowth !== null && (
                <div
                  className={`px-3 py-1 rounded font-bold ${
                    recentGrowth > 0 ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
                  }`}
                >
                  Recent Growth: {(recentGrowth * 100).toFixed(1)}%
                </div>
              )}
            </div>

            {chartData.length === 0 ? (
              <div className="h-80 flex items-center justify-center text-gray-500">No data points to chart.</div>
            ) : (
              <div className="h-80 w-full mb-4">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="date" stroke="#9ca3af" tick={{ fontSize: 11 }} />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151' }}
                    />
                    <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={false} name="Posts" />
                    <Line type="monotone" dataKey="rolling_7d_avg" stroke="#10b981" strokeWidth={2} dot={false} strokeDasharray="5 5" name="7-day avg" />
                    <Scatter dataKey="anomalyValue" fill="#ef4444" isAnimationActive={false} name="Anomaly" />
                    <Scatter dataKey="changepointValue" fill="#f59e0b" shape="star" isAnimationActive={false} name="Changepoint" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Legend */}
            <div className="flex gap-6 text-xs text-gray-400 mb-4">
              <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-blue-500 inline-block"></span> Posts</span>
              <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-emerald-500 inline-block" style={{borderTop:'2px dashed'}}></span> 7-day avg</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block"></span> Anomaly</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-amber-500 inline-block"></span> Changepoint</span>
            </div>

            <div className="bg-gray-900 overflow-hidden p-4 rounded text-gray-300 border border-gray-700 relative">
              <span className="block font-bold text-gray-400 text-xs uppercase mb-2">AI Summary</span>
              {data?.summary || 'No summary available.'}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
