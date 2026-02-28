# Aigis Gold-Standard Checklist — Change Log

## v1.0 — 2026-02-27 (Initial)
- 13 categories, 80 checklist items
- NTH/GTH tiers per 4 deal types (producing_asset, exploration, development, corporate)
- Jurisdiction-specific items: GoM, UKCS, Norway
- Initial keyword libraries and pre-written DRL request text per item

## 2026-02-27 11:34 UTC — v1.0 → v1.1
Accepted 5 proposal(s):
- **Shareholder loan agreements and intercompany financing arrangements** → category: `financial`, tier: `need_to_have`, from deal: `00000000-0000-0000-0000-c005a1000002` | Shareholder loans are critical for understanding the capital structure, related party transactions, and potential liabilities that transfer with the asset or entity
- **Third-party debt facilities and credit agreements** → category: `financial`, tier: `need_to_have`, from deal: `00000000-0000-0000-0000-c005a1000002` | External debt facilities are essential for understanding leverage, covenants, change of control provisions, and financing obligations that may impact or transfer with the transaction
- **Performance bonds and escrow security arrangements** → category: `legal`, tier: `need_to_have`, from deal: `00000000-0000-0000-0000-c005a1000002` | Bonds and escrow arrangements are critical legal obligations that secure regulatory compliance and operational performance, directly impacting asset transferability and ongoing obligations
- **Office lease agreements and real estate contracts** → category: `contracts`, tier: `good_to_have`, from deal: `00000000-0000-0000-0000-c005a1000002` | Office leases represent ongoing operational commitments and costs that are relevant for corporate acquisitions to understand overhead obligations and potential assignment requirements
- **Employee benefit plan agreements and retirement plans** → category: `hr_key_person`, tier: `good_to_have`, from deal: `00000000-0000-0000-0000-c005a1000002` | 401k and benefit plan agreements are important for corporate deals to understand employee obligations, fiduciary responsibilities, and transition requirements for benefit programs

## 2026-02-27 11:55 UTC — v1.1 → v1.2
Accepted 2 proposal(s):
- **Facility P&IDs and mechanical drawings** → category: `technical`, tier: `good_to_have`, from deal: `b4b71f51-0c39-47a8-b6dc-d1639702357d` | Process and instrumentation diagrams are critical technical documents for understanding facility operations, maintenance requirements, and operational risks. Essential for technical due diligence on producing assets with processing facilities.
- **Facility photographs and visual documentation** → category: `technical`, tier: `good_to_have`, from deal: `b4b71f51-0c39-47a8-b6dc-d1639702357d` | Visual documentation of facilities provides valuable context for asset condition assessment and helps validate technical reports, though not absolutely critical if detailed inspection reports are available.

## 2026-02-27 — v1.2 Calibration Fixes (manual, triggered by Project Coulomb false flags)
- **`legal_002` PSC/Concession Agreement**: Restricted jurisdictions from `[International, GoM]` to `[International]` only. GoM assets use federal OCS leases (BOEM), not PSCs — this item was generating a false NTH gap on all GoM deals.
- **`cont_002` Saltwater Disposal (SWD)**: Downgraded `producing_asset` tier from `need_to_have` to `good_to_have`. Updated notes to clarify onshore/shallow-water only — not applicable to deepwater/platform-hosted production where produced water is re-injected or disposed offshore.
- **`fina_001` Shareholder loan agreements**: Downgraded `producing_asset` tier from `need_to_have` to `good_to_have`. For asset sales (vs corporate acquisitions) shareholder-level debt is typically not transferred with the asset and will not appear in a producing asset VDR.
- **`fina_002` Third-party debt facilities**: Same rationale as `fina_001` — `producing_asset` tier downgraded from `need_to_have` to `good_to_have`.
