import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AlertCircle, BriefcaseBusiness, Clock, MapPin, RefreshCw } from 'lucide-react';
import { alertService, predictionService } from '../services/services';
import type { Alert, Prediction } from '../types';
import { ErrorState, Loading, PageHeader, RiskBadge } from '../components/ui';

export function PredictionDetail() {
  const { id = '' } = useParams();
  const [p, setP] = useState<Prediction>();
  const [alert, setAlert] = useState<Alert | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const nav = useNavigate();

  const fetchDetail = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const pred = await predictionService.get(id);
      setP(pred);
      const a = await alertService.forPrediction(pred.id);
      setAlert(a);
    } catch (err: any) {
      setError(err?.message || `Prediction intelligence for '${id}' could not be retrieved.`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  if (loading) return <Loading />;
  if (error || !p) {
    return (
      <div className="page">
        <PageHeader eyebrow="PREDICTION INTELLIGENCE" title="Not Found">
          <button className="btn secondary" onClick={() => nav('/heatmap')}>
            Back to heatmap
          </button>
        </PageHeader>
        <ErrorState>
          {error || 'Prediction intelligence record could not be located.'}
          <div style={{ marginTop: '1rem' }}>
            <button className="btn secondary" onClick={fetchDetail}>
              <RefreshCw size={16} /> Retry
            </button>
          </div>
        </ErrorState>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader eyebrow="PREDICTION INTELLIGENCE" title={p.location_id}>
        <button className="btn secondary" onClick={() => nav('/heatmap')}>
          Back to heatmap
        </button>
      </PageHeader>
      <div className="detail-hero">
        <div>
          <p className="eyebrow">{p.crime_category}</p>
          <h2>{p.location_name}</h2>
          <p>
            <MapPin size={16} />
            {p.region}, India • Lat: {p.latitude.toFixed(4)}, Lon: {p.longitude.toFixed(4)}
          </p>
        </div>
        <RiskBadge level={p.risk_level} />
      </div>
      <div className="detail-grid">
        <section className="panel score-card">
          <p className="eyebrow">ASSESSMENT</p>
          <div className="big-score">
            {p.risk_score}
            <span>%</span>
          </div>
          <h2>Risk score</h2>
          <div className="meter">
            <i style={{ width: `${Math.min(p.risk_score, 100)}%` }} />
          </div>
          <div className="metric-row">
            <span>
              <Clock /> Predicted window <b>{p.predicted_window}</b>
            </span>
            <span>
              Confidence <b>{p.confidence}%</b>
            </span>
          </div>
        </section>
        <section className="panel factors">
          <p className="eyebrow">WHY THIS LOCATION IS HIGH-RISK</p>
          <h2>Contributing intelligence</h2>
          {p.top_factors && p.top_factors.length > 0 ? (
            p.top_factors.map((f, i) => (
              <div key={f}>
                <span>{i + 1}</span>
                {f}
              </div>
            ))
          ) : (
            <p className="help">No contributing factors listed.</p>
          )}
        </section>
        <section className="panel detail-meta">
          <p className="eyebrow">CASE & COMPLAINTS LINKAGE</p>
          <h2>Related complaints</h2>
          <div className="chips">
            {p.related_complaints && p.related_complaints.length > 0 ? (
              p.related_complaints.map((c) => <span key={c}>{c}</span>)
            ) : (
              <span style={{ color: 'var(--muted)' }}>No linked complaints</span>
            )}
          </div>
          <dl>
            <div>
              <dt>Model version</dt>
              <dd>{p.model_version}</dd>
            </div>
            <div>
              <dt>Prediction rank</dt>
              <dd>#{p.rank}</dd>
            </div>
            {p.created_at && (
              <div>
                <dt>Generated at</dt>
                <dd>{new Date(p.created_at).toLocaleDateString()}</dd>
              </div>
            )}
          </dl>
        </section>
        <section className="panel action-panel">
          <p className="eyebrow">OPERATIONAL ACTION</p>
          <h2>Coordinate response</h2>
          <p>
            {alert
              ? 'A linked alert is in the operational queue.'
              : 'No linked alert exists for this prediction.'}
          </p>
          <button className="btn" onClick={() => nav('/alerts')}>
            <AlertCircle size={17} />
            {alert ? 'View alert' : 'Create alert'}
          </button>
          {p.case_id && (
            <button
              className="btn secondary"
              onClick={() => nav(`/investigations/${p.case_id}`)}
            >
              <BriefcaseBusiness size={17} />
              Open investigation
            </button>
          )}
        </section>
      </div>
    </div>
  );
}
