import { useEffect, useState } from 'react';
import { api } from '../api';

const METRIC_OPTIONS = [
  { key: 'revenue',       label: '營業收入' },
  { key: 'net_income',    label: '淨利' },
  { key: 'gross_margin',  label: '毛利率 %' },
  { key: 'net_margin',    label: '淨利率 %' },
  { key: 'roe',           label: 'ROE %' },
  { key: 'roa',           label: 'ROA %' },
  { key: 'current_ratio', label: '流動比率' },
  { key: 'debt_ratio',    label: '負債比率 %' },
  { key: 'revenue_yoy',   label: '營收 YoY %' },
];

function fmtVal(key, v) {
  if (v == null) return '—';
  const isPct = ['gross_margin', 'net_margin', 'roe', 'roa', 'debt_ratio', 'revenue_yoy', 'operating_margin'].includes(key);
  if (isPct) {
    const cls = v >= 0 ? 'pct' : 'pct neg';
    return <span className={cls}>{v.toFixed(2)}%</span>;
  }
  if (Math.abs(v) >= 1e8) return `${(v / 1e8).toFixed(1)} 億`;
  return v.toLocaleString();
}

export default function RankingTable({ year = 2025, season = 3, industryCode }) {
  const [metric, setMetric] = useState('revenue');
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.getRanking({ metric, year, season, industryCode, limit: 25 })
      .then(setRows)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [metric, year, season, industryCode]);

  return (
    <div className="table-card">
      <h2>🏆 產業排名（{year} Q{season}）</h2>
      <div className="metric-tabs" style={{ marginBottom: 16 }}>
        {METRIC_OPTIONS.map((m) => (
          <button key={m.key} className={`metric-tab${metric === m.key ? ' active' : ''}`}
            onClick={() => setMetric(m.key)}>
            {m.label}
          </button>
        ))}
      </div>
      {loading && <div className="loading-overlay">載入中…</div>}
      {!loading && !rows.length && <div className="empty-state">無資料</div>}
      {!loading && rows.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>排名</th>
              <th>代號</th>
              <th>公司</th>
              <th>產業</th>
              <th>{METRIC_OPTIONS.find((m) => m.key === metric)?.label}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.company_id}>
                <td style={{ textAlign: 'center' }}>{row.rank}</td>
                <td>{row.company_id}</td>
                <td>{row.short_name}</td>
                <td>{row.industry_code}</td>
                <td>{fmtVal(metric, row.metric_value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
