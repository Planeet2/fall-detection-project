import { useCallback, useEffect, useState } from "react";

import { createElderProfile, getElders } from "../services/api";

const EMPTY_FORM = {
  full_name: "",
  age: "",
  room: "",
  location: "",
  has_chronic_disease: false,
  health_notes: "",
  caregiver_name: "",
  caregiver_contact: "",
  family_contact: "",
  emergency_contact: "",
};

function ElderProfiles({ selectedElderId, onSelect }) {
  const [profiles, setProfiles] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const loadProfiles = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getElders();
      setProfiles(data.items || []);
    } catch (err) {
      setError(err.message || "Elder profiles are temporarily unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(loadProfiles, 0);
    return () => window.clearTimeout(timeoutId);
  }, [loadProfiles]);

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!form.full_name.trim()) {
      setError("Full name is required.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      const createdProfile = await createElderProfile({
        ...form,
        full_name: form.full_name.trim(),
        age: form.age ? Number(form.age) : null,
      });
      setForm(EMPTY_FORM);
      setProfiles((current) => [createdProfile, ...current]);
      onSelect(createdProfile);
    } catch (err) {
      setError(err.message || "Could not create elder profile.");
    } finally {
      setSaving(false);
    }
  }

  const selectedProfile = profiles.find((profile) => profile.id === selectedElderId) || null;

  return (
    <section id="elders" className="panel elderProfilesPanel">
      <div className="panelHeader">
        <div>
          <span className="stepTag">Profiles</span>
          <h2>Elder Profiles</h2>
          <p>Select a profile before video analysis</p>
        </div>
        <button className="ghostButton" type="button" onClick={loadProfiles}>
          Refresh
        </button>
      </div>

      <div className="elderProfilesGrid">
        <div className="elderList">
          <button
            type="button"
            className={!selectedElderId ? "elderOption active" : "elderOption"}
            onClick={() => onSelect(null)}
          >
            <strong>No linked elder</strong>
            <span>Analyze without profile context</span>
          </button>

          {loading ? (
            <p className="tableEmpty">Loading profiles...</p>
          ) : profiles.length === 0 ? (
            <p className="tableEmpty">No active elder profiles yet.</p>
          ) : (
            profiles.map((profile) => (
              <button
                key={profile.id}
                type="button"
                className={selectedElderId === profile.id ? "elderOption active" : "elderOption"}
                onClick={() => onSelect(profile)}
              >
                <strong>{profile.full_name}</strong>
                <span>{profile.room || profile.location || "No room set"}</span>
              </button>
            ))
          )}
        </div>

        <form className="elderProfileForm" onSubmit={handleSubmit}>
          <div className="formGrid">
            <label>
              <span>Full name</span>
              <input value={form.full_name} onChange={(event) => updateField("full_name", event.target.value)} />
            </label>
            <label>
              <span>Age</span>
              <input type="number" min="0" value={form.age} onChange={(event) => updateField("age", event.target.value)} />
            </label>
            <label>
              <span>Room</span>
              <input value={form.room} onChange={(event) => updateField("room", event.target.value)} />
            </label>
            <label>
              <span>Location</span>
              <input value={form.location} onChange={(event) => updateField("location", event.target.value)} />
            </label>
            <label>
              <span>Caregiver</span>
              <input value={form.caregiver_name} onChange={(event) => updateField("caregiver_name", event.target.value)} />
            </label>
            <label>
              <span>Caregiver contact</span>
              <input value={form.caregiver_contact} onChange={(event) => updateField("caregiver_contact", event.target.value)} />
            </label>
            <label>
              <span>Family contact</span>
              <input value={form.family_contact} onChange={(event) => updateField("family_contact", event.target.value)} />
            </label>
            <label>
              <span>Emergency contact</span>
              <input value={form.emergency_contact} onChange={(event) => updateField("emergency_contact", event.target.value)} />
            </label>
          </div>

          <label className="checkboxRow">
            <input
              type="checkbox"
              checked={form.has_chronic_disease}
              onChange={(event) => updateField("has_chronic_disease", event.target.checked)}
            />
            <span>Has chronic disease</span>
          </label>

          <label className="notesField">
            <span>Health notes</span>
            <textarea value={form.health_notes} onChange={(event) => updateField("health_notes", event.target.value)} />
          </label>

          <button className="primaryButton" type="submit" disabled={saving}>
            {saving ? "Creating..." : "Create profile"}
          </button>
        </form>
      </div>

      {selectedProfile && (
        <div className="selectedElderBox">
          <span>Selected elder</span>
          <strong>{selectedProfile.full_name}</strong>
          <p>{selectedProfile.room || "No room"} · {selectedProfile.location || "No location"}</p>
        </div>
      )}

      {error && <div className="errorBox compactError">{error}</div>}
    </section>
  );
}

export default ElderProfiles;
