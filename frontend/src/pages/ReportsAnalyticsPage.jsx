import React, { useEffect, useState } from 'react';
import { Download, FileSpreadsheet } from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
} from 'recharts';
import { claimsService } from '../services/api';
import { RiskBadge, StatusBadge } from '../components/Badges';

export default function ReportsAnalyticsPage() {
  const [analytics, setAnalytics] = useState(null);
  const [claims, setClaims] = useState([]);
  const [downloadingId, setDownloadingId] = useState('');

  useEffect(() => {
    Promise.all([claimsService.getDashboardAnalytics(), claimsService.list()]).then(
      ([aRes, cRes]) => {
        setAnalytics(aRes.data);
        setClaims(cRes.data.claims || []);
      }
    );
  }, []);

  const handleDownloadPdf = async (claimId) => {
    setDownloadingId(claimId);
    try {
      await claimsService.downloadReport(claimId);
    } finally {
      setDownloadingId('');
    }
  };

  if (!analytics) {
    return <div className="text-sm text-slate-500 py-12 text-center">Loading analytics & reports...</div>;
  }

  const { kpis, anomaly_categories, processing_trend } = analytics;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-navy-900">Reports & Risk Analytics</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Operational telemetry, anomaly category breakdowns, and downloadable PDF claim assessment dossiers.
        </p>
      </div>

      {/* Summary Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <span className="text-xs text-slate-500">Total Processed Claims</span>
          <div className="text-2xl font-bold text-navy-900 mt-1">{kpis.total_claims}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <span className="text-xs text-slate-500">Under Investigation (SIU)</span>
          <div className="text-2xl font-bold text-orange-600 mt-1">{kpis.investigation_claims}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <span className="text-xs text-slate-500">High-Risk Flagged</span>
          <div className="text-2xl font-bold text-red-600 mt-1">{kpis.high_risk_claims}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <span className="text-xs text-slate-500">Mean Workflow Latency</span>
          <div className="text-2xl font-bold text-emerald-700 mt-1">
            {(kpis.avg_processing_ms / 1000).toFixed(2)} sec
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <h2 className="text-base font-semibold text-navy-900 mb-1">Common Anomaly Categories</h2>
          <p className="text-xs text-slate-500 mb-4">Frequency of rule-based and AI anomaly flags across assessed claims</p>
          <div className="h-64">
            {anomaly_categories.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No anomaly indicators recorded yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={anomaly_categories} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
                  <YAxis dataKey="category" type="category" width={150} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" name="Occurrences" fill="#0f2942" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <h2 className="text-base font-semibold text-navy-900 mb-1">Processing Time Analytics (Seconds)</h2>
          <p className="text-xs text-slate-500 mb-4">End-to-end 4-agent LangGraph execution time by date</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={processing_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="avg_processing_sec"
                  name="Avg Processing (s)"
                  stroke="#2563eb"
                  strokeWidth={2.5}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Downloadable PDF Assessment Dossiers */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center gap-2">
          <FileSpreadsheet className="w-5 h-5 text-navy-900" />
          <h2 className="text-base font-semibold text-navy-900">Downloadable Claim Assessment PDF Reports</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">Claim ID</th>
                <th className="px-4 py-3">Policyholder</th>
                <th className="px-4 py-3">Policy #</th>
                <th className="px-4 py-3">Risk Level</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Assessment Dossier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {claims.map((c) => (
                <tr key={c.claim_id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-semibold text-navy-900">{c.claim_id}</td>
                  <td className="px-4 py-3">{c.policyholder_name}</td>
                  <td className="px-4 py-3 font-mono text-xs">{c.policy_number}</td>
                  <td className="px-4 py-3">
                    <RiskBadge level={c.risk_level} score={c.risk_score} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDownloadPdf(c.claim_id)}
                      disabled={downloadingId === c.claim_id}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 rounded-lg text-xs font-semibold transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>{downloadingId === c.claim_id ? 'Generating...' : 'Download PDF'}</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
