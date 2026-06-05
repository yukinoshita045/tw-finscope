import { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement,
  Title, Tooltip, Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { api } from '../api';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

export default function MarginChart({ companyId, fromYear = 2022, toYear = 2025 }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!companyId) { setData(null); return; }
    setLoading(true);
    Promise.all([
      api.getTimeseries({ companyId, metric: 'gross_margin', from: fromYear, to: toYear }),
      api.getTimeseries({ companyId, metric: 'operating_margin', from: fromYear, to: toYear }),
      api.getTimeseries({ companyId, metric: 'net_margin', from: fromYear, to: toYear }),
    ]).then(([gm, om, nm]) => {
      const labels = gm.map((p) => p.period_label);
      setData({
        labels,
        datasets: [
          { label: '毛利率 %', data: gm.map((p) => p.value), backgroundColor: 'rgba(56,161,105,0.75)' },
          { label: '營業利益率 %', data: om.map((p) => p.value), backgroundColor: 'rgba(49,130,206,0.75)' },
          { label: '淨利率 %', data: nm.map((p) => p.value), backgroundColor: 'rgba(221,107,32,0.75)' },
        ],
      });
    }).catch(console.error).finally(() => setLoading(false));
  }, [companyId, fromYear, toYear]);

  return (
    <div className="chart-card">
      <h2>📊 利潤率分解（%）</h2>
      {loading && <div className="loading-overlay">載入中…</div>}
      {!loading && !data && <div className="empty-state">請選擇公司</div>}
      {!loading && data && (
        <Bar
          data={data}
          options={{
            responsive: true,
            plugins: { legend: { position: 'top' } },
            scales: {
              y: { ticks: { callback: (v) => `${v?.toFixed(1)}%` } },
            },
          }}
        />
      )}
    </div>
  );
}
