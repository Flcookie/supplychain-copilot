import { useState } from "react";
import { sendChat } from "../api/client";
import { useCopilot } from "../context/CopilotContext";
import { t } from "../i18n";
import {
  AiPrimaryButton,
  NextStepBanner,
  StepWizard,
} from "../components/shared/UiBits";

interface FormData {
  name: string;
  category: string;
  country: string;
  size: string;
  firstTime: boolean;
}

const STEPS = [
  { id: 1, labelKey: "step1" as const },
  { id: 2, labelKey: "step2" as const },
  { id: 3, labelKey: "step3" as const },
];

export function QualificationPage() {
  const { lang, setOpen, setPageContext, openWithQuestion } = useCopilot();
  const L = t(lang).qualification;
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<FormData>({
    name: "",
    category: "Yarn",
    country: "China",
    size: "Medium",
    firstTime: true,
  });
  const [checklist, setChecklist] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [qualId] = useState("QUAL-2025-0042");

  const steps = STEPS.map((s) => ({ id: s.id, label: L[s.labelKey] }));

  const generateChecklist = async () => {
    setLoading(true);
    setPageContext({
      page: "qualification",
      extraPrefix: `New supplier: ${form.name}, category ${form.category}, country ${form.country}`,
    });
    const question = `We have a new ${form.category.toLowerCase()} supplier from ${form.country} named ${form.name || "TBD"}. What qualification process and required documents should we follow?`;
    try {
      const res = await sendChat({ question, language: lang });
      setChecklist(res.answer);
      setStep(2);
      setOpen(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-[#1e3a5f]">{L.title}</h1>
      <StepWizard steps={steps} current={step} />

      {step === 1 && (
        <>
          <p className="text-sm text-slate-600">{L.step1Hint}</p>
          <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-6">
            <h2 className="font-semibold">{L.step1}</h2>
            <label className="block text-sm">
              Supplier name
              <input
                className="mt-1 w-full rounded border px-3 py-2"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </label>
            <label className="block text-sm">
              Category
              <select
                className="mt-1 w-full rounded border px-3 py-2"
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              >
                {["Yarn", "Fabric", "Leather", "Manufacturing", "Services"].map(
                  (c) => (
                    <option key={c}>{c}</option>
                  ),
                )}
              </select>
            </label>
            <label className="block text-sm">
              Country
              <input
                className="mt-1 w-full rounded border px-3 py-2"
                value={form.country}
                onChange={(e) => setForm({ ...form, country: e.target.value })}
              />
            </label>
            <AiPrimaryButton
              label={L.generate}
              sublabel={L.nextAfterStep1}
              disabled={loading}
              onClick={() => void generateChecklist()}
            />
          </div>
        </>
      )}

      {step === 2 && checklist && (
        <>
          <NextStepBanner
            title={L.step2}
            description={L.step2Hint}
            actionLabel={L.next}
            onAction={() => setStep(3)}
          />
          <div className="space-y-4 rounded-xl border-2 border-[#553c9a]/30 bg-white p-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-semibold">{L.step2}</h2>
              <AiPrimaryButton
                label={t(lang).copilot.open}
                sublabel="Clarify any checklist item"
                onClick={() =>
                  openWithQuestion(
                    `Explain the qualification checklist for ${form.name || "new supplier"} (${form.category}, ${form.country})`,
                  )
                }
              />
            </div>
            <div className="whitespace-pre-wrap rounded-lg bg-purple-50 p-4 text-sm ring-1 ring-purple-200">
              {checklist}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="rounded border px-4 py-2 text-sm"
              >
                {L.back}
              </button>
              <button
                type="button"
                onClick={() => setStep(3)}
                className="rounded-lg bg-[#1e3a5f] px-4 py-2 text-white"
              >
                {L.next}
              </button>
            </div>
          </div>
        </>
      )}

      {step === 3 && (
        <>
          <p className="text-sm text-slate-600">{L.step3Hint}</p>
          <div className="space-y-4 rounded-xl border border-green-200 bg-green-50/50 p-6">
            <h2 className="font-semibold text-green-900">{L.step3}</h2>
            <p className="text-sm">✅ Checklist saved</p>
            <p className="text-sm">
              📋 Qualification ID: <strong>{qualId}</strong>
            </p>
            <p className="text-sm">📅 Valid until: 2025-09-01</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => alert("Simulated: reminder email sent")}
                className="rounded border bg-white px-3 py-2 text-sm"
              >
                {L.sendEmail}
              </button>
              <button
                type="button"
                onClick={() => alert("Export coming soon")}
                className="rounded border bg-white px-3 py-2 text-sm"
              >
                {L.exportPdf}
              </button>
            </div>
            <NextStepBanner
              title="All set"
              description="Track this supplier in the list or start another qualification."
              actionLabel="View suppliers"
              to="/suppliers"
            />
          </div>
        </>
      )}
    </div>
  );
}
