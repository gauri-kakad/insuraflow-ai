import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  ShieldAlert,
  CheckCircle,
  FileWarning,
  UserCheck,
  Download,
  Cpu,
  Info,
} from 'lucide-react';
import { claimsService } from '../services/api';
import { RiskBadge, StatusBadge } from '../components/Badges';

export default function ClaimAnalysisPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [claims, setClaims] = useState([]);
  const [selectedClaimId, setSelectedClaimId] = useState(searchParams.get('claimId') || '');
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    claimsService.list().then((res) => {
      const list = res.data.claims || [];
      setClaims(list);
      if (!selectedClaimId && list.length > 0) {
        setSelectedClaimId(list[0].claim_id);
      }
    });
  }, []);

  useEffect(() => {
    if (!selectedClaimId) return;
    setSearchParams({ claimId: selectedClaimId });
    setLoading(true);
    claimsService
      .getById(selectedClaimId)
      .then((res) => setDetail(res.data))
      .finally(() => setLoading(false));
  }, [selectedClaimId]);

  if (loading && !detail) {
    return <div className="text-sm text-slate-500 py-12 text-center">Loading claim assessment dossier...</div>;
  }

  const claim = detail?.claim;
  const assessment = detail?.assessment;
  const docOut = assessment?.document_intelligence;
  const polOut = assessment?.policy_verification;
  const fraudOut = assessment?.fraud_analysis;
  const finalOut = assessment?.final_assessment;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">Claim Evidence & Risk Analysis</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Consolidated multi-agent findings, policy coverage checks, and explainable fraud risk indicators.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedClaimId}
            onChange={(e) => setSelectedClaimId(e.target.value)}
            className="px-3.5 py-2 rounded-lg border border-slate-300 bg-white text-sm font-medium text-navy-900"
          >
            {claims.map((c) => (
              <option key={c.claim_id} value={c.claim_id}>
                {c.claim_id} — {c.policyholder_name}
              </option>
            ))}
          </select>

          {claim && (
            <>
              <button
                onClick={() => claimsService.downloadReport(claim.claim_id)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium rounded-lg"
              >
                <Download className="w-4 h-4" />
                <span>PDF Report</span>
              </button>
              <Link
                to={`/review?claimId=${claim.claim_id}`}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white text-sm font-medium rounded-lg"
              >
                <UserCheck className="w-4 h-4" />
                <span>Proceed to Human Review</span>
              </Link>
            </>
          )}
        </div>
      </div>

      {claim && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <span className="text-xs text-slate-400 block">Claim Reference</span>
            <span className="font-bold text-navy-900">{claim.claim_id}</span>
          </div>
          <div>
            <span className="text-xs text-slate-400 block">Policyholder & Vehicle</span>
            <span className="font-semibold text-slate-800 block">{claim.policyholder_name}</span>
            <span className="text-xs text-slate-500 font-mono">{claim.vehicle_number} • {claim.vehicle_model}</span>
          </div>
          <div>
            <span className="text-xs text-slate-400 block">Claimed Amount</span>
            <span className="font-bold text-navy-900">
              INR {Number(claim.claimed_amount || 0).toLocaleString('en-IN')}
            </span>
          </div>
          <div>
            <span className="text-xs text-slate-400 block">Fraud Risk Score</span>
            <div className="mt-0.5">
              <RiskBadge level={claim.risk_level} score={claim.risk_score} />
            </div>
          </div>
          <div>
            <span className="text-xs text-slate-400 block">Workflow Status</span>
            <div className="mt-0.5">
              <StatusBadge status={claim.status} />
            </div>
          </div>
        </div>
      )}

      {!assessment ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center space-y-3">
          <p className="text-sm text-slate-600">
            This claim has not yet been processed by the multi-agent pipeline.
          </p>
          <Link
            to={`/processing?claimId=${selectedClaimId}`}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg"
          >
            <Cpu className="w-4 h-4" />
            <span>Open AI Processing Center</span>
          </Link>
        </div>
      ) : (
        <>
          {/* Agent 4 Final Recommendation Banner */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-blue-600">
                  Agent 4 Synthesis • {assessment.model_used}
                </span>
                <h2 className="text-lg font-bold text-navy-900 mt-0.5">
                  Recommended Action: {finalOut.recommended_next_action}
                </h2>
              </div>
              <div className="text-right">
                <span className="text-xs text-slate-400 block">Preliminary Eligible Payout Estimate</span>
                <span className="text-lg font-bold text-emerald-700">
                  {finalOut.estimated_eligible_amount !== null && finalOut.estimated_eligible_amount !== undefined
                    ? `INR ${Number(finalOut.estimated_eligible_amount).toLocaleString('en-IN')}`
                    : 'Withheld Pending Verification'}
                </span>
              </div>
            </div>

            <p className="text-sm text-slate-700 leading-relaxed">{finalOut.explanation}</p>

            <div className="bg-blue-50/70 border border-blue-200 rounded-lg p-3.5 text-xs text-blue-900 flex items-start gap-2.5">
              <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
              <span>
                <strong>Human Review Mandatory:</strong> InsuraFlow AI provides structured decision support only. An authorized claims officer must review and confirm the final decision.
              </span>
            </div>
          </div>

          {/* 3 Columns: Document Intelligence, Policy Verification, Fraud Explanation */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Document Extraction */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
              <div className="flex items-center gap-2 text-navy-900 font-semibold text-base border-b border-slate-100 pb-3">
                <CheckCircle className="w-4 h-4 text-blue-600" />
                <span>Document Intelligence</span>
              </div>
              <dl className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Policy Number</dt>
                  <dd className="font-mono font-semibold">{docOut.policy_number}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Vehicle Number</dt>
                  <dd className="font-mono font-semibold">{docOut.vehicle_number}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Accident Date</dt>
                  <dd className="font-medium">{docOut.accident_date}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Location</dt>
                  <dd className="font-medium">{docOut.accident_location}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Invoice Refs</dt>
                  <dd className="font-mono font-medium">
                    {docOut.invoice_numbers?.length ? docOut.invoice_numbers.join(', ') : 'None extracted'}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Extraction Confidence</dt>
                  <dd className="font-semibold text-emerald-700">{Math.round((docOut.confidence || 0) * 100)}%</dd>
                </div>
              </dl>
              {docOut.validation_notes?.length > 0 && (
                <div className="pt-2 border-t border-slate-100">
                  <p className="text-xs font-semibold text-amber-700 mb-1">Cross-Document Notes</p>
                  <ul className="text-xs text-slate-600 space-y-1">
                    {docOut.validation_notes.map((n, i) => (
                      <li key={i}>• {n}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Policy Verification */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
              <div className="flex items-center gap-2 text-navy-900 font-semibold text-base border-b border-slate-100 pb-3">
                <FileWarning className="w-4 h-4 text-indigo-600" />
                <span>Policy Verification</span>
              </div>
              <dl className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Policy Valid on Incident</dt>
                  <dd className={`font-semibold ${polOut.policy_valid ? 'text-emerald-700' : 'text-red-600'}`}>
                    {polOut.policy_valid ? 'Yes (Active)' : 'No / Invalid'}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Coverage Type</dt>
                  <dd className="font-medium">{polOut.coverage_type}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Policy Period</dt>
                  <dd className="font-mono">{polOut.policy_start_date} to {polOut.policy_end_date}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Coverage Limit (IDV)</dt>
                  <dd className="font-semibold">INR {Number(polOut.coverage_limit || 0).toLocaleString('en-IN')}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Compulsory Deductible</dt>
                  <dd className="font-medium">INR {Number(polOut.deductible || 0).toLocaleString('en-IN')}</dd>
                </div>
              </dl>
              <p className="text-xs text-slate-600 pt-2 border-t border-slate-100">{polOut.explanation}</p>
              {polOut.missing_documents?.length > 0 && (
                <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900">
                  <strong>Missing Documents:</strong> {polOut.missing_documents.join(', ')}
                </div>
              )}
            </div>

            {/* Fraud Risk Score Explanation Panel */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2 text-navy-900 font-semibold text-base">
                  <ShieldAlert className="w-4 h-4 text-red-600" />
                  <span>Fraud Risk Explanation</span>
                </div>
                <span className="text-sm font-bold text-navy-900">{fraudOut.risk_score}/100</span>
              </div>

              <p className="text-xs text-slate-600 leading-relaxed">{fraudOut.explanation}</p>

              {fraudOut.indicators?.length === 0 ? (
                <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800">
                  No rule-based or pattern anomalies triggered for this submission.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {fraudOut.indicators.map((ind, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-navy-900">{ind.type}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            ind.severity === 'High'
                              ? 'bg-red-100 text-red-700'
                              : ind.severity === 'Medium'
                              ? 'bg-amber-100 text-amber-700'
                              : 'bg-slate-200 text-slate-700'
                          }`}
                        >
                          {ind.severity} • {ind.source}
                        </span>
                      </div>
                      <p className="text-slate-600">{ind.evidence}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
