/**
 * api.js — FastAPI 後端 API 封裝
 */

const API_BASE = import.meta.env.VITE_API_BASE || '';

async function apiFetch(path, params = {}) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') {
      url.searchParams.set(k, v);
    }
  });
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export const api = {
  getCompanies: (industryCode) =>
    apiFetch('/api/companies', industryCode ? { industry_code: industryCode } : {}),

  getIndustries: () => apiFetch('/api/industries'),

  getMetrics: ({ companyIds, from, to, season } = {}) =>
    apiFetch('/api/metrics', {
      company_ids: Array.isArray(companyIds) ? companyIds.join(',') : companyIds,
      from,
      to,
      season,
    }),

  getTimeseries: ({ companyId, metric, from = 2022, to = 2025 }) =>
    apiFetch('/api/timeseries', { company_id: companyId, metric, from, to }),

  getRanking: ({ metric, year, season, industryCode, limit = 20 }) =>
    apiFetch('/api/ranking', { metric, year, season, industry_code: industryCode, limit }),

  getIndustryAverage: ({ industryCode, metric, from = 2022, to = 2025 }) =>
    apiFetch('/api/industry-average', {
      industry_code: industryCode,
      metric,
      from,
      to,
    }),

  getMeta: () => apiFetch('/api/meta'),
};
