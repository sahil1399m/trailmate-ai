import { useState } from 'react';

const ACTIVITIES = ['Walking', 'Cycling', 'Running', 'Hiking'];
const INTENSITIES = ['Low', 'Moderate', 'High'];

const DEFAULT_FORM = {
  time: '',
  activity: '',
  intensity: '',
  budget: '',
  location: '',
};

export default function PlannerForm({ onSubmit, loading = false }) {
  const [form, setForm] = useState(DEFAULT_FORM);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.time || !form.activity || !form.intensity || !form.location) {
      return;
    }

    const payload = {
      time_available: parseInt(form.time, 10) || 15,
      activity: form.activity.toLowerCase(),
      intensity: form.intensity.toLowerCase(),
      budget: parseFloat(String(form.budget).replace(/[^0-9.]/g, '')) || 0,
      location: form.location.trim(),
    };

    if (onSubmit) onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate={false}>
      {/* Row 1: Time + Location */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <div>
          <label htmlFor="time" className="trail-label">
            ⏱ Available Time (minutes)
          </label>
          <input
            id="time"
            name="time"
            type="number"
            min="15"
            max="480"
            placeholder="e.g. 90 minutes"
            className="trail-input"
            value={form.time}
            onChange={handleChange}
            disabled={loading}
            required
          />
        </div>
        <div>
          <label htmlFor="location" className="trail-label">
            📍 Location
          </label>
          <input
            id="location"
            name="location"
            type="text"
            placeholder="City, area or postcode"
            className="trail-input"
            value={form.location}
            onChange={handleChange}
            disabled={loading}
            required
          />
        </div>
      </div>

      {/* Row 2: Activity + Intensity */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <div>
          <label htmlFor="activity" className="trail-label">
            🏃 Activity
          </label>
          <select
            id="activity"
            name="activity"
            className="trail-select"
            value={form.activity}
            onChange={handleChange}
            disabled={loading}
            required
          >
            <option value="" disabled>Select activity…</option>
            {ACTIVITIES.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="intensity" className="trail-label">
            🔥 Intensity
          </label>
          <select
            id="intensity"
            name="intensity"
            className="trail-select"
            value={form.intensity}
            onChange={handleChange}
            disabled={loading}
            required
          >
            <option value="" disabled>Select intensity…</option>
            {INTENSITIES.map((i) => (
              <option key={i} value={i}>{i}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Row 3: Budget */}
      <div>
        <label htmlFor="budget" className="trail-label">
          💰 Budget (optional)
        </label>
        <input
          id="budget"
          name="budget"
          type="text"
          placeholder="e.g. 0 (Free) or 20"
          className="trail-input"
          value={form.budget}
          onChange={handleChange}
          disabled={loading}
        />
      </div>

      {/* Submit */}
      <button
        id="create-adventure-btn"
        type="submit"
        disabled={loading}
        className={`btn-cta mt-2 ${loading ? 'opacity-80 cursor-not-allowed' : 'animate-pulse-glow'}`}
      >
        {loading ? (
          <>
            <svg
              className="animate-spin"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
            >
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.25" />
              <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" />
            </svg>
            <span>Creating Adventure...</span>
          </>
        ) : (
          <>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 12l9-9 9 9"/>
              <path d="M9 21V12h6v9"/>
            </svg>
            <span>Create My Adventure</span>
          </>
        )}
      </button>
    </form>
  );
}

