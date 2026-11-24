import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileText, X, AlertCircle, Play } from 'lucide-react';
import { claimsService } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function ClaimSubmissionPage() {
  const navigate = useNavigate();
  const { preferDemoMode } = useAuth();

  const [form, setForm] = useState({
    policyholder_name: 'Rahul Sharma',
    policyholder_email: 'rahul.sharma@example.com',
    policyholder_phone: '+91-98220-11234',
    policy_number: 'MTR-2026-001',
    vehicle_number: 'MH28AB1234',
    vehicle_model: 'Hyundai i20',
    accident_date: '2026-11-23',
    accident_time: '11:30',
    accident_location: 'Amravati Bypass Road',
    claimed_amount: '48500',
    estimated_damage_amount: '48500',
    damage_description: 'Front bumper impact, left headlamp housing fracture, and grille misalignment.',
  });

  const [supportingFiles, setSupportingFiles] = useState([]);
  const [policyFiles, setPolicyFiles] = useState([]);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/webp'];

  const handleFileSelection = (e, setter) => {
    const selected = Array.from(e.target.files || []);
    const valid = [];
    for (const file of selected) {
      if (!allowedTypes.includes(file.type)) {
        setError(`Unsupported file format: ${file.name}. Upload PDF, PNG, JPG, or WEBP only.`);
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setError(`File ${file.name} exceeds the 10MB limit.`);
        return;
      }
      valid.push(file);
    }
    setError('');
    setter((prev) => [...prev, ...valid]);
  };

  const removeFile = (idx, setter) => {
    setter((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!form.policyholder_name || !form.policy_number || !form.vehicle_number || !form.accident_date) {
      setError('Please complete all required policyholder, policy, vehicle, and incident fields.');
      return;
    }
    if (Number(form.claimed_amount) <= 0) {
      setError('Claimed amount must be greater than INR 0.');
      return;
    }

    setSubmitting(true);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => fd.append(k, v));
      supportingFiles.forEach((f) => fd.append('supporting_documents', f));
      policyFiles.forEach((pf) => fd.append('policy_documents', pf));

      const createRes = await claimsService.create(fd);
      const claimId = createRes.data.claim.claim_id;

      // Immediately start LangGraph Multi-Agent Processing
      await claimsService.process(claimId, preferDemoMode);
      navigate(`/processing?claimId=${claimId}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit claim for multi-agent processing.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-navy-900">Motor Insurance Claim Intake</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Submit First Notice of Loss (FNOL) details and supporting repair invoices or policy PDFs for multi-agent verification.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Claimant & Policy Info */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-navy-900 border-b border-slate-100 pb-3">
            1. Policyholder & Policy Identification
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Policyholder Full Name *</label>
              <input
                name="policyholder_name"
                value={form.policyholder_name}
                onChange={handleChange}
                required
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Policy Number *</label>
              <input
                name="policy_number"
                value={form.policy_number}
                onChange={handleChange}
                required
                placeholder="e.g., MTR-2026-001"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Contact Email</label>
              <input
                type="email"
                name="policyholder_email"
                value={form.policyholder_email}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Contact Phone</label>
              <input
                name="policyholder_phone"
                value={form.policyholder_phone}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm"
              />
            </div>
          </div>
        </div>

        {/* Vehicle & Accident Details */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-navy-900 border-b border-slate-100 pb-3">
            2. Vehicle & Incident Details
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Vehicle Registration *</label>
              <input
                name="vehicle_number"
                value={form.vehicle_number}
                onChange={handleChange}
                required
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm font-mono uppercase"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Vehicle Make & Model *</label>
              <input
                name="vehicle_model"
                value={form.vehicle_model}
                onChange={handleChange}
                required
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Accident Date *</label>
              <input
                type="date"
                name="accident_date"
                value={form.accident_date}
                onChange={handleChange}
                required
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Accident Time</label>
              <input
                type="time"
                name="accident_time"
                value={form.accident_time}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Accident Location *</label>
              <input
                name="accident_location"
                value={form.accident_location}
                onChange={handleChange}
                required
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Claimed Amount (INR) *</label>
              <input
                type="number"
                name="claimed_amount"
                value={form.claimed_amount}
                onChange={handleChange}
                required
                min="1"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm font-semibold"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Damage Description *</label>
            <textarea
              name="damage_description"
              value={form.damage_description}
              onChange={handleChange}
              rows={3}
              required
              className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm"
            />
          </div>
        </div>

        {/* Document Uploads */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-5">
          <h2 className="text-base font-semibold text-navy-900 border-b border-slate-100 pb-3">
            3. Supporting Documents & Policy PDFs
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-2">
                Supporting Claim Documents (Repair Estimate, Invoice, RC, DL, FIR)
              </label>
              <label className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl p-5 cursor-pointer bg-slate-50/60 transition-colors">
                <UploadCloud className="w-7 h-7 text-blue-600 mb-2" />
                <span className="text-xs font-medium text-slate-700">Click to attach PDF or Image files</span>
                <span className="text-[11px] text-slate-400 mt-1">PDF, PNG, JPG, WEBP up to 10MB</span>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.png,.jpg,.jpeg,.webp"
                  onChange={(e) => handleFileSelection(e, setSupportingFiles)}
                  className="hidden"
                />
              </label>
              {supportingFiles.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {supportingFiles.map((f, idx) => (
                    <li
                      key={idx}
                      className="flex items-center justify-between text-xs bg-slate-100 px-3 py-2 rounded-lg"
                    >
                      <span className="flex items-center gap-2 truncate">
                        <FileText className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                        <span className="truncate">{f.name}</span>
                        <span className="text-slate-400">({(f.size / 1024).toFixed(0)} KB)</span>
                      </span>
                      <button type="button" onClick={() => removeFile(idx, setSupportingFiles)}>
                        <X className="w-3.5 h-3.5 text-slate-500 hover:text-red-600" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-2">
                Policy Schedule PDF (Optional override / reference)
              </label>
              <label className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl p-5 cursor-pointer bg-slate-50/60 transition-colors">
                <UploadCloud className="w-7 h-7 text-navy-800 mb-2" />
                <span className="text-xs font-medium text-slate-700">Click to attach Policy PDF</span>
                <span className="text-[11px] text-slate-400 mt-1">PDF up to 10MB</span>
                <input
                  type="file"
                  multiple
                  accept=".pdf"
                  onChange={(e) => handleFileSelection(e, setPolicyFiles)}
                  className="hidden"
                />
              </label>
              {policyFiles.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {policyFiles.map((f, idx) => (
                    <li
                      key={idx}
                      className="flex items-center justify-between text-xs bg-slate-100 px-3 py-2 rounded-lg"
                    >
                      <span className="flex items-center gap-2 truncate">
                        <FileText className="w-3.5 h-3.5 text-navy-800 shrink-0" />
                        <span className="truncate">{f.name}</span>
                      </span>
                      <button type="button" onClick={() => removeFile(idx, setPolicyFiles)}>
                        <X className="w-3.5 h-3.5 text-slate-500 hover:text-red-600" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-2 px-6 py-3 bg-navy-900 hover:bg-navy-800 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors disabled:opacity-60"
          >
            <Play className="w-4 h-4" />
            <span>{submitting ? 'Submitting & Initializing Agents...' : 'Submit Claim & Run Multi-Agent Pipeline'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
