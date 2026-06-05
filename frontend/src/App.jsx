import { useState } from 'react';
import CompanyPicker from './components/CompanyPicker';
import HealthScoreCard from './components/HealthScoreCard';
import IndustryFilter from './components/IndustryFilter';
import LastUpdatedBadge from './components/LastUpdatedBadge';
import MarginChart from './components/MarginChart';
import RankingTable from './components/RankingTable';
import RatioCompare from './components/RatioCompare';
import TrendChart from './components/TrendChart';

export default function App() {
  const [industryCode, setIndustryCode] = useState('');
  const [primaryCompany, setPrimaryCompany] = useState('');
  const [compareCompany, setCompareCompany] = useState('');
  const [fromYear, setFromYear] = useState(2022);
  const [toYear, setToYear] = useState(2025);
  const [season, setSeason] = useState(3);
  const [showIndustryAvg, setShowIndustryAvg] = useState(true);

  const companyIds = [primaryCompany, compareCompany].filter(Boolean);

  return (
    <div className="app">
      <header>
        <div>
          <h1>🇹🇼 tw-finscope</h1>
          <p>台灣上市公司財務健康儀表板 — 資料來源:MOPS 公開資訊觀測站</p>
        </div>
        <LastUpdatedBadge />
      </header>

      {/* 控制列 */}
      <div className="controls">
        <IndustryFilter
          value={industryCode}
          onChange={(v) => {
            setIndustryCode(v);
            setPrimaryCompany('');
            setCompareCompany('');
          }}
        />
        <CompanyPicker
          industryCode={industryCode}
          value={primaryCompany}
          onChange={setPrimaryCompany}
        />
        <CompanyPicker
          industryCode={industryCode}
          value={compareCompany}
          onChange={setCompareCompany}
        />

        <div className="control-group">
          <label>起始年</label>
          <select value={fromYear} onChange={(e) => setFromYear(+e.target.value)}>
            {[2020, 2021, 2022, 2023, 2024, 2025].map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label>結束年</label>
          <select value={toYear} onChange={(e) => setToYear(+e.target.value)}>
            {[2022, 2023, 2024, 2025].map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label>比率比較季度</label>
          <select value={season} onChange={(e) => setSeason(+e.target.value)}>
            {[1, 2, 3, 4].map((s) => (
              <option key={s} value={s}>
                Q{s}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label>產業平均疊圖</label>
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 12px',
              border: '1px solid #e2e8f0',
              borderRadius: 8,
              background: 'white',
              cursor: 'pointer',
              minWidth: 180,
            }}
          >
            <input
              type="checkbox"
              checked={showIndustryAvg}
              onChange={(e) => setShowIndustryAvg(e.target.checked)}
            />
            {showIndustryAvg ? '已開啟' : '已關閉'}
          </label>
        </div>
      </div>

      {/* 圖表區 */}
      <div className="charts-grid">
        <TrendChart
          companyIds={companyIds}
          fromYear={fromYear}
          toYear={toYear}
          showIndustryAvg={showIndustryAvg}
          industryCode={industryCode}
        />
        <MarginChart companyId={primaryCompany} fromYear={fromYear} toYear={toYear} />
        <RatioCompare companyIds={companyIds} year={toYear} season={season} />
        <HealthScoreCard companyId={primaryCompany} year={toYear} season={season} />
      </div>

      {/* 排名表 */}
      <RankingTable year={toYear} season={season} industryCode={industryCode} />

      <footer
        style={{
          textAlign: 'center',
          color: '#718096',
          fontSize: '0.75rem',
          padding: '20px 0',
        }}
      >
        tw-finscope · 資料來源 MOPS 公開資訊觀測站 · 每週一自動更新
      </footer>
    </div>
  );
}
