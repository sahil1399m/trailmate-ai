export default function AdventurePlan({ plan, loading = false, error = null }) {
  // ── 1. Error State ──
  if (error) {
    return (
      <div
        className="glass-card animate-fade-in-up"
        style={{
          border: '1px solid rgba(239, 68, 68, 0.4)',
          background: 'rgba(38, 18, 18, 0.65)',
          padding: '1.75rem 2rem',
          textAlign: 'center',
        }}
      >
        <div style={{ display: 'inline-flex', padding: '0.6rem', borderRadius: '50%', background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', marginBottom: '0.75rem' }}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <h3 className="font-display" style={{ margin: '0 0 0.5rem', color: '#fca5a5', fontSize: '1.1rem' }}>
          Unable to Generate Adventure
        </h3>
        <p style={{ color: 'rgba(244, 241, 235, 0.8)', fontSize: '0.9rem', margin: 0, lineHeight: 1.5 }}>
          {error}
        </p>
      </div>
    );
  }

  // ── 2. Loading State ──
  if (loading) {
    return (
      <div className="plan-output animate-fade-in-up" style={{ minHeight: '220px' }}>
        <div className="animate-float" style={{ position: 'relative' }}>
          <svg
            width="52"
            height="52"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#a3e635"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="animate-spin"
            style={{ animationDuration: '6s' }}
          >
            <circle cx="12" cy="12" r="10" />
            <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" fill="rgba(163,230,53,0.2)" />
          </svg>
        </div>
        <p className="font-display" style={{ color: '#a3e635', fontWeight: 700, fontSize: '1.1rem', margin: '0.5rem 0 0' }}>
          Scouting your outdoor mission…
        </p>
        <p style={{ color: 'rgba(232,227,219,0.6)', fontSize: '0.85rem', margin: 0 }}>
          Crafting route concepts, packing list, and sensory challenges.
        </p>
      </div>
    );
  }

  // ── 3. Empty Initial State ──
  if (!plan) {
    return (
      <div className="plan-output animate-fade-in-up anim-delay-400">
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="rgba(163,230,53,0.35)"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="animate-float"
        >
          <circle cx="12" cy="12" r="10" />
          <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
        </svg>
        <p style={{ color: 'rgba(163,230,53,0.65)', fontWeight: 600, fontSize: '1rem', margin: 0 }}>
          Your adventure will appear here.
        </p>
        <p style={{ color: 'rgba(232,227,219,0.4)', fontSize: '0.85rem', margin: 0 }}>
          Fill in your details above and hit <em>Create My Adventure</em> to get started.
        </p>
      </div>
    );
  }

  // ── 4. Rendered Adventure Plan ──
  const duration = plan.duration_minutes || plan.duration || 'Flexible';
  const activity = plan.activity || 'Outdoor';
  const difficulty = plan.difficulty || 'Moderate';
  const thingsToCarry = Array.isArray(plan.things_to_carry) ? plan.things_to_carry : [];
  const safetyTips = Array.isArray(plan.safety_tips) ? plan.safety_tips : [];

  return (
    <div className="glass-card animate-fade-in-up" style={{ padding: '2.25rem 2rem', overflow: 'hidden' }}>
      {/* Top Banner / Badges */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '1.25rem' }}>
        <span className="stat-badge">
          ⏱ {duration} mins
        </span>
        <span className="stat-badge" style={{ textTransform: 'capitalize' }}>
          🏃 {activity}
        </span>
        <span className="stat-badge" style={{ textTransform: 'capitalize' }}>
          🔥 {difficulty} effort
        </span>
      </div>

      {/* Plan Title */}
      <h2
        className="font-display"
        style={{
          margin: '0 0 0.85rem',
          fontSize: 'clamp(1.5rem, 3.5vw, 2rem)',
          fontWeight: 800,
          lineHeight: 1.2,
          color: '#e8e3db',
          letterSpacing: '-0.02em',
        }}
      >
        {plan.title}
      </h2>

      {/* Summary */}
      <p style={{ fontSize: '1rem', color: 'rgba(232,227,219,0.85)', lineHeight: 1.65, margin: '0 0 1.75rem' }}>
        {plan.summary}
      </p>

      {/* Structured Sections */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {/* Mission */}
        {plan.mission && (
          <div style={{ padding: '1.25rem', background: 'rgba(13,31,15,0.7)', borderRadius: '14px', border: '1px solid rgba(163,230,53,0.15)' }}>
            <div className="trail-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', margin: '0 0 0.4rem' }}>
              <span>🎯</span> Mission
            </div>
            <p style={{ margin: 0, color: 'var(--clr-stone-200)', lineHeight: 1.6, fontSize: '0.95rem' }}>
              {plan.mission}
            </p>
          </div>
        )}

        {/* Route Idea */}
        {plan.route_idea && (
          <div style={{ padding: '1.25rem', background: 'rgba(13,31,15,0.7)', borderRadius: '14px', border: '1px solid rgba(163,230,53,0.15)' }}>
            <div className="trail-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', margin: '0 0 0.4rem' }}>
              <span>🗺️</span> Route Idea
            </div>
            <p style={{ margin: 0, color: 'var(--clr-stone-200)', lineHeight: 1.6, fontSize: '0.95rem' }}>
              {plan.route_idea}
            </p>
          </div>
        )}

        {/* Two-column layout on larger screens: Things to Carry & Challenge */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Things to Carry */}
          {thingsToCarry.length > 0 && (
            <div style={{ padding: '1.25rem', background: 'rgba(13,31,15,0.7)', borderRadius: '14px', border: '1px solid rgba(163,230,53,0.15)' }}>
              <div className="trail-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', margin: '0 0 0.6rem' }}>
                <span>🎒</span> Things to Carry
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.2rem', color: 'rgba(232,227,219,0.9)', fontSize: '0.9rem', lineHeight: 1.65 }}>
                {thingsToCarry.map((item, idx) => (
                  <li key={idx} style={{ marginBottom: '0.25rem' }}>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Sensory Challenge */}
          {plan.challenge && (
            <div style={{ padding: '1.25rem', background: 'rgba(163,230,53,0.06)', borderRadius: '14px', border: '1px solid rgba(163,230,53,0.25)' }}>
              <div className="trail-label" style={{ color: '#a3e635', display: 'flex', alignItems: 'center', gap: '0.4rem', margin: '0 0 0.4rem' }}>
                <span>🌿</span> Touch-Grass Challenge
              </div>
              <p style={{ margin: 0, color: 'var(--clr-stone-100)', lineHeight: 1.6, fontSize: '0.95rem', fontStyle: 'italic' }}>
                "{plan.challenge}"
              </p>
            </div>
          )}
        </div>

        {/* Safety Tips */}
        {safetyTips.length > 0 && (
          <div style={{ padding: '1.25rem', background: 'rgba(13,31,15,0.7)', borderRadius: '14px', border: '1px solid rgba(163,230,53,0.15)' }}>
            <div className="trail-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', margin: '0 0 0.6rem' }}>
              <span>🛡️</span> Safety Tips
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.2rem', color: 'rgba(232,227,219,0.9)', fontSize: '0.9rem', lineHeight: 1.65 }}>
              {safetyTips.map((tip, idx) => (
                <li key={idx} style={{ marginBottom: '0.25rem' }}>
                  {tip}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

