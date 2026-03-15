# Shadow AI: Risks and Governance for Australian SMEs

## The Scale of the Problem

Shadow AI refers to the use of AI tools that have not been approved, evaluated, or monitored by an organisation. Research consistently shows this is now the norm, not the exception.

### Key Statistics

- **80% of employees** at small and medium businesses use AI tools not approved by their employer (Microsoft/LinkedIn 2024 Work Trend Index)
- **50%** of employees use unauthorised AI tools, with **46% saying they would continue even if banned** (Software AG)
- **38%** of employees share confidential data with AI platforms without approval (CybSafe/National Cybersecurity Alliance)
- **77%** share sensitive or proprietary information with tools like ChatGPT (Proofpoint)
- **20%** of organisations experienced security breaches directly linked to Shadow AI in 2025 (IBM)
- Organisations with high Shadow AI face **$670,000 in additional breach costs** (IBM 2025 Cost of Data Breach Report)

### Why Shadow AI Is Existential for SMEs

The financial asymmetry makes this an existential risk:
- A $670,000 additional breach cost is survivable for a Fortune 500 company
- For an SME with $2–10 million revenue, it is potentially company-ending
- Only **37%** of organisations globally have policies to manage or detect Shadow AI
- Only **17%** have technical controls to prevent confidential data uploads to public AI tools
- SMEs typically have zero dedicated security staff monitoring for unauthorised tool use

## Regulatory Exposure from Shadow AI

### Privacy Act Breaches

Every prompt submitted to an external AI tool containing personal information constitutes:
- A potential **use or disclosure** under APP 6 beyond the primary purpose of collection
- A **cross-border disclosure** under APP 8 (most AI tools are US-hosted)
- A potential **notifiable data breach** under the NDB scheme if personal information is exposed

### OAIC Guidance on Shadow AI

The OAIC published specific guidance (October 2024) requiring organisations to:
1. Implement an internal AI audit and governance framework
2. Establish internal policies and procedures for AI product use
3. Conduct Privacy Impact Assessments before deploying AI
4. Refrain from entering personal information into publicly available AI tools
5. Use enterprise licences with managed privacy settings
6. Schedule bi-annual staff training

The OAIC's blog used a fictional case study ("CarCover") depicting a **notifiable data breach** caused by an employee uploading sensitive information into ChatGPT — a scenario occurring daily across thousands of Australian SMEs.

### Victorian Position

Victoria's Office of the Victorian Information Commissioner has taken the most explicit position, stating that Victorian Public Service staff "must not" enter personal information into publicly available GenAI tools.

## Shadow AI Governance Framework for SMEs

### Detection

Without enterprise CASB, DLP, or SIEM, SMEs should:
1. Conduct anonymous staff surveys about AI tool usage
2. Review browser extension lists across company devices
3. Check network DNS logs for known AI service domains
4. Review expense reports for AI tool subscriptions
5. Monitor for local LLM installations (Ollama, LM Studio)

### AI Service Domains to Monitor

| Provider | Domains |
|----------|---------|
| OpenAI | api.openai.com, chat.openai.com, chatgpt.com |
| Anthropic | api.anthropic.com, claude.ai |
| Google | gemini.google.com, aistudio.google.com |
| Microsoft | copilot.microsoft.com |
| Others | perplexity.ai, deepseek.com, huggingface.co |
| Local | localhost:11434 (Ollama), localhost:1234 (LM Studio) |

### Response Procedures

When Shadow AI is discovered:
1. **Do not immediately block** — understand the business need driving adoption
2. **Assess data exposure** — what information has been shared? Is it personal information?
3. **Conduct breach assessment** — is this a notifiable data breach under the NDB scheme?
4. **Evaluate the tool** — can it be approved with appropriate controls?
5. **Provide approved alternatives** — enterprise versions with data protections
6. **Update policies** — ensure clear rules exist for AI tool usage
7. **Train staff** — explain why unapproved AI tools create compliance risk

### Policy Requirements

An effective Shadow AI policy must:
- Define what constitutes an "approved" vs "unapproved" AI tool
- List currently approved tools and their permitted use cases
- Specify what data classifications can be used with each tool tier
- Establish a process for requesting approval of new AI tools
- Define consequences for policy violations (proportionate, not punitive)
- Require transparency — staff should feel safe reporting Shadow AI use
