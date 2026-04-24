# wfd-os Architecture Landscape

*Date: April 19, 2026*
*Owner: Ritu Bahl*
*Status: Living document — update as the architecture evolves*

This document captures the architectural landscape of wfd-os, the commercial
SaaS platform owned by Waifinder. It covers the three-component structure,
the modules within each component, the customer segments each serves, and
the design discipline that governs how the platform evolves.

The document serves three audiences:

- **Ritu** — reference for strategic and product decisions
- **Gary and future engineering contributors** — shared mental model for where features belong
- **Future external parties** (CFA board, potential partners, potential investors, eventual Waifinder team members) — understanding of what the platform is and how it's organized

---

## Part 1 — Platform Overview

### What wfd-os is

wfd-os is Waifinder's commercial software platform for workforce development.
It's architected as an agentic system — FastAPI microservices, Claude-driven
reasoning, AI-native design patterns — rather than a traditional three-tier
web application.

The platform serves multiple customer segments in the workforce development
sector. It is modular: customers can license specific components and modules
rather than the full platform, based on what their organization needs.

### History and current state

wfd-os is an agentic rewrite of an earlier React-based platform that ran at
watechcoalition.org. The earlier platform (referred to as "wtc" in this
document) was a traditional three-tier web app hosted on Azure. Ritu
rewrote the system using Claude Code during a focused build sprint in
Las Vegas, April 1-5, 2026. The rewrite is wfd-os.

After Las Vegas, the wfd-os codebase was pushed to the
Building-With-Agents GitHub organization (specific repository name
pending verification).

The original React platform (wtc) is on a sunset track but remains active
for two reasons:

1. It currently serves as the training codebase for Building-With-Agents
   Cohort 1 (Waifinder's apprenticeship program). The cohort will
   transition to wfd-os when wfd-os is stable enough to host their
   training work.

2. Gary and Cohort 1 have built substantial infrastructure on wtc — most
   notably the Job Intelligence Engine (JIE, currently in
   Building-With-Agents/job-intelligence-engine) and curriculum/delivery
   tooling for the apprenticeship program. This work must be ported to
   wfd-os before wtc can fully sunset.

Full sunset of wtc depends on both wfd-os stability and completion of
the JIE + curriculum port.

### Ownership and commercial structure

**Platform ownership:** Waifinder owns wfd-os outright. All components,
all modules, all intellectual property belong to Waifinder.

**Data ownership:** Customer data belongs to the customer. Waifinder is
the custodian of customer data under defined terms, but the data itself
(student records, financial records, operational records) is owned by
the customer organization using the platform.

**Customer relationship model:** SaaS. Customers license access to
specific components and modules. Pricing, terms, and contracts are
standard commercial SaaS arrangements.

**CFA-specific considerations:** CFA is a prospective customer of
Waifinder. Ritu is Executive Director of CFA and 50% owner of Waifinder.
Ritu recuses from all CFA decisions regarding Waifinder products,
including the decision of whether CFA licenses wfd-os and on what terms.
The CFA board evaluates any Waifinder-CFA commercial arrangement on its
merits with Ritu recused. Related-party transaction disclosure on Form
990 Schedule L applies. Federal grant compliance requirements apply if
any grant funds are used.

---

## Part 2 — The Three Components

wfd-os is organized into three top-level components. Each component
serves a distinct set of customer use cases and has a clear center of
gravity.

### Component 1: Youth

**Purpose:** Infrastructure for K-12 computer science and technology
education programs.

**Primary customer:** CFA (Computing for All), for whom youth
programming is the original and core mission.

**Secondary customers:** Other 501(c)(3) youth technology education
nonprofits, K-12 school districts running tech curriculum, after-school
program providers.

**Current scope in wfd-os:** Sparse. A marketing surface exists (/youth
page) but substantive functionality is minimal. This component reflects
a real need (CFA's core mission) but hasn't been built out because most
attention has gone to Coalition/Workforce and Consulting.

**Strategic status:** Intentionally under-invested today. Will require
deliberate product thinking and build work when CFA's youth program needs
grow beyond current marketing-surface capabilities.

### Component 2: Coalition / Workforce

**Purpose:** End-to-end infrastructure for adult workforce development —
sourcing candidates, assessing skills, identifying gaps, enabling
upskilling, matching to jobs, managing placement, reporting on outcomes.

**Primary customer (initially):** CFA's Coalition program (Washington
Technology Workforce Coalition), currently backboned by CFA under the
K8341 federal grant.

**Secondary customers:** Other workforce development nonprofits
(especially those with federal or state grant funding), community
colleges, bootcamps, state workforce agencies, corporate L&D
departments with internal mobility programs.

**Current scope in wfd-os:** The densest component. Most of what's
been built in the platform lives here. Rich data model (students table,
skills, work experience, gap analyses), multiple functional modules
(see Part 3), active development (Phases 1-2G of the Finance and
Recruiting modules have shipped to local-dev this month).

**Strategic status:** The flagship component. The primary commercial
surface area. Likely where Waifinder's first meaningful revenue comes
from.

### Component 3: Consulting

**Purpose:** Infrastructure for operating a professional services
consulting business — managing inbound inquiries, structuring
engagements, delivering client work, managing the consulting workforce
(including apprentices), and handling business development.

**Primary customer:** Waifinder itself, which operates a commercial AI
consulting business using this infrastructure internally.

**Secondary customers:** Other consulting businesses, particularly those
that combine client work with apprenticeship/training programs (tech
bootcamps that do cohort-based consulting, workforce development
nonprofits that run earned-revenue consulting arms, etc.).

**Current scope in wfd-os:** Partially built. Consulting funnel,
pipeline management, client portal, and BD/marketing modules were
started during the Vegas build sprint. Apprentice-specific modules
(workforce management, curriculum delivery) are largely still in wtc
and need to be ported as part of the wtc sunset.

**Strategic status:** Waifinder-facing. The consulting component serves
Waifinder's own business operations first. Commercial sale to other
consulting businesses is a secondary opportunity.

**Important structural note:** The apprenticeship program belongs under
Consulting, not as its own separate component. Apprentices are
Waifinder's consulting workforce doing real client work for real wages.
The training happens in the context of and in service of the work. The
apprenticeship is a real job, not a training program separate from
commercial activity.

---

## Part 3 — Modules Within Each Component

For each component, we catalog the modules — the sub-units of
functionality that can be independently licensed or enabled/disabled.
Each module has a status reflecting its current state in wfd-os.

Status key:
- **Built** — functional in wfd-os, being actively used or ready to use
- **In progress** — actively under development in wfd-os
- **Planned** — committed to build, not yet started
- **Designed** — architectural concept articulated, deferred from build
- **Unbuilt** — recognized need but no specific design or plan yet

### Youth Component — Modules

**Youth program marketing surface** — Public-facing pages describing
CFA's (or another customer's) youth programming. Landing page,
program descriptions, enrollment inquiry forms.
*Status: Built (minimal — /youth marketing page only)*

**Youth participant management** — Infrastructure for tracking kids in
programs: registration, parent/guardian info, program enrollment,
attendance, progress tracking, certification issuance.
*Status: Unbuilt*

**Youth curriculum delivery** — Tools for running K-12 tech education
programs: lesson plans, exercises, instructor dashboards, student
portfolios.
*Status: Unbuilt*

**Youth-family communication** — Transactional email/SMS to parents
about their children's programs, schedules, achievements.
*Status: Unbuilt*

**Youth funding and sponsorship** — Infrastructure for donor-funded
youth programs: grant tracking, sponsor engagement, program outcome
reporting to funders.
*Status: Unbuilt*

### Coalition / Workforce Component — Modules

**Student profile** — The foundational data model and interfaces for
student information: identity, contact, skills, work experience,
education, career objectives, preferences. Resume parsing pipeline.
Profile completeness scoring.
*Status: Built (from Vegas work, based on earlier React platform)*

**Job matching & gap analysis** — Matching students to jobs using
embedding-based similarity (Phase 2D cosine matching in pgvector) plus
gap analysis showing what skills a student has vs. needs for a target
role. Recommendations for closing gaps.
*Status: Built (Phase 2D shipped April 2026; gap_analyses table
populated)*

**Match narratives** — Claude-generated recruiter notes explaining why
a particular student is (or isn't) a good match for a particular job.
Verdict line + two-paragraph narrative + structured strengths and gaps.
Caching with input-hash invalidation.
*Status: In progress (Phase 2G — narrative generation validated, UI
integration in flight)*

**Talent showcase** — Employer-facing candidate browse. Privacy-redacted
student profiles (first name + last initial) filterable by skill,
location, track. Requires staff-approved showcase-eligibility flag.
*Status: Built (from Vegas work)*

**College partner portal** — Token-based dashboard for partner
institutions (Bellevue College, North Seattle College) showing their
graduates in the Coalition pipeline. ILIKE-based matching of students
to institutions.
*Status: Built (from Vegas work)*

**Recruiting / placement staff workbench (Jessica module)** — The
Workday-style view for Coalition staff doing placement work. Job
listings with match counts, job drill with matched students, student
drill with full profile, application initiation. This is what we've
been building in Phases 2B-2G.
*Status: In progress (Phases 2B-2E built; 2F polish and 2G narratives
in flight)*

**Finance & operations** — The cockpit for grant-funded organizations:
budget & burn tracking, placements, providers, transactions, ESD
reporting, audit readiness. Tabs, drills, and hero metrics.
*Status: In progress (Phases 1-2 built with real CFA data)*

**WJI reporting** — Grant partner dashboard specific to Washington Job
Initiative reporting requirements.
*Status: Built (from Vegas work, specific to CFA's grant context)*

**Compliance / Quinn** — AI assistant for federal grant compliance
management. Agent that helps staff handle provider subawards, grant
documentation, compliance workflows. Scoped narrowly to K8341
initially.
*Status: Designed (design conversations held, not yet built)*

**Upskilling / learning resource discovery** — Agent that scours free
learning resources (primarily YouTube, also documentation, tutorials)
to build a curated catalog of high-quality courses mapped to specific
skills. Integrates with gap analysis so students closing a gap get
specific, ranked learning recommendations.
*Status: Designed (architectural concept developed; not yet built)*

**Student-facing portal** — Student's own view of their journey:
profile, gap analysis, matches, applications, progress. Distinct from
the staff workbench — this is what students see.
*Status: Built (from Vegas work, /student dashboard exists but is
underused)*

**Public arrival experience** — Pre-signup public flow: paste a job,
upload a resume, get a real gap analysis, see natural conversion CTAs.
Addresses the critical "fast value before signup" problem for
acquiring students.
*Status: Designed (build spec drafted — see
coalition_arrival_spec.md; not yet built)*

### Consulting Component — Modules

**Consulting funnel** — Inbound inquiry management: prospective clients
describe what they need, get routed to appropriate intake, build
engagement proposal.
*Status: Built (from Vegas work)*

**Consulting pipeline / engagement management** — Active client work:
engagement lifecycle, scope, deliverables, status, assignments.
*Status: Built (from Vegas work)*

**Client portal** — Client-facing view of their engagements: status,
deliverables, communications, invoices.
*Status: Built (from Vegas work, state unclear)*

**BD and marketing** — Business development pipeline, outreach
management, marketing content, lead tracking. Serves Waifinder's sales
and marketing operations.
*Status: Built (from Vegas work)*

**Apprentice workforce management** — Infrastructure for managing
apprentices as consulting workforce: roster, compensation, engagement
assignments, skill development, progression.
*Status: Planned (partially exists in wtc via Gary's Cohort 1
infrastructure; must be ported to wfd-os as part of wtc sunset)*

**Apprentice curriculum delivery** — Structured learning that happens
alongside client work: training materials, mentor workflows, weekly
sprint cadence, progress milestones. The curriculum infrastructure
Gary built for Cohort 1.
*Status: Planned (currently in wtc; must be ported as part of sunset)*

---

## Part 4 — Cross-Component Flows

Some important flows cross component boundaries. These need to be
supported by the platform architecture even though the components are
organizationally distinct.

### Student → Apprentice transition

A student in Coalition/Workforce may eventually be hired by Waifinder
as a consulting apprentice. When this happens:

- Coalition marks the student as "placed at Waifinder" (treated like
  any other job placement — same as if they'd been placed at Microsoft)
- Consulting creates a new apprentice record for that person
- Some metadata crosses the boundary (provenance: came from Coalition,
  last known gap analysis, skill profile) but the records are distinct
- The apprentice's ongoing data lives in Consulting; their historical
  Coalition record remains in Coalition

This is a clean separation — the person crosses the boundary once,
becoming a new entity in the destination component.

### Coalition student data → Waifinder commercial intelligence

Coalition's aggregate data (anonymized, de-identified) could inform
Waifinder's commercial product intelligence: what skills are in demand,
what gaps students commonly face, what learning resources are most
effective. This requires explicit data-use agreements and proper
anonymization. Not a technical flow but a business flow that needs
governance.

### Cross-customer learning

If Waifinder has multiple Coalition/Workforce component customers in
the future (CFA plus others), the aggregated learning across customers
(anonymized) could improve the platform for all of them. Again, this
requires governance structure and customer consent, but it's worth
noting architecturally — the multi-tenant design should allow for this
pattern.

---

## Part 5 — Customer Segments and Module Mapping

Different customer types want different subsets of the platform.
Waifinder's commercial strategy depends on the modularity that lets
each customer license what they need.

**Workforce development nonprofits (like CFA)**
- Most likely to want: full Coalition/Workforce component
- Also potentially useful: parts of Consulting if they run earned-revenue arms
- Usually not needed: full Consulting component
- Typically also useful: Youth component if the org serves kids too

**Community colleges**
- Most likely to want: Student profile, Job matching, Gap analysis,
  Talent showcase, College partner portal (from Coalition/Workforce)
- Often useful: Upskilling / learning resource discovery
- Usually not needed: Finance/grant infrastructure, compliance,
  full consulting ops

**Bootcamps**
- Most likely to want: Student profile, Job matching, Gap analysis,
  Student portal, Upskilling
- Often useful: Talent showcase for employer partnerships
- Usually not needed: Finance/grant, compliance, consulting ops

**State workforce agencies**
- Most likely to want: Student profile, Recruiting workbench, WJI-like
  reporting, Finance infrastructure, Compliance/Quinn
- Heavy regulatory environment drives need for compliance features
- Usually not needed: Consulting ops

**Corporate L&D departments**
- Most likely to want: Upskilling, Gap analysis, Student profile
  (internal employee profile)
- Sometimes useful: Internal job matching for mobility
- Usually not needed: Most of the rest

**Consulting businesses / services firms**
- Most likely to want: Full Consulting component including
  apprenticeship infrastructure
- Sometimes useful: Talent acquisition pipeline (Coalition/Workforce
  modules) for recruiting
- Usually not needed: Youth, grant compliance

---

## Part 6 — Design Principles

The architectural commitments that govern how wfd-os evolves.

### Principle 1: Design broad, implement narrow

Think ambitiously about the architecture — where boundaries are, what
interfaces look like, what the full product family might someday be —
but only build what's needed right now. Document the broad design;
implement the narrow current need.

This protects against both pre-building unnecessary flexibility
(which slows delivery and complicates maintenance) and painting into
architectural corners (which forces rework when real demand emerges).

When considering any new build: default answer is no unless there's a
concrete current trigger — a real customer asking, a real problem in
the current product, a real revenue opportunity.

### Principle 2: Module boundaries are real, not just organizational

Modules communicate through well-defined interfaces. A module's
internals are private to it. Other modules can consume its outputs but
cannot reach into its data model or implementation.

This is the commitment that makes modularity commercially real — a
customer can license Coalition/Workforce without Consulting because
the modules actually are separable, not just documented as separable.

### Principle 3: Data ownership is clean

Customer data belongs to the customer. Waifinder is custodian. Data
is isolated between customer organizations (multi-tenancy from the
start). Anonymization for cross-customer learning is a deliberate,
consent-based process, not a default.

### Principle 4: AI-native, not AI-bolted-on

wfd-os was built in the agentic rewrite era because AI capabilities
enable things the earlier three-tier platform couldn't do well —
reasoning over unstructured data, personalized intelligence,
conversational interfaces, content generation. New modules should use
AI for what AI is actually good at, not as decoration.

Corollary: quality of AI-generated content matters more than quantity.
A feature that produces poor-quality narratives/recommendations/
analyses erodes user trust faster than having no such feature.
Validation steps (like the sample-review step used in Phase 2G) should
be the norm, not optional.

### Principle 5: Honesty over marketing

Output the platform produces — gap analyses, match narratives,
recommendations, reports — should be honest even when the honest
answer is uncomfortable. A gap analysis showing a student is far from
employable should say so. A match score that's weak should be labeled
weak. A budget that's running hot should look hot.

This applies across the platform. Recruiters, students, administrators,
grant officers — they all trust the platform more when it tells them
the truth than when it tells them what they want to hear.

### Principle 6: Sustainable cleanliness

Tech debt accumulates from deferred cleanup, inconsistent patterns,
and quick hacks. wfd-os has been pretty disciplined about this so far
(shared shell extraction, type definitions, deferred-item tracking).
Maintaining that discipline is what keeps development speed
compounding. Sloppiness compounds the other direction — faster now,
much slower later.

### Principle 7: Narrow first customer, broad architecture

The platform's first real commercial customer will be CFA (if CFA's
board approves) or potentially another workforce development org.
That first customer's needs will shape what gets built and what gets
polished. That's fine. But the architecture should anticipate that
the second and third customers will have different needs — so the
decisions being made for customer one should be module-internal, not
architecture-global.

---

## Part 7 — What's Deliberately Not in wfd-os

Things considered but intentionally excluded, at least for now.

**Identity management as a platform module.** We may need auth
(passwordless, probably via magic link + OAuth — template exists in
wtc to learn from). But that's infrastructure, not a commercial
module. Customers don't license "identity management"; they license
modules that include identity for their users.

**Payment processing.** Customers pay Waifinder via standard
commercial billing (invoice, ACH, credit card). Not a platform module.

**Generic LMS features.** wfd-os does upskilling via the learning
resource discovery agent and (for Consulting apprentices) via
structured curriculum. It is not a generic Learning Management
System. Customers who need a full LMS should license an LMS separately
and integrate.

**Generic CRM features.** BD/marketing exists for Consulting, but
wfd-os is not a Salesforce replacement. Customers who need a full
CRM should license a CRM separately.

**K-12 curriculum content.** Youth component may eventually have
curriculum delivery, but it provides the infrastructure for
delivering curriculum — not the curriculum itself. Content is the
customer's responsibility or a separate partnership.

**General-purpose agent framework.** wfd-os uses agents for specific
workforce-development purposes. It is not a general-purpose agent
platform like LangGraph or CrewAI. Customers who want to build
arbitrary agents should use those tools.

---

## Part 8 — Open Questions

Things the architecture doesn't fully resolve yet. Worth being
explicit about rather than pretending everything is settled.

**Multi-tenancy model.** Is wfd-os going to be a single multi-tenant
deployment (all customers share infrastructure, data isolated per
customer) or separate deployments per customer (heavier ops but
stronger isolation)? The answer shapes a lot of infrastructure
decisions.

**Module licensing granularity.** Can customers license individual
modules, or must they license whole components? Finer granularity is
commercially flexible but operationally more complex.

**Data portability and exit.** If a customer leaves, how does their
data come with them? SaaS customers care about this; it affects
willingness to commit.

**JIE integration.** The Job Intelligence Engine is currently a
separate repo with its own architecture. When/how does it integrate
into wfd-os? As a separate service that wfd-os calls? As a module
that gets absorbed into wfd-os? What's the timeline?

**wtc sunset timing.** When is wfd-os "stable enough" for Cohort 1 to
transition? What's the criteria? Who makes that call? Without
explicit criteria, the transition can drift indefinitely.

**Apprentice component port.** The apprentice workforce management
and curriculum delivery infrastructure lives in wtc today. Porting it
to wfd-os is Gary's work. What's the timeline? What's the scope?

**Compliance module scope.** Quinn is designed for K8341 specifically
but general federal grant compliance is a much broader market.
Commercial scope decision needed: narrow (K8341-shaped workflows) vs.
broad (generic federal grant compliance agent).

**Pricing model.** SaaS subscription per seat? Per student processed?
Per customer organization? Annual license? The commercial model isn't
set yet and will shape both engineering and go-to-market.

**Go-to-market strategy.** Beyond CFA, who does Waifinder sell to
first? Second? Third? Different customer segments require different
sales motions, different product emphasis, different pricing.

---

## Part 9 — Living Document Maintenance

This document reflects the architecture as understood at the time of
writing. It should be updated as:

- Modules move from Designed to Planned to In Progress to Built
- New modules are added (or removed) based on real customer demand
- Customer segment understanding deepens through actual sales
  conversations
- Open questions resolve
- Design principles evolve (though core principles should be stable)

Ritu is the editor. Updates should happen at natural decision points —
when a module ships, when a new customer is engaged, when strategic
direction shifts. The goal is to keep the document accurate enough to
serve as a shared reference without making it a maintenance burden.

---

*End of document.*
