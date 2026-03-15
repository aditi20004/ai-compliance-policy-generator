# APP 8: Cross-Border Disclosure and AI Data Sovereignty

## The Core Issue

When an Australian SME submits customer data as a prompt to ChatGPT, Claude, or Gemini, that data is typically processed and stored in US data centres. Under Australian Privacy Principle 8, this constitutes a **cross-border disclosure of personal information**.

## APP 8 Requirements

### Vicarious Liability (Section 16C)

The disclosing Australian entity must:
1. Take "reasonable steps" to ensure the overseas recipient doesn't breach the APPs
2. Remain **vicariously liable** for the overseas recipient's data handling
3. Accept liability even if a breach occurs entirely outside Australia

This means: if your AI vendor suffers a data breach overseas, YOUR organisation faces the penalties under Australian law.

### Practical Implications for AI Tool Usage

| AI Tool | Data Centre Location | APP 8 Risk |
|---------|---------------------|-----------|
| ChatGPT / OpenAI | United States | HIGH — no Australian data residency option for most tiers |
| Claude / Anthropic | United States | HIGH — similar to OpenAI |
| Microsoft Copilot (M365) | Australia (claimed) | MEDIUM — Microsoft announced in-country processing but "cannot guarantee data sovereignty" for all customers |
| Google Gemini | United States / Singapore | HIGH — no guaranteed Australian processing |
| DeepSeek | China | VERY HIGH — different legal framework, government access provisions |
| Local LLMs (Ollama) | On-premises | LOW — data stays on your infrastructure |

### US CLOUD Act

The **Australia-US CLOUD Act Agreement** (entered into force 31 January 2024) allows authorities in both countries to send production orders directly to communications service providers in the other's jurisdiction for serious crimes.

**Impact:** Any data held by a US-headquartered cloud provider — Microsoft, Google, Amazon, OpenAI — may be subject to US government access regardless of where it is physically stored.

### Whitelist Mechanism

The POLA Act 2024 introduced a "whitelist" mechanism allowing the Government to prescribe countries with substantially similar privacy protections.

**Status as of March 2026:** No countries have been whitelisted. The enabling regulations have not been made.

## Compliance Steps for SMEs

### Before Using an Overseas AI Tool

1. **Identify** where the AI tool processes and stores data
2. **Assess** whether the tool offers Australian data residency
3. **Review** the vendor's privacy policy and data processing terms
4. **Evaluate** whether a Data Processing Agreement (DPA) is in place
5. **Consider** whether anonymisation or pseudonymisation can reduce risk
6. **Document** the cross-border disclosure in your APP 1 privacy policy
7. **Obtain consent** if the disclosure is for a secondary purpose

### Data Minimisation Strategies

- Only send the minimum data necessary in AI prompts
- Remove personal identifiers before AI processing where possible
- Use synthetic data for testing and development
- Consider on-premises or Australian-hosted AI alternatives for sensitive data
- Implement data classification rules: no Restricted/Confidential data to overseas AI

### Contractual Protections

Even where available, contractual protections are difficult for SMEs to negotiate. At minimum, seek:
- Written confirmation of data processing locations
- Commitment to APP-equivalent data protections
- Breach notification obligations
- Data deletion commitments
- Sub-processor disclosure

### Australian-Hosted Alternatives

Where sensitive data is involved, consider:
- Microsoft Azure (Australian regions) with data residency guarantees
- Local LLMs (Ollama, LM Studio) for on-premises processing
- Australian cloud providers with AI capabilities
- Enterprise tiers of major AI tools that offer data residency options

## Data Sovereignty Investment Landscape

Over **A$100 billion** in data centre investments announced 2023–2025:
- OpenAI's A$7 billion NextDC partnership (December 2025)
- Microsoft: M365 Copilot processed in-country for Australian customers
- AWS, Google: expanding Australian regions

However, for most SME-tier AI subscriptions, **no data residency guarantees are available**.
