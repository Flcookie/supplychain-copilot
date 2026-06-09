import { useState } from "react";
import { sendChat } from "../api/client";
import { useCopilot } from "../context/CopilotContext";
import { t } from "../i18n";
import { ButtonBar, DataTable, ListPanel, PageHeader, StepWizard } from "../components/shared/UiBits";

interface FormData {
  name: string;
  category: string;
  country: string;
}

const STEPS = [
  { id: 1, labelKey: "step1" as const },
  { id: 2, labelKey: "step2" as const },
  { id: 3, labelKey: "step3" as const },
];

export function QualificationPage() {
  const { lang, setOpen, setPageContext } = useCopilot();
  const L = t(lang).qualification;
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<FormData>({
    name: "",
    category: "Yarn",
    country: "China",
  });
  const [checklist, setChecklist] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [qualId] = useState("QUAL-2025-0042");

  const steps = STEPS.map((s) => ({ id: s.id, label: L[s.labelKey] }));

  const generateChecklist = async () => {
    setLoading(true);
    setPageContext((prev) => ({
      ...prev,
      page: "qualification",
      extraPrefix: `New supplier: ${form.name || "TBD"}, category ${form.category}, country ${form.country}`,
    }));
    const question = `We have a new ${form.category.toLowerCase()} supplier from ${form.country} named ${form.name || "TBD"}. What qualification process and required documents should we follow?`;
    try {
      const res = await sendChat({ question, language: lang });
      setChecklist(res.answer);
      setStep(2);
      setOpen(true);
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader title={L.title} />
      <StepWizard steps={steps} current={step} />

      {step === 1 && (
        <>
          <ListPanel>
            <DataTable>
              <tbody>
                <tr>
                  <td style={{ color: "var(--muted)", width: "10rem" }}>Supplier name</td>
                  <td>
                    <input
                      className="field"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      placeholder="Optional"
                    />
                  </td>
                </tr>
                <tr>
                  <td style={{ color: "var(--muted)" }}>Category</td>
                  <td>
                    <select
                      className="field"
                      value={form.category}
                      onChange={(e) => setForm({ ...form, category: e.target.value })}
                    >
                      {["Yarn", "Fabric", "Leather", "Manufacturing", "Services"].map(
                        (c) => (
                          <option key={c}>{c}</option>
                        ),
                      )}
                    </select>
                  </td>
                </tr>
                <tr>
                  <td style={{ color: "var(--muted)" }}>Country</td>
                  <td>
                    <input
                      className="field"
                      value={form.country}
                      onChange={(e) => setForm({ ...form, country: e.target.value })}
                    />
                  </td>
                </tr>
              </tbody>
            </DataTable>
          </ListPanel>
          <div className="mt-4">
            <ButtonBar>
              <button
                type="button"
                disabled={loading}
                onClick={() => void generateChecklist()}
                className="btn btn-primary"
              >
                {loading ? t(lang).common.loading : L.generate}
              </button>
            </ButtonBar>
          </div>
        </>
      )}

      {step === 2 && checklist && (
        <>
          <ListPanel className="panel-pad">
            <div
              className="whitespace-pre-wrap text-sm leading-relaxed"
              style={{ color: "var(--ink-soft)" }}
            >
              {checklist}
            </div>
          </ListPanel>
          <div className="mt-4">
            <ButtonBar>
              <button type="button" onClick={() => setStep(1)} className="btn btn-ghost">
                {L.back}
              </button>
              <button
                type="button"
                onClick={() => setOpen(true)}
                className="btn btn-secondary"
              >
                {t(lang).copilot.open}
              </button>
              <button type="button" onClick={() => setStep(3)} className="btn btn-primary">
                {L.next}
              </button>
            </ButtonBar>
          </div>
        </>
      )}

      {step === 3 && (
        <>
          <ListPanel>
            <DataTable>
              <tbody>
                <tr>
                  <td style={{ color: "var(--muted)", width: "10rem" }}>Qualification ID</td>
                  <td className="font-medium">{qualId}</td>
                </tr>
                <tr>
                  <td style={{ color: "var(--muted)" }}>Supplier</td>
                  <td>{form.name || "TBD"}</td>
                </tr>
                <tr>
                  <td style={{ color: "var(--muted)" }}>Category / Country</td>
                  <td>
                    {form.category} · {form.country}
                  </td>
                </tr>
                <tr>
                  <td style={{ color: "var(--muted)" }}>Valid until</td>
                  <td>2025-09-01</td>
                </tr>
              </tbody>
            </DataTable>
          </ListPanel>
          <div className="mt-4">
            <ButtonBar>
              <button type="button" onClick={() => setStep(2)} className="btn btn-ghost">
                {L.back}
              </button>
              <button
                type="button"
                onClick={() => alert("Simulated: reminder email sent")}
                className="btn btn-secondary"
              >
                {L.sendEmail}
              </button>
              <button
                type="button"
                onClick={() => alert("Export coming soon")}
                className="btn btn-secondary"
              >
                {L.exportPdf}
              </button>
            </ButtonBar>
          </div>
        </>
      )}
    </div>
  );
}
