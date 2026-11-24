import React from 'react';

export function RiskBadge({ level, score }) {
  const styles = {
    Low: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    Medium: 'bg-amber-50 text-amber-700 border-amber-200',
    High: 'bg-red-50 text-red-700 border-red-200',
    Pending: 'bg-slate-100 text-slate-600 border-slate-200',
  };
  const cls = styles[level] || styles.Pending;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${cls}`}>
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          level === 'Low'
            ? 'bg-emerald-500'
            : level === 'Medium'
            ? 'bg-amber-500'
            : level === 'High'
            ? 'bg-red-500'
            : 'bg-slate-400'
        }`}
      />
      {level || 'Pending'} {typeof score === 'number' ? `(${score})` : ''}
    </span>
  );
}

export function StatusBadge({ status }) {
  const styles = {
    Submitted: 'bg-slate-100 text-slate-700 border-slate-200',
    Processing: 'bg-blue-50 text-blue-700 border-blue-200',
    'Processing Failed': 'bg-red-50 text-red-700 border-red-200',
    'Pending Human Review': 'bg-indigo-50 text-indigo-700 border-indigo-200',
    'Additional Docs Required': 'bg-amber-50 text-amber-700 border-amber-200',
    'Under Investigation': 'bg-orange-50 text-orange-700 border-orange-200',
    Reviewed: 'bg-teal-50 text-teal-700 border-teal-200',
    'Approved by Officer': 'bg-emerald-50 text-emerald-700 border-emerald-200',
    'Rejected by Officer': 'bg-rose-50 text-rose-700 border-rose-200',
    Settled: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  };
  const cls = styles[status] || 'bg-slate-100 text-slate-700 border-slate-200';
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium border ${cls}`}>
      {status}
    </span>
  );
}
