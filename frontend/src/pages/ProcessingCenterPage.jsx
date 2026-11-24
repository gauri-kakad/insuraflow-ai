import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  CheckCircle2,
  Loader2,
  Clock,
  XCircle,
  RefreshCw,
  ArrowRight,
  Terminal,
} from 'lucide-react';
import { claimsService } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function ProcessingCenterPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { preferDemoMode } = useAuth();

  const [claims, setClaims] = useState([]);
  const [selectedClaimId, setSelectedClaimId] = useState(searchParams.get('claimId') || '');
  const [statusData, setStatusData] = useState(null);
  const [error, setError] = useState('');
  const [triggering, setTriggering] = useState(false);

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

    let active = true;
    const fetchStatus = () => {
      claimsService
        .getStatus(selectedClaimId)
        .then((res) => {
          if (active) {
            setStatusData(res.data);
            setError('');
          }
        })
        .catch((err) => {
          if (active) setError(err.response?.data?.detail || 'Unable to load execution status.');
        });
    };

    fetchStatus();
    const interval = setInterval(() => {
      if (statusData?.claim_status === 'Processing' || statusData?.execution?.status === 'running') {
        fetchStatus();
      }
    }, 1500);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [selectedClaimId, statusData?.claim_status, statusData?.execution?.status]);

  const handleRerun = async () => {
    if (!selectedClaimId) return;
    setTriggering(true);
    setError('');
    try {
      await claimsService.process(selectedClaimId, preferDemoMode);
      const res = await claimsService.getStatus(selectedClaimId);
      setStatusData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to trigger LangGraph workflow.');
    } finally {
      setTriggering(false);
    }
  };

  const execution = statusData?.execution;
  const stages = execution?.stages || [];

  const getStageBadge = (st) => {
    if (st === 'completed') {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full">
          <CheckCircle2 className="w-3.5 h-3.5" /> Completed
        </span>
      );
    }
    if (st === 'running') {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-2.5 py-0.5 rounded-full">
          <Loader2 className="w-3.5 h-3.5 animate-spin" /> Running
        </span>
      );
    }
    if (st === 'failed') {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-700 bg-red-50 border border-red-200 px-2.5 py-0.5 rounded-full">
          <XCircle className="w-3.5 h-3.5" /> Failed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-600 bg-slate-100 border border-slate-200 px-2.5 py-0.5 rounded-full">
        <Clock className="w-3.5 h-3.5" /> Pending
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">AI Processing Center (LangGraph Orchestration)</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Live state inspection across the four specialized motor insurance agents.
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
                {c.claim_id} — {c.policyholder_name} ({c.status})
              </option>
            ))}
          </select>

          <button
            onClick={handleRerun}
            disabled={triggering || !selectedClaimId}
            className="inline-flex items-center gap-2 px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white text-sm font-medium rounded-lg disabled:opacity-60"
          >
            <RefreshCw className={`w-4 h-4 ${triggering ? 'animate-spin' : ''}`} />
            <span>Run / Rerun Workflow</span>
          </button>

          {selectedClaimId && (
            <Link
              to={`/analysis?claimId=${selectedClaimId}`}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg"
            >
              <span>View Assessment</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      {execution && (
        <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-6">
            <div>
              <span className="text-slate-400 block">Execution ID</span>
              <span className="font-mono font-semibold text-navy-900">{execution.execution_id}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Model / Engine</span>
              <span className="font-semibold text-blue-700">{execution.model_used}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Workflow Status</span>
              <span className="font-semibold uppercase text-slate-800">{execution.status}</span>
            </div>
          </div>
          {execution.demo_mode && (
            <span className="px-3 py-1 rounded-md bg-amber-50 border border-amber-200 text-amber-800 font-medium">
              Deterministic Demo Mode Active (Not Live Gemini)
            </span>
          )}
        </div>
      )}

      {/* 4 Agent Stages */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {stages.map((stage, index) => (
          <div
            key={stage.agent_id}
            className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between space-y-4"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2.5">
                  <span className="w-6 h-6 rounded-full bg-navy-900 text-white text-xs font-bold flex items-center justify-center">
                    {index + 1}
                  </span>
                  <h3 className="font-semibold text-navy-900 text-base">{stage.agent_name}</h3>
                </div>
                {getStageBadge(stage.status)}
              </div>

              <div className="text-xs text-slate-500 mb-3">
                Processing Duration:{' '}
                <span className="font-mono font-semibold text-slate-700">
                  {typeof stage.duration_ms === 'number' ? `${stage.duration_ms} ms` : '—'}
                </span>
              </div>

              {stage.error && (
                <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs mb-3">
                  {stage.error}
                </div>
              )}

              {stage.key_findings?.length > 0 && (
                <div className="space-y-1.5 mb-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Key Findings</p>
                  <ul className="space-y-1 text-xs text-slate-700">
                    {stage.key_findings.map((f, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-blue-600 font-bold">•</span>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {stage.output && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Structured JSON Output
                </p>
                <pre className="bg-slate-900 text-slate-100 rounded-lg p-3 text-[11px] overflow-x-auto max-h-48">
                  {JSON.stringify(stage.output, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Execution Logs */}
      {execution?.logs?.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <Terminal className="w-4 h-4 text-navy-900" />
            <h2 className="text-sm font-semibold text-navy-900">Orchestration Execution Trace</h2>
          </div>
          <div className="bg-slate-900 text-slate-200 rounded-lg p-4 font-mono text-xs space-y-1.5 max-h-56 overflow-y-auto">
            {execution.logs.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
