import { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  Title, Tooltip, Legend, Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { api } from '../api';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

const METRIC_OPTIONS = [
  { key: 'revenue',             label: '營業收入' },
  { key: 'gross_profit',        label: '毛利' },
  { key: 'operating_income',    label: '營業利益' },
  { key: 'net_income',          label: '淨利' },
  { key: 'operating_cash_flow', label: '營業現金流' },
];

const COLORS = ['#3182ce', '#38a169', '#dd6b20', '#805ad5', '#e53e3e'];

function fmtVal(v) {
  if (v == null) return '—';
  if (Math.abs(v) >= 1e8) return `${(v / 1e8).toFixed(1)} 億`;
  if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(0)} 百萬`;
  return v.toLocaleString();
}

export default function TrendChart({
  companyIds = [],
  fromYear = 2022,
  toYear = 2025,
  showIndustryAvg = false,
  industryCode = '',
}) {
  const [metric, setMetric] = useState('revenue');
  const [datasets, setDatasets] = useState([]);
  const [labels, setLabels] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!companyIds.length) {
      setDatasets([]);
      setLabels([]);
      return;
    }
    setLoading(true);

    const tasks = companyIds.map((cid, idx) =>
      api
        .getTimeseries({ companyId: cid, metric, from: fromYear, to: toYear })
        .then((pts) => ({ kind: 'co', cid, pts, color: COLORS[idx % COLORS.length] }))
        .catch(() => ({ kind: 'co', cid, pts: [], color: COLORS[idx % COLORS.length] })),
    );

    // 創意亮點:產業平均疊圖
    if (showIndustryAvg && industryCode) {
      tasks.push(
        api
          .getIndustryAverage({
            industryCode,
            metric,
            from: fromYear,
            to: toYear,
          })
          .then((pts) => ({ kind: 'avg', pts }))
          .catch(() => ({ kind: 'avg', pts: [] })),
      );
    }

    Promise.all(tasks)
      .then((results) => {
        const coRes = results.filter((r) => r.kind === 'co');
        const avgRes = results.find((r) => r.kind === 'avg');

        const firstWithData = coRes.find((r) => r.pts?.length) || avgRes;
        if (!firstWithData?.pts?.length) {
          setLabels([]);
          setDatasets([]);
          return;
        }

        const lbls = firstWithData.pts.map((p) => p.period_label);
        setLabels(lbls);

        const ds = coRes.map(({ cid, pts, color }) => ({
          label: cid,
          data: pts.map((p) => p.value),
          borderColor: color,
          backgroundColor: color + '22',
          fill: false,
          tension: 0.35,
          pointRadius: 4,
        }));

        if (avgRes?.pts?.length) {
          ds.push({
            label: `產業 ${industryCode} 平均`,
            data: avgRes.pts.map((p) => p.value),
            borderColor: '#718096',
            backgroundColor: '#71809633',
            borderDash: [6, 4],
            tension: 0.3,
            pointRadius: 3,
            fill: false,
          });
        }

        setDatasets(ds);
      })
      .finally(() => setLoading(false));
  }, [companyIds.join(','), metric, fromYear, toYear, showIndustryAvg, industryCode]);

  return (
    <div className="chart-card">
      <h2>📈 損益趨勢{showIndustryAvg && industryCode ? ` · 含產業 ${industryCode} 平均` : ''}</h2>
      <div className="metric-tabs">
        {METRIC_OPTIONS.map((m) => (
          <button
            key={m.key}
            className={`metric-tab${metric === m.key ? ' active' : ''}`}
            onClick={() => setMetric(m.key)}
          >
            {m.label}
          </button>
        ))}
      </div>
      {loading && <div className="loading-overlay">載入中…</div>}
      {!loading && !labels.length && <div className="empty-state">請選擇公司</div>}
      {!loading && labels.length > 0 && (
        <Line
          data={{ labels, datasets }}
          options={{
            responsive: true,
            plugins: {
              legend: { position: 'top' },
              tooltip: {
                callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmtVal(ctx.raw)}` },
              },
            },
            scales: {
              y: { ticks: { callback: (v) => fmtVal(v) } },
            },
          }}
        />
      )}
    </div>
  );
}
