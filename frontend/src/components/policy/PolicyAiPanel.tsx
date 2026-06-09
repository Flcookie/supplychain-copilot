import { t } from "../../i18n";
import { useCopilot } from "../../context/CopilotContext";
import { ActionCell, DataTable, ListPanel } from "../shared/UiBits";

const QUICK_PROMPTS = [
  "What ESG documents are required for yarn suppliers from China?",
  "What is the process for C-rated suppliers?",
  "What monitoring applies to strategic yarn suppliers?",
];

export function PolicyAiPanel({
  onAsk,
  loading,
}: {
  onAsk: (q: string) => void;
  loading: boolean;
}) {
  const { lang } = useCopilot();
  const L = t(lang).policy;

  return (
    <section className="page-section">
      <div className="page-section-head">
        <h2 className="panel-title">{L.suggestedQuestions}</h2>
      </div>
      <ListPanel>
        <DataTable>
          <thead>
            <tr>
              <th>Question</th>
              <th className="col-actions">Action</th>
            </tr>
          </thead>
          <tbody>
            {QUICK_PROMPTS.map((q) => (
              <tr key={q}>
                <td style={{ color: "var(--ink-soft)" }}>{q}</td>
                <ActionCell>
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => onAsk(q)}
                    className="btn btn-sm btn-secondary"
                  >
                    {t(lang).copilot.askAi}
                  </button>
                </ActionCell>
              </tr>
            ))}
          </tbody>
        </DataTable>
      </ListPanel>
    </section>
  );
}
