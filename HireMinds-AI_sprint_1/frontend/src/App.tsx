import { useEffect, useState } from 'react';

interface HealthData {
  status: string;
  project: string;
  version: string;
  environment: string;
  timestamp: string;
  services: Record<string, string>;
}

export function App() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetch('/api/v1/health')
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then((data: HealthData) => {
        setHealth(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to connect to backend');
        setLoading(false);
      });
  }, []);

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', maxWidth: '640px', margin: '40px auto', padding: '24px', border: '1px solid #e2e8f0', borderRadius: '8px', background: '#ffffff', color: '#0f172a' }}>
      <h1 style={{ margin: '0 0 8px 0', fontSize: '24px', color: '#1e293b' }}>HireMinds AI — Phase 1</h1>
      <p style={{ margin: '0 0 20px 0', color: '#64748b', fontSize: '14px' }}>
        Backend-first foundation verification page.
      </p>

      <div style={{ padding: '16px', borderRadius: '6px', backgroundColor: '#f8fafc', border: '1px solid #cbd5e1' }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>Backend Health Status</h3>

        {loading && <p style={{ color: '#64748b' }}>Checking backend health at /api/v1/health...</p>}

        {error && (
          <div style={{ color: '#b91c1c', backgroundColor: '#fee2e2', padding: '12px', borderRadius: '4px' }}>
            <strong>Connection Error:</strong> {error}
            <br />
            <small>Ensure the FastAPI backend is running on http://127.0.0.1:8000</small>
          </div>
        )}

        {health && (
          <div>
            <p><strong>Status:</strong> <span style={{ color: '#15803d', fontWeight: 'bold' }}>● {health.status}</span></p>
            <p><strong>Project:</strong> {health.project} (v{health.version})</p>
            <p><strong>Environment:</strong> {health.environment}</p>
            <p><strong>API Check Time:</strong> {new Date(health.timestamp).toLocaleTimeString()}</p>
            <p><strong>Active Services:</strong></p>
            <ul style={{ margin: '4px 0 0 20px', padding: 0 }}>
              {Object.entries(health.services).map(([service, status]) => (
                <li key={service}>
                  <code>{service}</code>: {status}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div style={{ marginTop: '24px', fontSize: '13px', color: '#64748b', borderTop: '1px solid #e2e8f0', paddingTop: '12px' }}>
        Backend API Docs available at: <a href="http://127.0.0.1:8000/api/v1/docs" target="_blank" rel="noreferrer" style={{ color: '#2563eb' }}>http://127.0.0.1:8000/api/v1/docs</a>
      </div>
    </div>
  );
}

export default App;
