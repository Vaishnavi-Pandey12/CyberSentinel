import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Banknote, MapPinned, MessageSquare, RefreshCw } from 'lucide-react';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { dashboardService, predictionService, alertService } from '../services/services';
import type { Alert, DashboardSummary, Prediction } from '../types';
import { trend } from '../mocks/data';
import { MapView } from '../components/MapView';
import { Loading, PageHeader, RiskBadge, StatusBadge, ErrorState } from '../components/ui';

const icon = [MessageSquare, MapPinned, AlertTriangle, Banknote];

export function Dashboard() {
  const [s, setS] = useState<DashboardSummary>();
  const [p, setP] = useState<Prediction[]>([]);
  const [a, setA] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const nav = useNavigate();

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, predictionData, alertData] = await Promise.all([
        dashboardService.getSummary(),
        predictionService.list(),
        alertService.list(),
      ]);
      setS(summaryData);
      setP(predictionData);
      setA(alertData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboard intelligence from the server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <Loading />;
  if (error || !s) {
    return (
      <div className="page">
        <PageHeader eyebrow="OPERATIONAL OVERVIEW" title="Threat picture" />
        <ErrorState>
          {error || 'Unable to connect to live backend services.'}
          <div style={{ marginTop: '1rem' }}>
            <button className="btn secondary" onClick={loadData}>
              <RefreshCw size={16} /> Retry
            </button>
          </div>
        </ErrorState>
      </div>
    );
  }

  const cards = [
    ['Total Complaints', s.totalComplaints, 'Validated & linked complaints'],
    ['High-Risk Zones', s.highRiskZones, 'Critical and high priority'],
    ['Active Alerts', s.activeAlerts, 'Awaiting operational action'],
    ['At-Risk ATMs', s.atRiskAtms, 'Next 24-hour forecast'],
  ];

  return (
    <div className="page">
      <PageHeader eyebrow="OPERATIONAL OVERVIEW" title="Threat picture">
        <button className="btn secondary" onClick={() => nav('/heatmap')}>
          Open full heatmap
        </button>
      </PageHeader>
      <div className="kpis">
        {cards.map(([l, v, d], i) => {
          const Icon = icon[i];
          return (
            <article className="kpi" key={l}>
              <Icon />
              <p>{l}</p>
              <strong>{Number(v).toLocaleString()}</strong>
              <small>{d}</small>
            </article>
          );
        })}
      </div>
      <div className="dashboard-grid">
        <section className="panel map-panel">
          <div className="section-title">
            <div>
              <p className="eyebrow">GIS RISK OVERLAY</p>
              <h2>Risk heatmap preview</h2>
            </div>
            <span className="data-note">Live API telemetry • India</span>
          </div>
          <MapView
            compact
            data={p.slice(0, 5)}
            onSelect={(x) => nav(`/predictions/${x.id}`)}
          />
        </section>
        <section className="panel">
          <div className="section-title">
            <div>
              <p className="eyebrow">7-DAY SIGNAL</p>
              <h2>Risk trend</h2>
            </div>
          </div>
          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend}>
                <XAxis dataKey="day" stroke="#6F7772" tick={{ fill: '#A6ADA8', fontSize: 11 }} />
                <YAxis domain={[0, 100]} stroke="#6F7772" tick={{ fill: '#A6ADA8', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#191C1A', border: '1px solid #292D2A', borderRadius: '6px' }} labelStyle={{ color: '#F1F3F1' }} itemStyle={{ color: '#48D878' }} />
                <Line
                  type="monotone"
                  dataKey="risk"
                  stroke="#48D878"
                  strokeWidth={3}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="panel wide">
          <div className="section-title">
            <div>
              <p className="eyebrow">PRIORITISED HOTSPOTS</p>
              <h2>Top predicted locations</h2>
            </div>
            <button className="link-btn" onClick={() => nav('/heatmap')}>
              View all locations
            </button>
          </div>
          <div className="location-list">
            {p.slice(0, 4).map((x) => (
              <button
                key={x.id}
                onClick={() => nav(`/predictions/${x.id}`)}
              >
                <span className="rank">{x.rank}</span>
                <span>
                  <b>{x.location_id}</b>
                  <small>
                    {x.location_name} · {x.region}
                  </small>
                </span>
                <strong>{x.risk_score}%</strong>
                <RiskBadge level={x.risk_level} />
              </button>
            ))}
          </div>
        </section>
        <section className="panel">
          <div className="section-title">
            <div>
              <p className="eyebrow">RESPONSE QUEUE</p>
              <h2>Recent alerts</h2>
            </div>
            <button className="link-btn" onClick={() => nav('/alerts')}>
              Open queue
            </button>
          </div>
          <div className="alert-list">
            {a.slice(0, 4).map((x) => {
              const pp = p.find((q) => q.id === x.prediction_id);
              return (
                <button
                  key={x.id}
                  onClick={() => nav('/alerts')}
                >
                  <RiskBadge level={x.severity} />
                  <span>
                    <b>{pp ? pp.location_id : x.prediction_id}</b>
                    <small>
                      {pp ? `${pp.predicted_window} · ` : ''}{pp ? `${pp.risk_score}/100` : x.id}
                    </small>
                  </span>
                  <StatusBadge status={x.status} />
                </button>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
