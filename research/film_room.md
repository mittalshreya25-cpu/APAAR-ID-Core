# Film Room research brief — 2026-10-28

Participant brief for the existing council; no nested agents. Access date for every source: **2026-10-28**. Claims below await non-author source review. “Observed” describes my retrieval, not independent council approval. Search scope: official AICTE APH, 2026-27 amendments, government-hosted copies, APAAR and API Setu documentation; targeted official SIH searches.

## Claims

### FILM-1 — Approved intake excludes supernumerary seats

**Claim:** APH definition 10 defines approved intake per course excluding supernumerary seats. Therefore comparing all student rows to approved intake alone can misclassify permitted supernumerary admissions (last sentence is an engineering inference).

- Source: [AICTE Approval Process Handbook 2024-25 to 2026-27](https://www.aicte.gov.in/sites/default/files/APH%20Final.pdf), Definitions item 10, printed p. viii; PDF zero-based p.11. Publisher: AICTE. Publication: launch independently dated 2023-12-06 by [PIB](https://www.pib.gov.in/Pressreleaseshare.aspx?PRID=1983013&lang=2&reg=48); exact PDF revision date not confirmed.
- Short excerpt (shared APH quote budget): “excluding the Supernumerary Seats” (4 words).
- Observed: official PDF opened, 231 pages. Baseline fact supported; applicability still requires amendments and institution/course/year approval evidence.

### FILM-2 — Baseline NRI seats are within intake

**Claim:** Baseline APH §2.8(b) permits 5% NRI seats **within** approved intake; §2.8(a) requires application and nil deficiency. Under §2.8(d), unfilled NRI seats may go to general candidates on merit at regular fees. This is not an additional 5% capacity pool.

- Source: same [APH](https://www.aicte.gov.in/sites/default/files/APH%20Final.pdf), printed p.18, PDF zero-based p.33, §2.8(a), (b), (d).
- No additional verbatim excerpt.
- Observed: exact baseline text read. **Not certified as the complete 2026-27 rule:** I did not retrieve the full applicable amendment chain or establish that §2.8 is unchanged.

### FILM-3 — A 2026-27 amendment distinguishes programme and level

**Claim:** A government-hosted copy of AICTE’s *Addendum/Corrigendum 2026-27 of APH 2024-27*, item 21, modified §2.9 table, shows E&T diploma/UG 15%; E&T PG 25%; listed other programmes at all levels 25%, above approved intake per course. The listed programmes are Management, Computer Applications, Applied Arts and Crafts, Design, Planning, and Hotel Management and Catering Technology.

- Source: [Government of Rajasthan-hosted AICTE approval documents](https://hte.rajasthan.gov.in/Website/DepartmentOfCollegeEducation/CONTENTFILES/AICTE%20Approval.pdf), addendum printed p.6, item 21, **right-hand Modified Clauses column**, programme/level/percentage table; p.7 completes “Catering Technology”. Publisher of underlying document: AICTE; host: Rajasthan Department of College Education. Exact issuance/publication date unconfirmed (index says approximately six months before access; that is not an issuance date).
- Excerpt (shared addendum quote budget): “over and above the approved intake per course” (8 words).
- **Partial:** official-host search index returned the original two-column document text and printed page numbers, but repeated direct web opens timed out. Local Python urllib also failed DNS; no PDF downloaded. This copy does not prove completeness of the amendment chain or an individual institution’s approval. Do not load these as authoritative production caps without source retrieval, reconciliation and approval evidence.

### FILM-4 — Baseline vacant-seat NRI conversion conflicts with modified 2026-27 text

**Claim:** Baseline §2.9(d) allows remaining FN/OCI/CIWG seats after the last State/UT admission round to be filled with NRI seats conditionally. The 2026-27 item 21 modified §2.9(d) instead restricts unfilled international seats to international students, defined there by foreign passport. A demo must not present the older vacant-seat exception as a verified current rule.

- Sources: [baseline APH](https://www.aicte.gov.in/sites/default/files/APH%20Final.pdf), printed p.19 / PDF zero-based p.34, §2.9(d); [Rajasthan copy of addendum](https://hte.rajasthan.gov.in/Website/DepartmentOfCollegeEducation/CONTENTFILES/AICTE%20Approval.pdf), printed p.7, item 21, right-hand §2.9(d). Addendum date/access limitations as FILM-3.
- Excerpt: “one who shall possess a foreign passport” (8 words; addendum combined quotes 16 words).
- **Partial current applicability:** original modified clause is visible through official-host indexed text, but full amendment chain and source PDF remain unverified. Foreign-passport wording may affect CIWG/OCI classification; do not resolve that eligibility issue from a boolean category alone.

### FILM-5 — The baseline 10% rule is a specific lateral-entry provision

**Claim:** Baseline §6.13(a) applies a 10% supernumerary allowance plus specified first-year vacancies to second-year diploma/UG lateral entry, as applicable in Annexure 8. It is not a universal extra 10% admission allowance. Current amendment reconciliation remains necessary.

- Source: [APH](https://www.aicte.gov.in/sites/default/files/APH%20Final.pdf), printed pp.54–55 / PDF zero-based pp.69–70, §6.13(a); §6.13(f) also addresses first-year withdrawal vacancies. Date as FILM-1.
- No additional verbatim excerpt.
- Observed baseline. The APH-derived paraphrases across FILM-1, 2, 4 and 5 are kept compact; baseline facts must not be promoted to complete current law.

### FILM-6 — Twelve digits establishes format, not registry verification

**Claim:** APAAR’s official FAQ describes a unique 12-digit identity. Its creation/status workflow involves verification, authentication and DigiLocker/UDISE+ status. A 12-digit regex therefore establishes syntax only; it cannot establish that an ID exists, belongs to the submitted student, or authorizes record access (inference).

- Source: [APAAR FAQs](https://apaar.education.gov.in/faqs), questions 2, 3, 13 and 18. Publisher: Ministry of Education APAAR portal. Publication/update date not displayed.
- Excerpt: “a unique 12-digit code” (5 words).
- Observed official page content. Recommended prototype states: format-valid, mock-match, mock-not-found, unavailable; explicitly label mock outcomes. Those labels are design advice, not official API response codes.

### FILM-7 — API listings exist; prototype authorization is unconfirmed

**Claim:** API Setu lists an ABC collection including APAAR verification-related services. Listing does not grant access: official API Setu documentation says consumers register/subscribe and require publisher approval. No evidence establishes this student project’s eligibility, credentials, sandbox access, endpoint contract, quotas or approval timeline.

- Source A: [Academic Bank of Credits API collection](https://directory.apisetu.gov.in/api-collection/abc), sections “APAAR ID Verification by Partner for Student Concession API” and “Academic Bank of Credits (ABC) APIs”. Publisher/provider: DigiLocker/API Setu. Date not displayed. Indexed content exposed listings, but direct rendered open omitted them and index showed YAML fetch forbidden. Therefore listing observation is **partial**, not a tested API.
- Source B: [API Setu Overview](https://docs.apisetu.gov.in/document-central/explore-apisetu/Overview.html), §2 Consumer Registration & API Subscription, final sentence. Publisher: DIC/NeGD, MeitY. Date not displayed. Direct page opened successfully.
- Excerpt from B: “access granted only after the publisher’s approval” (8 words).
- Recommendation: continue the user-authorized mock adapter and document the interface; do not imply registry verification or integration approval.

### FILM-8 — Actual approvals require institution/course/year evidence

**Claim:** An observed 2026-27 AICTE EoA separately records approved intake, NRI approval status and international-student approval status per course. Thus handbook maxima alone are insufficient evidence that a particular institution can consume those capacities (inference).

- Primary artifact: [AICTE EoA for Government Residential Women Polytechnic College, Jodhpur](https://hte.rajasthan.gov.in/Website/GOVERNMENTRESIDENTIALWOMENPOLYTECHNICCOLLEGEJODHPUR/CONTENTFILES/f0c6c0d2-7cd5-47ed-9f81-68a353800cdc.pdf), application 1-46221905298, inside a **38-page composite PDF**. EoA begins at zero-based PDF p.4 (printed EoA Page 1 of 5); table continues at p.5 (printed Page 2 of 5), with separate intake, NRI approval and international-student approval columns. **Date of Approval: 2026-03-16; letter print date: 2026-03-25.** Corrected metadata from Empiricist's independent direct text retrieval; see review below.
- No verbatim excerpt beyond column labels above (14 words total).
- **Retrieval provenance:** Film Room initially saw indexed text only. Non-author Empiricist subsequently directly read the composite PDF text; screenshot retrieval timed out. Example is source-supported within that narrow scope, not a universal permission rule or this project’s target institution approvals.

## Material gaps and implications

- Cannot certify the complete regulatory position for 2026-27: AICTE homepage returned 403; guessed approval landing page inaccessible; Rajasthan amendment PDF direct opens timed out. Need original complete amendments, issue dates, later notices, applicable EoA, cohort/course/year and relevant State/UT admission rules before production enforcement. Rounding, CIWG eligibility under new foreign-passport wording and interaction with lateral entry remain open.
- Baseline §2.9 also requires course-specific continuation application and includes eligibility/approval conditions; a generic 15% number cannot replace approval evidence.
- Official SIH searches for “26263” and exact title returned no matching official result. Baseline transcript supplies the full ten-requirement text; parent independently observed screenshot PS ID 26263. Treat these as supplied problem-statement evidence, not independently recovered official web evidence. No SIH 2026 finale dates, team rules or pre-built-code permission confirmed.
- Local baseline report/zip were not inspected because not present in supplied files. Historical test counts, accuracy, throughput and implemented features remain claims from transcript only.
- Weakest load-bearing claim: **complete current capacity applicability**. It would be strengthened by a retrieved official amendment set plus institution-specific 2026-27 EoA and non-author clause review. Conservative project behavior: rule applicability unknown → review-required, never silently assume a cap or an exception.

## Cross-review request

Please independently inspect FILM-3/4 from the original PDF, particularly item 21 right column pp.6–7, and challenge whether later amendments alter it. Also inspect FILM-2’s within-intake distinction and FILM-7’s approval boundary. Do not mark current law verified solely because another brief agrees.

## Author response to non-author review — 2026-10-28

Read [Empiricist's review](review_film_room.md). Accept the FILM-8 metadata corrections: actual approval is 16 March 2026, while 25 March is the print date; the EoA is inside a 38-page compilation beginning at zero-based PDF p.4, with the continued table at p.5. Corrected the original claim above and attributed direct retrieval to the reviewer rather than claiming I inspected it.

Preserve FILM-3/4 as **partial/index-only** and complete current applicability as unresolved. The historical vacant-seat case D cannot be described as a verified correct 2026-27 warning; it needs a historical/provisional source label or an applicability-review-required outcome. The review independently reproduced excerpts but did not retrieve the original amendment PDF or full amendment chain.

Accept the APAAR scope qualification: FAQ school/UDISE+ steps are an observed creation workflow, not evidence that it is the only higher-education creation channel. FILM-6's format-versus-registry distinction and FILM-7's publisher-approval boundary stand. No production capacity cap or official API authorization is asserted by this response; reviewer retains final review authority.
