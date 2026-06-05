import { useEffect, useState } from 'react';
import { api } from '../api';

export default function CompanyPicker({ industryCode, value, onChange }) {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.getCompanies(industryCode)
      .then(setCompanies)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [industryCode]);

  return (
    <div className="control-group">
      <label>公司{loading ? '（載入中...）' : `（${companies.length} 家）`}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading}
      >
        <option value="">請選擇公司</option>
        {companies.map((co) => (
          <option key={co.company_id} value={co.company_id}>
            {co.company_id} {co.short_name}
          </option>
        ))}
      </select>
    </div>
  );
}
