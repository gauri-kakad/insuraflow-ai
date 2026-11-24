import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { UserCheck, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import { claimsService } from '../services/api';
import { RiskBadge, StatusBadge } from '../components/Badges';

export default function HumanReviewPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [claims, setClaims] = useState([]);
  const [selectedClaimId, setSelectedClaimId] = useState(searchParams.get('claimId') || '');
  const [detail, setDetail] = useState(null);

  const [action, setAction] = useState('Mark Reviewed');
  const [notes, setNotes] = useState('');
  const [approvedAmount, setApprovedAmount] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState({ type: '', text: '' });

  const loadClaimDetail = (cid) => {
    if (!cid) return;
    claimsService.getById(cid).then((res) => {
      setDetail(res.data);
      const elig = res.data.assessment?.final_assessment?.estimated_eligible_amount;
      setApprovedAmount(elig !== null && elig !== undefined ? String(elig) : '');
    });
  };

  useEffect(() => {
    claimsService.list().then((res) => {
      const list = res.data.claims || [];
      setClaims(list);
      const initialId = selectedClaimId || (list[0]?.claim_id ?? '');
      setSelectedClaimId(initialId);
      if (initialId) loadClaimDetail(initialId);
    });
  }, []);

  const handleSelectClaim = (cid) => {
    setSelectedClaimId(cid);
    setSearchParams({ claimId: cid });
    setFeedback({ type: '', text: '' });
    loadClaimDetail(cid);
  };

  const handleSubmitReview = async (e) => {
    e.preventDefault();
    setFeedback({ type: '', text: '' });
    if (notes.trim().length < 3) {
      setFeedback({ type: 'error', text: 'Please enter detailed officer review notes.' });
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        action,
        notes: notes.trim(),
        approved_amount:
          action === 'Approve Payout Recommendation' && approvedAmount !== ''
            ? Number(approvedAmount)
            : null,
        requested_documents:
          action === 'Request Additional Documents'
            ? detail?.assessment?.final_assessment?.missing_documents || []
            : [],
      };
      await claimsService.submitReview(selectedClaimId, payload);
      setFeedback({
        type: 'success',
        text: `Officer action '${action}' recorded in the immutable audit trail.`,
      });
      setNotes('');
      loadClaimDetail(selectedClaimId);
      const listRes = await claimsService.list();
      setClaims(listRes.data.claims || []);
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to save human review decision.',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const claim = detail?.claim;
  const finalOut = detail?.assessment?.final_assessment;
  const auditLogs = detail?.audit_logs || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">Human Review & Adjudication Center</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Authorize officer determinations independently from AI recommendations. Every action is permanently audited.
          </p>
        </div>

        <select
          value={selectedClaimId}
          onChange={(e) => handleSelectClaim(e.target.value)}
          className="px-3.5 py-2 rounded-lg border border-slate-300 bg-white text-sm font-medium text-navy-900"
        >
          {claims.map((c) => (
            <option key={c.claim_id} value={c.claim_id}>
              {c.claim_id} — {c.policyholder_name} ({c.status})
            </option>
          ))}
        </select>
      </div>

      {claim && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: AI Decision-Support Summary */}
          <div className="lg:col-span-2 space-y-5">
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div>
                  <h2 className="text-base font-bold text-navy-900">
                    {claim.claim_id} — {claim.policyholder_name}
                  </h2>
                  <p className="text-xs text-slate-500">
                    Policy {claim.policy_number} • Vehicle {claim.vehicle_number} ({claim.vehicle_model})
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <RiskBadge level={claim.risk_level} score={claim.risk_score} />
                  <StatusBadge status={claim.status} />
                </div>
              </div>

              {finalOut ? (
                <div className="space-y-3 text-sm">
                  <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200">
                    <span className="text-xs font-semibold uppercase text-slate-500 block">
                      AI System Recommendation (Advisory Only)
                    </span>
                    <span className="text-base font-bold text-navy-900">{finalOut.recommended_next_action}</span>
                    <p className="text-xs text-slate-600 mt-1">{finalOut.explanation}</p>
                  </div>

                  {finalOut.unresolved_questions?.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                        Items Flagged for Officer Verification
                      </p>
                      <ul className="space-y-1 text-xs text-slate-700 bg-amber-50/70 border border-amber-200 rounded-lg p-3">
                        {finalOut.unresolved_questions.map((q, idx) => (
                          <li key={idx}>• {q}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-slate-500">AI assessment not yet executed for this claim.</p>
              )}
            </div>

            {/* Officer Decision Form */}
            <form onSubmit={handleSubmitReview} className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                <UserCheck className="w-5 h-5 text-navy-900" />
                <h2 className="text-base font-bold text-navy-900">Record Human Officer Decision</h2>
              </div>

              {feedback.text && (
                <div
                  className={`p-3.5 rounded-lg text-xs flex items-center gap-2 border ${
                    feedback.type === 'success'
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                      : 'bg-red-50 border-red-200 text-red-700'
                  }`}
                >
                  {feedback.type === 'success' ? (
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 shrink-0" />
                  )}
                  <span>{feedback.text}</span>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Officer Action *</label>
                  <select
                    value={action}
                    onChange={(e) => setAction(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm font-medium"
                  >
                    <option value="Mark Reviewed">Mark Claim as Reviewed</option>
                    <option value="Request Additional Documents">Request Additional Documents</option>
                    <option value="Mark Under Investigation">Mark Claim as Under Investigation (SIU)</option>
                    <option value="Approve Payout Recommendation">Approve Claim Settlement (Human Authorization)</option>
                    <option value="Reject Claim">Reject Claim (Human Authorization)</option>
                  </select>
                </div>

                {action === 'Approve Payout Recommendation' && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">
                      Authorized Settlement Amount (INR)
                    </label>
                    <input
                      type="number"
                      value={approvedAmount}
                      onChange={(e) => setApprovedAmount(e.target.value)}
                      min="0"
                      className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm font-semibold"
                    />
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Officer Review Notes & Rationale *
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  required
                  placeholder="Document your verification findings, surveyor notes, or rationale for the decision..."
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="px-5 py-2.5 bg-navy-900 hover:bg-navy-800 text-white text-sm font-semibold rounded-lg disabled:opacity-60"
              >
                {submitting ? 'Saving Audit Record...' : 'Record Officer Decision'}
              </button>
            </form>
          </div>

          {/* Right: Immutable Audit Trail */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3 mb-4">
              <Clock className="w-4 h-4 text-navy-900" />
              <h2 className="text-base font-semibold text-navy-900">Claim Audit Trail</h2>
            </div>

            <div className="space-y-4 max-h-[540px] overflow-y-auto pr-1">
              {auditLogs.map((log) => (
                <div key={log.audit_id} className="border-l-2 border-navy-800 pl-3 py-0.5 text-xs">
                  <div className="font-semibold text-navy-900">{log.action}</div>
                  <p className="text-slate-600 mt-1">{log.details}</p>
                  <p className="text-[11px] text-slate-400 mt-1">
                    {log.actor} • {new Date(log.timestamp).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
