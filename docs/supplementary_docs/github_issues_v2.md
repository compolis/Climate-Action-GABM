# Climate-Action-GABM — Planned GitHub Issues v2

## About This Document

This file is the **planning scaffold** for the next development cycle after the completed v0.4 work. It is **not yet** a set of GitHub-ready issues. Its job is to capture scope, confirmed decisions, work tracks, dependencies, and the open questions that need to be resolved before we expand the plan into multiple concrete GitHub issues.

**Status:** planning only, step-by-step.

**Relationship to other docs:**
- [Model_Design.md](Model_Design.md) remains the current design baseline.
- [github_issues.md](github_issues.md) records the earlier implementation plan that produced the current model.
- This file is the skeleton for the future issue set and will be expanded gradually.

## How To Read This File

- **Phases** describe the order in which planning should happen.
- **Tracks** describe the main topic areas of the work.
- **Groups** are placeholders for future GitHub issue bundles.

For now, the practical focus is simple:

- **Current step:** Phase 1 / Track A
- **Current goal:** define the two separate contact structures, the first redesign targets for network assignment, and the first asymmetry controls

---

## Planning Context

The current codebase already supports:

- citizen agents built from YouGov survey personas
- political-agent broadcasting
- peer messaging
- package communication mode
- Day-0 anchoring
- checkpoint/resume
- reach controls (`reach_a`, `reach_b`) and audience controls (`audience_cap`)
- multiple API-based LLM providers

The next planning cycle is aimed at the **next architectural step**, not at minor extensions to the current v0.4 surface.

The paper and current framework already treat **peer exchange** and
**political exposure** as separate structures. The main planning task here is
therefore **not** to re-open that basic principle, but to improve how the two
structures are represented, assigned from survey data, and varied
experimentally.

---

## User-Confirmed Planning Decisions

The following decisions are already fixed for this planning cycle:

1. **Both political broadcast and peer messaging remain in the model.**
   The future communication model is hybrid. We are not dropping either channel.

2. **The exact proportion and rules between direct and peer influence are deferred.**
   These will be decided later, likely after team discussion and literature review.

3. **Peer and broadcast networks should be separate.**
   This is required for custom control and cleaner experimental design.

4. **Message frequency asymmetry must be supported.**
   One political agent should be able to send messages more frequently than the other.

---

## Current Planning Scope

This planning scaffold covers the following eight themes:

1. **Move beyond the stochastic block model** to alternative network models and a pluggable network factory.
2. **Rethink the rule assignment for peer and political broadcast channels**, while retaining both channels.
3. **Support local LLMs as first-class/default model options** alongside API-based models (for example `Llama`, `Qwen`, `Apertus`, and compatible local runtimes).
4. **Add safe parallelization** for both API-based and local inference to reduce wall-time.
5. **Support stored real political communication** for the six climate-policy topics, alongside LLM-generated messages.
6. **Review and redesign memory architecture** in light of more recent agentic/RAG patterns and LLM-agent best practices.
7. **Keep the framework clean, modular, and object-oriented**, with explicit attention to software-engineering quality as the system grows.
8. **Add message frequency asymmetry controls**, so the two political agents can operate at different message cadences.

---

## Planning Principles

1. **Architecture before implementation.**
   We should avoid adding features directly into the current simulation loop without first deciding module boundaries and interfaces.

2. **Experiment control matters.**
   New knobs should support interpretable experimental designs, not just extra flexibility.

3. **Separate research work from engineering work where possible.**
   Some tracks involve literature review, corpus collection, and theory design; others are pure implementation.

4. **Preserve clean defaults.**
   The framework should stay usable by default even as richer options are introduced.

5. **Prefer pluggable abstractions over one-off branches.**
   New networks, message sources, memory strategies, and model providers should slot into explicit interfaces.

---

## High-Level Track Structure

This plan is split into parallel tracks, but some design gates must be resolved first.

### Track A — Communication Model and Network Architecture

Focus:
- separate peer and broadcast contact structures
- define the first concrete representation of each structure
- add network-model extensibility beyond SBM
- redesign survey-based assignment and routing rules
- add message-frequency asymmetry and related broadcast controls

### Track B — Political Message Sources and Corpus Work

Focus:
- define how stored real political messages enter the framework
- curate Reform/Green climate-policy message sets for the six target policies
- support stored-message defaults with LLM-based fallback or comparison modes
- design message metadata, provenance, and storage conventions

### Track C — Local LLMs and Runtime Execution

Focus:
- local-model support as a first-class pathway
- API/local provider abstraction
- capability matrix for different model backends
- safe concurrency and performance improvements

### Track D — Memory Architecture and Retrieval Design

Focus:
- review the current tiered-memory design
- define what richer memory should optimize for
- design a modular memory backend that can later support retrieval, compression, and selective recall

### Track E — Framework Architecture, Modularity, and Quality

Focus:
- maintain coherent object-oriented structure
- keep interfaces clean while tracks A-D expand
- define integration rules, tests, and documentation standards

---

## Dependency Logic

### Planning Gates That Must Happen Early

These design questions should be resolved before most implementation issues are written:

1. **Two-structure design gate**
   We already know both channels stay and that peer and broadcast structures
   should remain separate. The early planning task is to decide the first
   concrete form of that separation:
   - how the peer side should be represented and varied beyond SBM
   - how the broadcast side should be represented for direct political messaging
   - how survey data should be used to assign citizens into the peer structure
   - how survey data should be used to assign broadcast audiences
   - which asymmetry controls should be prioritized first

2. **Interface boundary gate**
   Before implementation, we should define the intended abstraction boundaries for:
   - network factories
   - exposure/channel policy
   - message sources
   - LLM providers
   - runtime execution/concurrency
   - memory backends

### Work That Can Proceed In Parallel After the Gates

Once the communication semantics and interface boundaries are defined, the following can be planned in parallel:

- alternative network models and routing rules
- real-message corpus collection and schema design
- local-model backend planning
- memory/RAG review and backend design

### Work That Should Stay Later

- full integration issues
- benchmark and validation plans
- final GitHub issue conversion

---

## Candidate Planning Phases

### Phase 0 — Scaffold and Scope

Purpose:
- create this planning document
- record confirmed decisions
- define the track structure and dependency logic

### Phase 1 — Resolve the Communication and Interface Gates

Purpose:
- define the two separate contact structures
- decide the first redesign targets for peer-network models beyond SBM
- decide how survey data should drive peer and broadcast assignment rules
- define where frequency, reach, and audience asymmetry controls belong
- freeze the intended architecture seams before feature planning goes deeper

### Phase 2 — Expand the Parallel Tracks

Purpose:
- turn each track into a set of candidate issue groups
- identify what can be shared with colleagues in parallel
- identify which tasks are research-heavy versus engineering-heavy

### Phase 3 — Integration and Validation Planning

Purpose:
- define cross-track integration rules
- define tests, notebooks, and benchmarking expectations
- ensure the framework remains coherent rather than patchwork

### Phase 4 — Convert to GitHub-Ready Issues

Purpose:
- expand the approved planning skeleton into concrete issue drafts
- split the work into batches suitable for implementation by multiple contributors

---

## Candidate Issue Groups (Skeleton Only)

These are **not yet final GitHub issues**. They are placeholders for the shape of the future plan.

### Group A — Two-Network Communication Model

Possible issue themes:
- define the peer contact structure
- define the broadcast audience or routing structure
- redesign survey-based assignment rules for each structure
- define where future direct-vs-peer weighting or proportion controls live

### Group B — Network Model Extensibility

Possible issue themes:
- pluggable network factory
- support for multiple peer-network topologies beyond SBM
- network diagnostics and validation outputs
- configuration schema for separate peer and broadcast graphs

### Group C — Channel Asymmetry Controls

Possible issue themes:
- message frequency asymmetry
- message reach asymmetry
- audience-size asymmetry
- interaction between frequency, cadence, reach, and audience controls

### Group D — Real Message Corpus and Message Sources

Possible issue themes:
- message-source abstraction
- stored-message schema and provenance
- manual or semi-structured corpus curation for Reform/Green climate communications
- default source selection rules (stored vs generated)

### Group E — Local LLM Provider Support

Possible issue themes:
- local-provider abstraction
- runtime/backend compatibility matrix
- default local model pathway
- testing and configuration for local inference

### Group F — Parallelization and Runtime Control

Possible issue themes:
- concurrency model for API and local backends
- rate-limit and backpressure handling
- runtime benchmarking
- reproducibility implications of concurrency

### Group G — Memory Architecture Redesign

Possible issue themes:
- review target memory goals
- define modular memory backend
- compare current tiered memory with RAG/episodic/retrieval-style designs
- define what is needed now versus what is future-facing

### Group H — Framework Quality and Integration

Possible issue themes:
- architectural cleanup and module boundaries
- interface consistency
- test strategy and coverage growth
- documentation and developer workflow rules for future growth

---

## Initial Parallelization Map

### Work That Could Be Shared With Colleagues Early

- literature review on communication channels and political-exposure design
- review of alternative network models and experimental affordances
- curation of real political message corpora
- survey of local-model runtimes and provider options
- review of agentic/RAG memory patterns relevant to this framework

### Work That Should Stay Centralized Early

- defining the two-network communication semantics
- defining the main abstractions and config surface
- defining how asymmetry knobs fit together
- deciding how much architectural change is acceptable in one cycle

---

## Open Questions for the Next Planning Pass

These are the most useful questions to answer next.

1. **Which alternative peer-network models should be the first comparison set beyond SBM?**
   Examples: Erdős–Rényi, Watts–Strogatz, Barabási–Albert, homophily-weighted models, or other survey-informed structures.

2. **How should survey data be used to assign the peer structure?**
   Examples: mainly social similarity / homophily, mainly alternative graph families, or a hybrid of both.

3. **How should survey data be used to assign broadcast audiences?**
   Examples: vote history as the default driver, or a broader mix of survey signals from the start.

4. **Should the broadcast side be implemented first as a separate audience/routing layer, or as a fuller network structure?**

5. **For message frequency asymmetry, what is the intended first control surface?**
   Examples: messages per day, number of broadcast events per phase, or asymmetric day schedules.

6. **Should stored real political messages be purely manual/curated, or should the plan leave room for a semi-automated collection pipeline?**

7. **Which local-model runtime should be treated as the first serious target?**
   Examples: `ollama`, `vllm`, `lm-studio`, `apertus`, or an OpenAI-compatible local endpoint.

8. **What is the primary goal of the memory redesign?**
   Examples: behavioral fidelity, lower cost, longer-run coherence, interpretability, or all of these in a defined order.

---

## What This Document Is Not Yet

This file does **not yet** contain:

- final issue numbering
- full issue descriptions
- acceptance criteria per issue
- implementation sequencing at task level
- detailed test plans per issue

Those will be added only after the planning gates above are discussed and approved.

---

## Next Step

The next planning pass should focus on **Track A / Phase 1**:

- define the two separate contact structures more concretely
- identify the first alternative peer-network models to compare with SBM
- define how survey data should assign peer and broadcast structures
- define the first asymmetry controls for broadcast frequency, reach, and audience size

Once that is clear, the rest of the plan can be expanded with much less risk of rework.