import { useState, useEffect } from 'react'

interface ApiStatus {
  message: string
  version: string
}

function App() {
  const [status, setStatus] = useState<ApiStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000'
    fetch(`${apiUrl}/api/v1/`)
      .then((res) => res.json())
      .then((data) => setStatus(data))
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Japan ETF Analyzer</h1>
      <p>日本のETF銘柄を探して分析するWebアプリケーション</p>

      <h2>API Status</h2>
      {error ? (
        <p style={{ color: 'red' }}>Error: {error}</p>
      ) : status ? (
        <div>
          <p>Message: {status.message}</p>
          <p>Version: {status.version}</p>
        </div>
      ) : (
        <p>Loading...</p>
      )}
    </div>
  )
}

export default App
