import { useEffect, useState } from 'react';
import { api } from '../api';

/**
 * 財務健康分數（複合指標, 創意加分）
 * 加權方式:
 *   毛利率 30% + ROE 25% + 流動比率 20% + 低負債比率 15% + 營收 YoY 10%
 */
export default function HealthScoreCard({ companyId, year, season }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!companyId) {
      setData(null);
      return;
    }
    setLoading(true);
    api
      .getMetrics({ companyIds: [companyId], from: year, to: year, season })
      .then((metrics) => {
        const m = metrics.find((r) => r.company_id === companyId);
        if (!m) {
          setData(null);
          return;
        }
        const gm = Math.min(Math.max(((m.gross_margin ?? 0) / 60) * 30, 0), 30);
        const roe = Math.min(Math.max(((m.roe ?? 0) / 25) * 25, 0), 25);
        const cr = Math.min(Math.max((((m.current_ratio ?? 1) - 1) / 2) * 20, 0), 20);
        const dr = Math.min(Math.max((1 - (m.debt_ratio ?? 50) / 100) * 15, 0), 15);
        const yoy = Math.min(Math.max(((m.revenue_yoy ?? 0) / 20) * 10, 0), 10);
        setData({
          total: Math.round(gm + roe + cr + dr + yoy),
          gm: m.gross_margin,
          roe: m.roe,
          cr: m.current_ratio,
          dr: m.debt_ratio,
          yoy: m.revenue_yoy,
        });
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [companyId, year, season]);

  const color = !data
    ? '#a0aec0'
    : data.total >= 80
    ? '#38a169'
    : data.total >= 60
    ? '#3182ce'
    : data.total >= 40
    ? '#dd6b20'
    : '#e53e3e';

  return (
    <div
      className="chart-card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
      }}
    >
      <h2>⭐ 財務健康分數</h2>
      {loading && <div className="loading-overlay">計算中…</div>}
      {!loading && !data && <div className="empty-state">請選擇公司</div>}
      {!loading && data && (
        <>
          <div
            style={{
              fontSize: '5rem',
              fontWeight: 800,
              color,
              lineHeight: 1.1,
              marginTop: 16,
            }}
          >
            {data.total}
          </div>
          <div style={{ fontSize: '1rem', color: '#718096', marginBottom: 20 }}>/ 100 分</div>
          <table style={{ fontSize: '0.85rem', width: '100%', maxWidth: 280 }}>
            <tbody>
              {[
                ['毛利率', data.gm, '%'],
                ['ROE', data.roe, '%'],
                ['流動比率', data.cr, 'x'],
                ['負債比率', data.dr, '%'],
                ['營收 YoY', data.yoy, '%'],
              ].map(([label, val, unit]) => (
                <tr key={label}>
                  <td style={{ textAlign: 'left', padding: '4px 8px', color: '#4a5568' }}>
                    {label}
                  </td>
                  <td style={{ textAlign: 'right', padding: '4px 8px', fontWeight: 600 }}>
                    {val != null ? `${val.toFixed(1)} ${unit}` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
