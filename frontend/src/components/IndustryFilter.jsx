import { useEffect, useState } from 'react';
import { api } from '../api';

export default function IndustryFilter({ value, onChange }) {
  const [industries, setIndustries] = useState([]);

  useEffect(() => {
    api.getIndustries().then(setIndustries).catch(console.error);
  }, []);

  return (
    <div className="control-group">
      <label>產業別</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">全部產業</option>
        {industries.map((ind) => (
          <option key={ind.industry_code} value={ind.industry_code}>
            {ind.industry_name}（{ind.company_count} 家）
          </option>
        ))}
      </select>
    </div>
  );
}
