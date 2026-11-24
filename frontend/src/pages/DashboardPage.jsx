import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  Clock,
  UserCheck,
  AlertTriangle,
  Gauge,
  Plus,
  ArrowUpRight,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { claimsService } from '../services/api';
import { RiskBadge, StatusBadge } from '../components/Badges';

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    claimsService
      .getDashboardAnalytics()
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load dashboard metrics.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-sm text-slate-500 py-12 text-center">Loading claims operations metrics...</div>;
  }

  if (error) {
    return (
      <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
        {error}
      </div>
    );
  }

  const { kpis, risk_distribution, processing_trend, recent_claims, recent_activity } = data;

  const statCards = [
    {
      label: 'Total Claims Processed',
      value: kpis.total_claims,
      icon: FileText,
      accent: 'text-blue-600 bg-blue-50',
    },
    {
      label: 'Pending Intake / Docs',
      value: kpis.pending_claims,
      icon: Clock,
      accent: 'text-slate-700 bg-slate-100',
    },
    {
      label: 'Requiring Human Review',
      value: kpis.human_review_required,
      icon: UserCheck,
      accent: 'text-indigo-600 bg-indigo-50',
    },
    {
      label: 'High-Risk Flagged',
      value: kpis.high_risk_claims,
      icon: AlertTriangle,
      accent: 'text-red-600 bg-red-50',
    },
    {
      label: 'Avg. Agent Pipeline Time',
      value: `${(kpis.avg_processing_ms / 1000).toFixed(2)}s`,
      icon: Gauge,
      accent: 'text-emerald-600 bg-emerald-50',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">Claims Operations Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Real-time overview of motor insurance claims, multi-agent triage, and officer review queues.
          </p>
        </div>
        <Link
          to="/submit"
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>New Motor Claim</span>
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.label}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">{card.label}</span>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${card.accent}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-4 text-2xl font-bold text-navy-900">{card.value}</div>
            </div>
          );
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="mb-4">
            <h2 className="text-base font-semibold text-navy-900">Claims Intake & High-Risk Trend</h2>
            <p className="text-xs text-slate-500">Daily claim submissions vs. high-risk anomaly escalations</p>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={processing_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#64748b' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="claims"
                  name="Total Claims"
                  stroke="#2563eb"
                  fill="#dbeafe"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="high_risk"
                  name="High-Risk Escalations"
                  stroke="#ef4444"
                  fill="#fee2e2"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="mb-4">
            <h2 className="text-base font-semibold text-navy-900">Risk Distribution</h2>
            <p className="text-xs text-slate-500">Breakdown by Fraud Detection Agent score</p>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={risk_distribution}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="45%"
                  innerRadius={52}
                  outerRadius={78}
                  paddingAngle={3}
                >
                  {risk_distribution.map((entry, idx) => (
                    <Cell key={idx} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend verticalAlign="bottom" height={32} iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom Row: Recent Claims + Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-base font-semibold text-navy-900">Recent Motor Claims</h2>
            <Link to="/history" className="text-xs font-medium text-blue-600 hover:underline flex items-center gap-1">
              <span>View All</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Claim ID</th>
                  <th className="px-4 py-3">Policyholder</th>
                  <th className="px-4 py-3">Amount</th>
                  <th className="px-4 py-3">Risk</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recent_claims.map((claim) => (
                  <tr key={claim.claim_id} className="hover:bg-slate-50/80">
                    <td className="px-4 py-3 font-medium text-navy-900">{claim.claim_id}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-800">{claim.policyholder_name}</div>
                      <div className="text-xs text-slate-500">{claim.vehicle_number}</div>
                    </td>
                    <td className="px-4 py-3 font-medium">
                      INR {Number(claim.claimed_amount || 0).toLocaleString('en-IN')}
                    </td>
                    <td className="px-4 py-3">
                      <RiskBadge level={claim.risk_level} score={claim.risk_score} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={claim.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/analysis?claimId=${claim.claim_id}`}
                        className="text-xs font-semibold text-blue-600 hover:text-blue-800"
                      >
                        Inspect
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <h2 className="text-base font-semibold text-navy-900 mb-4">Recent System & Audit Activity</h2>
          <div className="space-y-4 max-h-96 overflow-y-auto pr-1">
            {recent_activity.map((act) => (
              <div key={act.audit_id} className="border-l-2 border-blue-600 pl-3 py-0.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-navy-900">{act.action}</span>
                  <span className="text-slate-400">{act.claim_id}</span>
                </div>
                <p className="text-xs text-slate-600 mt-1 line-clamp-2">{act.details}</p>
                <p className="text-[11px] text-slate-400 mt-1">
                  {act.actor} • {new Date(act.timestamp).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
