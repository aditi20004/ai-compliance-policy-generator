from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class IndustrySector(StrEnum):
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    EDUCATION = "education"
    RETAIL = "retail"
    TECHNOLOGY = "technology"
    LEGAL = "legal"
    GOVERNMENT = "government"
    MANUFACTURING = "manufacturing"
    PROFESSIONAL_SERVICES = "professional_services"
    INSURANCE = "insurance"
    REAL_ESTATE = "real_estate"
    NOT_FOR_PROFIT = "not_for_profit"
    CONSTRUCTION = "construction"
    MEDIA_ENTERTAINMENT = "media_entertainment"
    MINING_RESOURCES = "mining_resources"
    AGRICULTURE = "agriculture"
    TRANSPORT_LOGISTICS = "transport_logistics"
    OTHER = "other"


class TrainingFrequency(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    BIANNUALLY = "biannually"
    ANNUALLY = "annually"
    ON_CHANGE = "on_policy_change"
    NEVER = "never"


class RevenueRange(StrEnum):
    UNDER_3M = "under_3m"
    BETWEEN_3M_10M = "3m_to_10m"
    BETWEEN_10M_50M = "10m_to_50m"
    OVER_50M = "over_50m"


class DataRetentionPeriod(StrEnum):
    DAYS_30 = "30_days"
    DAYS_90 = "90_days"
    YEAR_1 = "1_year"
    YEARS_3 = "3_years"
    NO_DEFINED = "no_defined_period"


AI_TOOLS_OPTIONS = [
    "ChatGPT / OpenAI",
    "GitHub Copilot",
    "Microsoft Copilot (M365)",
    "Google Gemini",
    "Midjourney",
    "DALL-E",
    "Claude / Anthropic",
    "Perplexity AI",
    "DeepSeek",
    "Adobe Firefly",
    "Custom/Internal AI",
    "Local LLMs (Ollama, LM Studio)",
    "Other",
]

# Which of those tools process data overseas
AI_TOOLS_OVERSEAS = [
    "ChatGPT / OpenAI (US)",
    "GitHub Copilot (US)",
    "Google Gemini (US)",
    "Midjourney (US)",
    "DALL-E / OpenAI (US)",
    "Claude / Anthropic (US)",
    "Perplexity AI (US)",
    "DeepSeek (China)",
    "Adobe Firefly (US)",
    "None — all data stays in Australia",
]

DATA_TYPES_OPTIONS = [
    "Personal Information (names, emails, addresses)",
    "Financial Data (transactions, account numbers)",
    "Health Information",
    "Biometric Data",
    "Customer Data (purchase history, preferences)",
    "Employee Data (HR records, performance)",
    "Children's Data (under 18)",
    "Trade Secrets / IP",
    "Publicly Available Data",
    "AI-Inferred Data (profiles, predictions)",
]

AUTOMATED_DECISION_TYPES = [
    "Employment decisions (hiring, performance, termination)",
    "Credit or lending decisions",
    "Insurance underwriting or claims",
    "Customer service prioritisation",
    "Content moderation or filtering",
    "Pricing or discount decisions",
    "Fraud detection",
    "Other decisions affecting individuals",
]

QUESTIONS = [
    # Section 1: Organisation Profile
    {
        "id": 1,
        "section": "Organisation Profile",
        "field": "business_name",
        "question": "What is your business name?",
        "type": "text",
        "required": True,
    },
    {
        "id": 2,
        "section": "Organisation Profile",
        "field": "abn",
        "question": "What is your Australian Business Number (ABN)?",
        "type": "text",
        "required": False,
    },
    {
        "id": 3,
        "section": "Organisation Profile",
        "field": "industry",
        "question": "What industry sector does your business operate in?",
        "type": "select",
        "options": [e.value for e in IndustrySector],
        "required": True,
    },
    {
        "id": 4,
        "section": "Organisation Profile",
        "field": "employee_count",
        "question": "How many employees does your organisation have?",
        "type": "number",
        "required": True,
    },
    {
        "id": 5,
        "section": "Organisation Profile",
        "field": "annual_revenue",
        "question": "What is your approximate annual revenue range?",
        "type": "select",
        "options": [e.value for e in RevenueRange],
        "required": True,
        "help": "The Privacy Act currently applies to organisations with >$3M revenue, but this exemption is expected to be removed.",
    },
    # Section 2: AI Tool Usage
    {
        "id": 6,
        "section": "AI Tool Usage",
        "field": "ai_tools_in_use",
        "question": "Which AI tools does your organisation officially use or approve?",
        "type": "multi_select",
        "options": AI_TOOLS_OPTIONS,
        "required": False,
        "help": "Select none if your organisation has not yet adopted AI tools.",
    },
    {
        "id": 7,
        "section": "AI Tool Usage",
        "field": "ai_tools_overseas",
        "question": "Which of your AI tools process data in overseas data centres?",
        "type": "multi_select",
        "options": AI_TOOLS_OVERSEAS,
        "required": False,
        "help": "Under APP 8, cross-border disclosure of personal information makes your organisation vicariously liable for the overseas provider's data handling.",
    },
    {
        "id": 8,
        "section": "AI Tool Usage",
        "field": "shadow_ai_aware",
        "question": "Are you aware of employees using AI tools that haven't been approved by the organisation?",
        "type": "boolean",
        "required": True,
        "help": "Research shows 80% of SME employees use unapproved AI tools. This is called 'Shadow AI'.",
    },
    {
        "id": 9,
        "section": "AI Tool Usage",
        "field": "shadow_ai_controls",
        "question": "Do you have any technical or policy controls to detect or prevent unapproved AI tool usage?",
        "type": "boolean",
        "required": True,
    },
    {
        "id": 10,
        "section": "AI Tool Usage",
        "field": "customer_facing_ai",
        "question": "Does your organisation use AI to generate customer-facing content (marketing, product descriptions, chatbots, recommendations)?",
        "type": "boolean",
        "required": True,
        "help": "AI-generated customer content triggers Australian Consumer Law obligations (s18 misleading conduct, consumer guarantees).",
    },
    {
        "id": 11,
        "section": "AI Tool Usage",
        "field": "ai_generated_content_reviewed",
        "question": "Is all AI-generated customer-facing content reviewed by a human before publication?",
        "type": "boolean",
        "required": True,
    },
    {
        "id": 12,
        "section": "AI Tool Usage",
        "field": "ai_access_restricted",
        "question": "Is access to AI tools restricted by role (not all employees have access)?",
        "type": "boolean",
        "required": True,
        "help": "Role-based access reduces risk of sensitive data exposure through AI tools.",
    },
    {
        "id": 13,
        "section": "AI Tool Usage",
        "field": "ai_outputs_logged",
        "question": "Are AI prompts and outputs logged or recorded for audit purposes?",
        "type": "boolean",
        "required": True,
        "help": "Logging AI interactions supports incident investigation, compliance evidence, and quality assurance.",
    },
    # Section 3: Data & Automated Decisions
    {
        "id": 14,
        "section": "Data & Decisions",
        "field": "data_types_processed",
        "question": "What types of data does your organisation process using AI tools?",
        "type": "multi_select",
        "options": DATA_TYPES_OPTIONS,
        "required": True,
    },
    {
        "id": 30,
        "section": "Data & Decisions",
        "field": "ai_profiling_or_eligibility",
        "question": "Do you use AI for profiling individuals or making eligibility/access decisions (e.g., credit checks, insurance, hiring)?",
        "type": "boolean",
        "required": True,
        "help": "APPs 3.6 and 6.1 impose strict requirements on using personal information for profiling and eligibility decisions.",
    },
    {
        "id": 31,
        "section": "Data & Decisions",
        "field": "bias_testing_conducted",
        "question": "Have you assessed AI outputs for bias against protected attributes (age, gender, race, disability)?",
        "type": "boolean",
        "required": True,
        "help": "AI Ethics Principle 2 (Fairness) and anti-discrimination laws require testing for bias in AI-assisted decisions.",
    },
    {
        "id": 32,
        "section": "Data & Decisions",
        "field": "ai_copyright_assessed",
        "question": "Have you assessed copyright ownership of AI-generated content your organisation uses or publishes?",
        "type": "boolean",
        "required": True,
        "help": "Under the Copyright Act 1968, AI-generated works may not have copyright protection. Assess IP risks before relying on AI outputs.",
    },
    {
        "id": 33,
        "section": "Data & Decisions",
        "field": "ai_in_marketing",
        "question": "Do you use AI-generated content in marketing, advertising, or product descriptions?",
        "type": "boolean",
        "required": True,
        "help": "ACL s18 imposes strict liability for misleading or deceptive conduct — AI-generated marketing claims must be accurate.",
    },
    {
        "id": 34,
        "section": "Data & Decisions",
        "field": "human_review_available",
        "question": "Is there a process for individuals to request human review of AI-assisted decisions?",
        "type": "boolean",
        "required": True,
        "help": "AI Ethics Principle 7 (Contestability) requires that individuals can challenge AI decisions that affect them.",
    },
    {
        "id": 15,
        "section": "Data & Decisions",
        "field": "trades_in_personal_info",
        "question": "Does your business 'trade in' personal information (e.g., sell customer lists, data brokering, lead generation)?",
        "type": "boolean",
        "required": True,
        "help": "Businesses that trade in personal information are covered by the Privacy Act regardless of revenue.",
    },
    {
        "id": 16,
        "section": "Data & Decisions",
        "field": "has_data_retention_policy",
        "question": "Do you have a data retention and deletion policy for AI-processed data and outputs?",
        "type": "boolean",
        "required": True,
        "help": "APP 11 requires destruction or de-identification of personal information no longer needed.",
    },
    {
        "id": 17,
        "section": "Data & Decisions",
        "field": "consent_mechanism_exists",
        "question": "Do you have a mechanism to obtain consent before processing personal information through AI tools?",
        "type": "boolean",
        "required": True,
        "help": "APP 3 and APP 6 require consent for collection and use of personal information.",
    },
    {
        "id": 18,
        "section": "Data & Decisions",
        "field": "automated_decisions",
        "question": "Does your organisation use AI for automated or semi-automated decisions that affect individuals?",
        "type": "boolean",
        "required": True,
        "help": "Under the POLA Act 2024, you must disclose automated decisions in your privacy policy by December 2026.",
    },
    {
        "id": 19,
        "section": "Data & Decisions",
        "field": "automated_decision_types",
        "question": "What types of automated decisions does your organisation make using AI?",
        "type": "multi_select",
        "options": AUTOMATED_DECISION_TYPES,
        "required": False,
    },
    # Section 4: Vendor & Compliance Posture
    {
        "id": 20,
        "section": "Compliance Posture",
        "field": "vendor_dpa_in_place",
        "question": "Do you have Data Processing Agreements (DPAs) in place with your AI tool vendors?",
        "type": "boolean",
        "required": True,
        "help": "DPAs establish contractual obligations for how vendors handle your data — critical for APP 8 compliance.",
    },
    {
        "id": 35,
        "section": "Compliance Posture",
        "field": "vendor_audit_rights",
        "question": "Do your contracts with AI vendors include audit or inspection rights?",
        "type": "boolean",
        "required": True,
        "help": "Audit rights allow your organisation to verify vendor compliance with contractual and regulatory obligations.",
    },
    {
        "id": 36,
        "section": "Compliance Posture",
        "field": "ndb_ai_process",
        "question": "Do you have a process for notifying the OAIC within 72 hours if an AI system is involved in a data breach?",
        "type": "boolean",
        "required": True,
        "help": "The Notifiable Data Breaches (NDB) scheme requires notification to the OAIC within 30 days, but best practice is 72 hours.",
    },
    {
        "id": 37,
        "section": "Compliance Posture",
        "field": "ai_incident_register",
        "question": "Do you maintain a dedicated AI incident register (separate from general IT incidents)?",
        "type": "boolean",
        "required": True,
        "help": "AI-specific incidents (bias, hallucination, data leakage) require dedicated tracking for pattern analysis and regulatory response.",
    },
    {
        "id": 38,
        "section": "Compliance Posture",
        "field": "essential_eight_applied",
        "question": "Has your organisation applied the ACSC Essential Eight security controls to AI systems and tools?",
        "type": "boolean",
        "required": True,
        "help": "The ACSC Essential Eight (application control, patching, MFA, etc.) should extend to AI tools and ML libraries.",
    },
    {
        "id": 21,
        "section": "Compliance Posture",
        "field": "pia_conducted",
        "question": "Have you conducted a Privacy Impact Assessment (PIA) for any AI tool deployed in your organisation?",
        "type": "boolean",
        "required": True,
        "help": "The OAIC recommends PIAs before deploying any AI system that processes personal information.",
    },
    {
        "id": 22,
        "section": "Compliance Posture",
        "field": "has_privacy_policy",
        "question": "Does your organisation have a published privacy policy?",
        "type": "boolean",
        "required": True,
        "help": "APP 1 requires organisations to have a clearly expressed privacy policy. The POLA Act requires updating it for automated decisions.",
    },
    {
        "id": 23,
        "section": "Compliance Posture",
        "field": "existing_it_policies",
        "question": "Does your organisation have existing IT security or acceptable use policies?",
        "type": "boolean",
        "required": True,
    },
    {
        "id": 24,
        "section": "Compliance Posture",
        "field": "incident_response_tested",
        "question": "Has your organisation tested its incident response procedures (e.g., tabletop exercise) in the past 12 months?",
        "type": "boolean",
        "required": True,
    },
    # Section 5: Governance
    {
        "id": 25,
        "section": "Governance",
        "field": "board_ai_awareness",
        "question": "Has your board or senior leadership been briefed on AI risks and governance obligations?",
        "type": "boolean",
        "required": True,
        "help": "Directors have a duty of care under the Corporations Act to understand material risks including AI.",
    },
    {
        "id": 39,
        "section": "Governance",
        "field": "ai_disclosure_to_customers",
        "question": "Do customers know when they are interacting with AI (e.g., chatbots, AI-generated recommendations)?",
        "type": "boolean",
        "required": True,
        "help": "POLA Act s15 and AI Ethics Principle 4 (Transparency) require disclosure when AI is used in customer interactions.",
    },
    {
        "id": 40,
        "section": "Governance",
        "field": "ai_supply_chain_assessed",
        "question": "Have you assessed the AI supply chain (sub-processors, model providers, data sources) used by your AI vendors?",
        "type": "boolean",
        "required": True,
        "help": "Understanding your AI supply chain is critical for APP 8 compliance and managing third-party risk.",
    },
    {
        "id": 41,
        "section": "Governance",
        "field": "tranche2_aware",
        "question": "Is your organisation aware of the POLA Act Tranche 2 requirements for high-risk AI systems?",
        "type": "boolean",
        "required": True,
        "help": "Tranche 2 may introduce mandatory conformity assessments, high-risk AI registers, and additional transparency obligations.",
    },
    {
        "id": 42,
        "section": "Governance",
        "field": "data_overseas_mapped",
        "question": "Have you mapped which AI tools store or process data outside Australia?",
        "type": "boolean",
        "required": True,
        "help": "APP 8 requires you to know where personal information is being disclosed overseas and take reasonable steps to ensure compliance.",
    },
    {
        "id": 26,
        "section": "Governance",
        "field": "training_frequency",
        "question": "How frequently do staff receive training on data privacy and AI usage?",
        "type": "select",
        "options": [e.value for e in TrainingFrequency],
        "required": True,
        "help": "The OAIC recommends bi-annual staff training on AI and privacy.",
    },
    {
        "id": 27,
        "section": "Governance",
        "field": "ai_governance_contact",
        "question": "Who is the named person responsible for AI governance in your organisation?",
        "type": "text",
        "required": False,
        "help": "AI Ethics Principle 8 (Accountability) requires identifiable individuals responsible for AI outcomes.",
    },
    {
        "id": 28,
        "section": "Data & Decisions",
        "field": "data_retention_period",
        "question": "What is the defined data retention period for AI-processed personal information?",
        "type": "select",
        "options": [e.value for e in DataRetentionPeriod],
        "required": True,
        "help": "APP 11 requires destruction or de-identification of personal information no longer needed. Define a retention ceiling.",
    },
    {
        "id": 29,
        "section": "Compliance Posture",
        "field": "vendor_ai_clauses_reviewed",
        "question": "Have vendor contracts been reviewed for AI-specific clauses (model training opt-out, sub-processor lists)?",
        "type": "boolean",
        "required": True,
        "help": "AI vendors may train on your data unless you contractually opt out. Review contracts for model-training, sub-processor, and IP clauses.",
    },
]


class QuestionnaireResponse(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200)
    abn: str | None = None
    industry: IndustrySector
    employee_count: int = Field(..., gt=0)
    annual_revenue: RevenueRange = RevenueRange.UNDER_3M
    revenue_exceeds_threshold: bool = False

    # AI usage
    ai_tools_in_use: list[str] = Field(default_factory=list)
    ai_tools_overseas: list[str] = Field(default_factory=list)
    shadow_ai_aware: bool = False
    shadow_ai_controls: bool = False
    customer_facing_ai: bool = False
    ai_generated_content_reviewed: bool = False
    ai_access_restricted: bool = False
    ai_outputs_logged: bool = False

    # Automated decisions
    automated_decisions: bool = False
    automated_decision_types: list[str] = Field(default_factory=list)

    # Data
    data_types_processed: list[str] = Field(..., min_length=1)
    trades_in_personal_info: bool = False
    has_data_retention_policy: bool = False
    data_retention_period: DataRetentionPeriod = DataRetentionPeriod.NO_DEFINED
    consent_mechanism_exists: bool = False
    ai_profiling_or_eligibility: bool = False
    bias_testing_conducted: bool = False
    ai_copyright_assessed: bool = False
    ai_in_marketing: bool = False
    human_review_available: bool = False

    # Vendor/compliance
    vendor_dpa_in_place: bool = False
    pia_conducted: bool = False
    has_privacy_policy: bool = False
    vendor_ai_clauses_reviewed: bool = False
    vendor_audit_rights: bool = False
    ndb_ai_process: bool = False
    ai_incident_register: bool = False
    essential_eight_applied: bool = False

    # Governance
    existing_it_policies: bool = False
    incident_response_tested: bool = False
    training_frequency: TrainingFrequency = TrainingFrequency.ANNUALLY
    ai_governance_contact: str | None = None
    board_ai_awareness: bool = False
    ai_disclosure_to_customers: bool = False
    ai_supply_chain_assessed: bool = False
    tranche2_aware: bool = False
    data_overseas_mapped: bool = False

    @field_validator("abn")
    @classmethod
    def validate_abn(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        digits = v.replace(" ", "")
        if not digits.isdigit() or len(digits) != 11:
            raise ValueError("ABN must be 11 digits")
        # ABN checksum validation
        weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
        nums = [int(d) for d in digits]
        nums[0] -= 1  # subtract 1 from first digit
        checksum = sum(w * n for w, n in zip(weights, nums, strict=True))
        if checksum % 89 != 0:
            raise ValueError("Invalid ABN checksum")
        return digits

    def model_post_init(self, __context):
        self.revenue_exceeds_threshold = self.annual_revenue != RevenueRange.UNDER_3M

    def is_privacy_act_covered(self) -> bool:
        """Determine if organisation is covered by Privacy Act."""
        return self.revenue_exceeds_threshold or self.trades_in_personal_info or self.has_health_data()

    def has_health_data(self) -> bool:
        return "Health Information" in self.data_types_processed

    def has_sensitive_data(self) -> bool:
        sensitive = {
            "Health Information",
            "Biometric Data",
            "Financial Data (transactions, account numbers)",
            "Children's Data (under 18)",
            "AI-Inferred Data (profiles, predictions)",
        }
        return bool(sensitive & set(self.data_types_processed))

    def has_cross_border_risk(self) -> bool:
        return bool(self.ai_tools_overseas) and "None — all data stays in Australia" not in self.ai_tools_overseas

    def has_shadow_ai_risk(self) -> bool:
        return not self.shadow_ai_controls

    def has_acl_risk(self) -> bool:
        return self.customer_facing_ai and not self.ai_generated_content_reviewed


def get_questions() -> list[dict]:
    return QUESTIONS
