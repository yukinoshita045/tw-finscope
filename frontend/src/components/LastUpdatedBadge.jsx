import { useEffect, useState } from 'react';
import { api } from '../api';

export default function LastUpdatedBadge() {
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getMeta()
      .then(setMeta)
      .catch(() => setMeta(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <span className="badge loading">⏳ 載入中...</span>;
  if (!meta?.last_etl_run) return <span className="badge stale">⚠ 尚無 ETL 記錄</span>;

  const d = new Date(meta.last_etl_run);
  const fmt = d.toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false });

  return (
    <div style={{ textAlign: 'right' }}>
      <span className="badge">✅ 資料更新：{fmt}</span>
      <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.7)', marginTop: 4 }}>
        {meta.total_companies} 家公司｜{meta.total_metric_rows?.toLocaleString()} 筆指標
      </div>
    </div>
  );
}
