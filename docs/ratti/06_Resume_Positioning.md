# Resume Positioning｜Supplier Lifecycle Copilot

## Suggested project title
企业供应商管理 AI Copilot｜基于 Ratti 校企项目的 RAG + NL2SQL 工作流｜独立完成

## Recommended bullets
- 基于 Politecnico di Milano × Ratti S.p.A. 校企项目中对供应商准入、品类分层、ESG 评估与 vendor rating 流程的观察，识别制造业采购团队在供应商信息分散、准入流程手工、KPI 查询低效和风险结果不可解释等痛点，设计面向 buyer 的 Supplier Lifecycle Copilot 原型。
- 围绕 Ratti 的 procurement category tree、qualification status、Kraljic classification、ESG scoring、采购订单、交付记录和质量异常，构建脱敏/模拟数据集与数据字典，支持供应商准入清单生成、KPI 查询、风险分析和 vendor rating explanation 四类核心场景。
- 基于 LangGraph 构建 Router + Qualification Assistant + Policy QA + KPI Query + Risk Scenario Analysis 多节点工作流；采用 RAG 处理供应商政策、ESG 文件和 qualification 规则，采用 NL2SQL 查询供应商 KPI 与采购记录，实现自然语言到采购决策支持的闭环。
- 设计 intent、confidence、ambiguity_type 等结构化路由字段，结合澄清追问、低置信兜底、只读 SQL、字段白名单、SQL 回显、数据范围说明和文档引用机制，提高企业采购场景下 AI 输出的可解释性和可信度。
- 完成 Streamlit Demo 与 25 条采购问题评测集，覆盖新供应商准入、供应商 KPI 查询、战略供应商 review、风险情景推演等任务；通过 LangSmith trace 迭代路由规则和 few-shot 示例，将模拟评测集路由准确率由约 65% 提升至 90%+。

## Interview explanation
This was not a formal internship at Ratti. It was an AI product prototype independently extended from a Politecnico di Milano × Ratti industry project. The real elements are the business process, category logic, qualification framework and evaluation dimensions. Supplier-level records and PO data were anonymized/simulated for prototype validation.
