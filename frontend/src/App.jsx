import { useState } from 'react';
import PlannerForm from './components/PlannerForm';
import AdventurePlan from './components/AdventurePlan';

export default function App() {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFormSubmit = async (formData) => {
    setLoading(true);
    setError(null);
    setPlan(null);

    try {
      const response = await fetch('http://localhost:8000/api/trailmate/plan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        let errorDetail = 'Failed to generate adventure plan.';
        try {
          const errData = await response.json();
          if (errData?.detail) {
            errorDetail = typeof errData.detail === 'string'
              ? errData.detail
              : JSON.stringify(errData.detail);
          }
        } catch {
          errorDetail = `Server returned status ${response.status}: ${response.statusText || 'Error'}`;
        }
        throw new Error(errorDetail);
      }

      const data = await response.json();
      setPlan(data);
    } catch (err) {
      console.error('API call failed:', err);
      setError(
        err.message ||
        'Unable to connect to TrailMate AI backend. Please verify the backend server is running on http://localhost:8000.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="hero-bg" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* ── Noise texture overlay ── */}
      <div
        aria-hidden="true"
        style={{
          position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E")`,
          opacity: 0.5,
        }}
      />

      {/* ── Nav Bar ── */}
      <nav style={{ position: 'relative', zIndex: 10, padding: '1.25rem 2rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(163,230,53,0.08)' }}>
        <div className="font-display" style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', fontWeight: 800, fontSize: '1.2rem', color: '#e8e3db', letterSpacing: '-0.01em' }}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#a3e635" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 17l4-8 4 4 3-6 4 10"/>
            <path d="M21 17H3"/>
          </svg>
          TrailMate <span style={{ color: '#a3e635' }}>AI</span>
        </div>
        <div className="stat-badge">
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#a3e635', display: 'inline-block' }}></span>
          AI Ready
        </div>
      </nav>

      {/* ── Main Content ── */}
      <main style={{ position: 'relative', zIndex: 10, flex: 1, width: '100%', maxWidth: '780px', margin: '0 auto', padding: '2.5rem 1.5rem 4rem' }}>

        {/* ── Hero ── */}
        <header style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <div className="animate-fade-in-up" style={{ display: 'flex', justifyContent: 'center', marginBottom: '1.25rem', gap: '0.6rem', flexWrap: 'wrap' }}>
            <span className="stat-badge">🥾 Hiking</span>
            <span className="stat-badge">🚴 Cycling</span>
            <span className="stat-badge">🏃 Running</span>
            <span className="stat-badge">🚶 Walking</span>
          </div>

          <h1
            className="font-display animate-fade-in-up anim-delay-100"
            style={{
              fontSize: 'clamp(2.2rem, 6vw, 3.6rem)',
              fontWeight: 900,
              lineHeight: 1.1,
              letterSpacing: '-0.03em',
              margin: '0 0 1rem',
              background: 'linear-gradient(135deg, #e8e3db 0%, #a3e635 60%, #84cc16 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            Turn your free time into<br />an outdoor mission.
          </h1>

          <p
            className="animate-fade-in-up anim-delay-200"
            style={{ fontSize: '1.05rem', color: 'rgba(232,227,219,0.65)', maxWidth: '520px', margin: '0 auto', lineHeight: 1.65 }}
          >
            TrailMate AI crafts personalised outdoor adventures matched to your schedule, fitness level and location — in seconds.
          </p>
        </header>

        {/* ── Planner Card ── */}
        <section
          id="planner"
          className="glass-card animate-fade-in-up anim-delay-300"
          style={{ padding: '2.25rem 2rem', marginBottom: '2rem' }}
          aria-label="Adventure planner"
        >
          <h2
            className="font-display"
            style={{ margin: '0 0 1.75rem', fontSize: '1.35rem', fontWeight: 700, color: '#e8e3db', letterSpacing: '-0.01em' }}
          >
            ⛰ Plan Your Adventure
          </h2>
          <PlannerForm onSubmit={handleFormSubmit} loading={loading} />
        </section>

        {/* ── Output Area ── */}
        <section id="adventure-output" aria-label="Generated adventure plan" aria-live="polite">
          <AdventurePlan plan={plan} loading={loading} error={error} />
        </section>
      </main>

      {/* ── Footer ── */}
      <footer style={{ position: 'relative', zIndex: 10, textAlign: 'center', padding: '1.5rem', borderTop: '1px solid rgba(163,230,53,0.08)', color: 'rgba(122,114,104,0.7)', fontSize: '0.8rem' }}>
        TrailMate AI &mdash; Built for explorers &bull; Powered by AI
      </footer>
    </div>
  );
}

