# Part 2: legal applicability of the current use case

Owner: Yani Wu. Primary sources checked November 22, 2026. Scope: a local synthetic Course Q&A assistant that drafts answers from public materials, flags staff-only questions and sends a selected answer only after review. It does not decide grades, admissions, accommodations, hiring or access to services. The conclusions below are scope assessments, not a certification for a future deployment.

## EU AI Act

Annex III's education categories include admission/access, assessment of learning outcomes, education-level placement and examination monitoring. Our public-information assistant does none of these; our inference is that the present intended purpose does not fall in those education high-risk categories. Being used in a course alone does not establish that category. A change to assessment or admissions requires a fresh classification and review of applicable obligations and dates. [European Commission, Annex III](https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3).

Transparency is a separate question. The Commission states Article 50 applies from August 2, 2026 and describes explicit notice for direct AI interaction and machine-readable marking obligations for generated content. Our code-added identity and human-contact paragraph supports notice in outgoing replies. It does not establish machine-readable marking or all provider/deployer compliance. Actual territorial reach, provider/deployer roles and the deployment interface must be assessed before release. [Commission transparency guidance](https://digital-strategy.ec.europa.eu/en/policies/guidelines-ai-transparency-obligations).

## Colorado

Use the current enacted SB26-189, which repeals and reenacts the earlier SB24-205 provisions. Its official summary concerns technology processing personal data that materially influences consequential decisions, including education and employment; developer documentation requirements begin January 1, 2027. It includes notice, correction and meaningful human review/reconsideration after adverse consequential outcomes. [Colorado General Assembly, enacted summary](https://www.leg.colorado.gov/bills/SB26-189).

Our inference: answering a public deadline question does not make such a consequential decision. If recommendations affect admission, grades or employment, reassess coverage and provide the required review process. The current approval button is a preventive send control; it is not an adverse-decision appeal mechanism. This assessment uses the enacted legislative summary rather than claiming an exhaustive review of every exemption or implementing rule.

## California

The adopted regulations define ADMT around replacing or substantially replacing human decisionmaking using personal information. Human involvement requires a reviewer who understands, actually analyzes and can change the decision. Article 11 addresses significant decisions. Section 7221(b)(1)'s qualified human appeal is a conditional alternative to opt-out, not a universal appeal requirement for every chatbot. [CPPA final regulations, §§7001, 7200, 7221](https://www.cppa.ca.gov/regulations/pdf/ccpa_updates_cyber_risk_admt_appr_text.pdf). The agency identifies January 1, 2027 as the ADMT compliance start. [CPPA adoption announcement](https://www.cppa.ca.gov/announcements/2025/20250923.html).

Our inference: the current public-information use case does not make significant decisions of this kind. A real deployment must also establish whether its entity and data processing are covered by the CCPA. Adding consequential student or employment decisions would require reassessment; nominal human approval alone does not prove meaningful human involvement. The disclosure line and TA contact are useful controls, not substitutes for statutory notice, access, opt-out or appeal procedures where applicable.
