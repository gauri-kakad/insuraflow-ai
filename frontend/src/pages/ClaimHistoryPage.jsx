import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, Eye, UserCheck, Trash2 } from 'lucide-react';
import { claimsService } from '../services/api';
import { RiskBadge, StatusBadge } from '../components/Badges';

export default function ClaimHistoryPage() {
  const [claims, setClaims] = useState([]);
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [dateFrom, setDateFrom] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchClaims = () => {
    setLoading(true);
    claimsService
      .list({
        search: search || undefined,
        risk_level: riskFilter !== 'All' ? riskFilter : undefined,
        status: statusFilter !== 'All' ? statusFilter : undefined,
        date_from: dateFrom || undefined,
      })
      .then((res) => setClaims(res.data.claims || []))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchClaims();
  }, [riskFilter, statusFilter, dateFrom]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchClaims();
  };

  const handleDelete = async (claimId) => {
    if (!window.confirm(`Delete claim ${claimId} from the repository?`)) return;
    await claimsService.delete(claimId);
    fetchClaims();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-navy-900">Claim History & Repository</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Search and filter all submitted motor insurance claims, historical assessments, and officer decisions.
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-wrap items-center gap-3">
        <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[220px] relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-2.5" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search Claim ID, Policy #, Vehicle #, or Name..."
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-slate-300 text-sm"
          />
        </form>

        <div className="flex items-center gap-2 text-xs">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm"
          >
            <option value="All">All Risk Levels</option>
            <option value="Low">Low Risk</option>
            <option value="Medium">Medium Risk</option>
            <option value="High">High Risk</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm"
          >
            <option value="All">All Statuses</option>
            <option value="Submitted">Submitted</option>
            <option value="Pending Human Review">Pending Human Review</option>
            <option value="Additional Docs Required">Additional Docs Required</option>
            <option value="Under Investigation">Under Investigation</option>
            <option value="Reviewed">Reviewed</option>
            <option value="Approved by Officer">Approved by Officer</option>
            <option value="Rejected by Officer">Rejected by Officer</option>
            <option value="Settled">Settled</option>
          </select>

          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            title="Filter from submission date"
            className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">Claim ID</th>
                <th className="px-4 py-3">Policy & Vehicle</th>
                <th className="px-4 py-3">Accident Date</th>
                <th className="px-4 py-3">Claimed</th>
                <th className="px-4 py-3">Risk Level</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500 text-sm">
                    Loading claims...
                  </td>
                </tr>
              ) : claims.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500 text-sm">
                    No motor claims match your filter criteria.
                  </td>
                </tr>
              ) : (
                claims.map((c) => (
                  <tr key={c.claim_id} className="hover:bg-slate-50/80">
                    <td className="px-4 py-3 font-semibold text-navy-900">{c.claim_id}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-800">{c.policyholder_name}</div>
                      <div className="text-xs text-slate-500 font-mono">
                        {c.policy_number} • {c.vehicle_number}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{c.accident_date}</td>
                    <td className="px-4 py-3 font-medium">
                      INR {Number(c.claimed_amount || 0).toLocaleString('en-IN')}
                    </td>
                    <td className="px-4 py-3">
                      <RiskBadge level={c.risk_level} score={c.risk_score} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex items-center gap-2">
                        <Link
                          to={`/analysis?claimId=${c.claim_id}`}
                          title="View Analysis"
                          className="p-1.5 rounded-lg text-blue-600 hover:bg-blue-50"
                        >
                          <Eye className="w-4 h-4" />
                        </Link>
                        <Link
                          to={`/review?claimId=${c.claim_id}`}
                          title="Human Review"
                          className="p-1.5 rounded-lg text-indigo-600 hover:bg-indigo-50"
                        >
                          <UserCheck className="w-4 h-4" />
                        </Link>
                        <button
                          onClick={() => handleDelete(c.claim_id)}
                          title="Delete Claim"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
