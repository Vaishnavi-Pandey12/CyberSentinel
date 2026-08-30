import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { caseService, predictionService } from '../services/services';
import type { Case, Prediction } from '../types';
import { ErrorState, PageHeader, RiskBadge, Loading } from '../components/ui';

export function Investigation() {
  const { id = '' } = useParams();
  const [c, setC] = useState<Case>();
  const [p, setP] = useState<Prediction[]>([]);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const nav = useNavigate();

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([caseService.get(id), predictionService.list()])
      .then(([caseData, predData]) => {
        if (!caseData) {
          setError(`Investigation record '${id}' could not be located.`);
        } else {
          setC(caseData);
        }
        setP(predData);
      })
      .catch((err) => {
        setError(err?.message || 'Failed to fetch investigation details.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id]);

  if (loading) return <Loading />;
  if (error || !c) {
    return (
      <div className="page">
        <PageHeader eyebrow="INVESTIGATION / CASE VIEW" title="Investigation" />
        <ErrorState>{error || 'Investigation record could not be located.'}</ErrorState>
      </div>
    );
  }

  const hot = p.filter((x) => c.hotspot_ids?.includes(x.id));

  return (
    <div className="page">
      <PageHeader eyebrow="INVESTIGATION / CASE VIEW" title={`CASE #${c.id}`}>
        <button className="btn secondary" onClick={() => nav('/alerts')}>
          View related alerts
        </button>
      </PageHeader>
      <div className="case-header">
        <div>
          <span className="status ack">{c.status}</span>
          <RiskBadge level={c.risk_level} />
        </div>
        <p>{c.summary}</p>
      </div>
      <div className="case-grid">
        <section className="panel">
          <p className="eyebrow">RELATED COMPLAINTS</p>
          <h2>Case associations</h2>
          <div className="chips">
            {c.complaints?.map((x) => (
              <span key={x}>{x}</span>
            ))}
          </div>
        </section>
        <section className="panel">
          <p className="eyebrow">PREDICTED HOTSPOTS</p>
          <h2>Priority locations</h2>
          {hot.length > 0 ? (
            hot.map((x) => (
              <button
                className="hotspot"
                key={x.id}
                onClick={() => nav(`/predictions/${x.id}`)}
              >
                <span>
                  <b>{x.location_id}</b>
                  <small>
                    {x.predicted_window} · {x.location_name}
                  </small>
                </span>
                <RiskBadge level={x.risk_level} />
              </button>
            ))
          ) : (
            <p className="help">No active predicted hotspots associated with this case.</p>
          )}
        </section>
        <section className="panel timeline">
          <p className="eyebrow">TRANSACTION / EVENT TIMELINE</p>
          <h2>Operational sequence</h2>
          {c.timeline?.map((x) => (
            <div key={x.time}>
              <time>{x.time}</time>
              <span />
              <p>
                <b>{x.event}</b>
                <small>{x.location}</small>
              </p>
            </div>
          ))}
        </section>
        <section className="panel notes">
          <p className="eyebrow">EVIDENCE & INTELLIGENCE NOTES</p>
          <h2>Officer notes</h2>
          {c.notes?.map((x) => (
            <p key={x}>• {x}</p>
          ))}
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (note && c) {
                const updated = await caseService.addNote(c.id, note);
                if (updated) {
                  setC(updated);
                } else {
                  c.notes.push(note);
                  setC({ ...c });
                }
                setNote('');
              }
            }}
          >
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add intelligence note"
            />
            <button className="btn small">Add note</button>
          </form>
        </section>
      </div>
    </div>
  );
}
