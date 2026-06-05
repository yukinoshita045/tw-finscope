import { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend,
} from 'chart.js';
import { Radar } from 'react-chartjs-2';
import { api } from '../api';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

const RATIO_METRICS = ['gross_margin', 'operating_margin', 'net_margin', 'roe', 'roa'];
const RATIO_LABELS  = ['毛利率', '營業利益率', '淨利率', 'ROE', 'ROA'];
const COLORS = ['rgba(49,130,206,0.6)', 'rgba(56,161,105,0.6)', 'rgba(221,107,32,0.6)', 'rgba(128,90,213,0.6)'];

export default function RatioCompare({ companyIds = [], year = 2025, season = 3 }) {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!companyIds.length) { setChartData(null); return; }
    setLoading(true);
    api.getMetrics({ companyIds, from: year, to: year, season })
      .then((rows) => {
        const datasets = companyIds.map((cid, i) => {
          const row = rows.find((r) => r.company_id === cid);
          return {
            label: cid,
            data: RATIO_METRICS.map((m) => row?.[m] ?? 0),
            backgroundColor: COLORS[i % COLORS.length],
            borderColor: COLORS[i % COLORS.length].replace('0.6', '1'),
            pointBackgroundColor: COLORS[i % COLORS.length].replace('0.6', '1'),
          };
        });
        setChartData({ labels: RATIO_LABELS, datasets });
      }).catch(console.error).finally(() => setLoading(false));
  }, [companyIds.join(','), year, season]);

  return (
    <div className="chart-card">
      <h2>🕸 財務比率雷達（{year} Q{season}）</h2>
      {loading && <div className="loading-overlay">載入中…</div>}
      {!loading && !chartData && <div className="empty-state">請選擇公司</div>}
      {!loading && chartData && (
        <Radar
          data={chartData}
          options={{
            responsive: true,
            scales: { r: { ticks: { callback: (v) => `${v}%` } } },
            plugins: { legend: { position: 'top' } },
          }}
        />
      )}
    </div>
  );
}
