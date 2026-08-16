# Talkar Persistent Narrative RPG

An instruction stack for running a persistent, long-form text roleplaying campaign set in **Talkar's Sky Islands** — a world of floating islands, layered magical storms, professional sky crews, and a civilization-scale migration that recurs roughly every ten years.

This is not a branching-choice adventure module. It is a set of layered documents that turn a language model into a **Game Master, world simulator, and continuity keeper** for a living world: NPCs act offscreen, contracts get taken by other crews, rumors mutate as they travel, and the player is one ordinary person who can *earn* importance rather than being handed it.

## Document Stack

The campaign uses separate information layers that must never be silently merged. Load them together; each has a distinct job.

| File | Document | Role |
|------|----------|------|
| [`00-master-instruction-set.md`](00-master-instruction-set.md) | Master Instruction Set | Top-level GM role, narrative philosophy, and campaign rules for Talkar |
| [`01-narrative-interaction-model.md`](01-narrative-interaction-model.md) | Narrative Interaction Model | Setting-agnostic model of attention, perception, relationships, subtext, and narrative memory |
| [`02-rpg-engine-v2.md`](02-rpg-engine-v2.md) | Persistent Narrative RPG Engine v2 | Setting-independent simulation rules: causality, time, knowledge architecture, consequence, state management |
| [`03-sky-islands-reference-repository-v1.md`](03-sky-islands-reference-repository-v1.md) | Sky Islands Reference Repository v1.0 | Setting canon: what currently exists, tagged by canon status (TEXT CANON / CURRENT CANON / PROVISIONAL / OPEN / VERSION CONFLICT / LEGACY / REJECTED-SUPERSEDED) |
| [`04-sky-islands-simulation-layer-v1.md`](04-sky-islands-simulation-layer-v1.md) | Sky Islands Simulation Layer v1.0 | How the setting changes over time when the player isn't looking: weather, routes, economy, wildlife, migration clock |
| [`05-campaign-initialization-kit-v1.md`](05-campaign-initialization-kit-v1.md) | Campaign Initialization Kit v1.0 — The Aven Corridor | A ready-to-play region: Aven, Pere, Dema, twenty seeded NPCs, fifteen background situations, and session-one openings |
| [`06-relationship-emphasis.md`](06-relationship-emphasis.md) | Relationship Emphasis Module v1.0 | Player-selected romance opportunity density (Low / Open / Romantic Lean / Romance Forward) — controls opportunity, never outcome |

### How the layers fit together

* The **Reference Repository** determines *what exists*.
* The **Simulation Layer** determines *how those things behave over time*.
* The **RPG Engine** determines *what can happen and how the world advances*.
* The **Narrative Interaction Model** determines *how experience, attention, relationships, and meaning accumulate through play*.
* The **Initialization Kit** provides the starting region, cast, and pressures for a new campaign.
* The **Relationship Emphasis Module** tunes how much romantic opportunity the simulation surfaces, without predetermining attraction or pairings.
* The **Master Instruction Set** binds the whole thing into the GM's role and design philosophy.

Two runtime layers are created during play rather than stored here:

* **Campaign State** — what has happened in a specific playthrough (the Engine's `/save` command produces a portable version).
* **Narrative Memory Ledger** — accumulated narrative context (recurring objects, behavioral permissions, unresolved exchanges) that plain facts don't capture. It starts empty; play fills it.

### Authority and precedence

When sources conflict (per Engine §2):

1. Explicit current player instruction or explicit retcon
2. Current Campaign State (things already established in play)
3. Current designated Sky Islands Reference Repository (setting canon)
4. Narrative Interaction Model (narrative behavior)
5. RPG Engine defaults
6. Improvisation

The newest explicitly designated repository version supersedes older setting material. Legacy Talkar lore is **not** automatically Sky Islands canon.

## Starting a Campaign

Give all seven documents to the model as its instructions, then say **START NEW CAMPAIGN**. The GM will ask only enough to begin — name, rough age, what your character does or why they're on Aven, whether you want to define your past now or discover it through play, and your desired relationship emphasis (Low / Open / Romantic Lean / Romance Forward) — then drop you into ordinary life in the Aven Corridor.

Out-of-character commands recognized during play: `/status`, `/character`, `/known`, `/suspicions`, `/relationships`, `/threads`, `/recap`, `/save`, `/ooc [question]`.

## Core Design Rules (the short version)

* **The world moves offscreen.** NPCs, organizations, weather, markets, and the migration clock advance whether or not the player is present. The player frequently meets the *wake* of events, not the events themselves.
* **No main-quest gravity, no quest markers, no dialogue trees.** The player may type anything reasonable; offered options are only ever illustrative.
* **Importance must be earned.** No chosen ones, hidden royalty, or identity-as-key plots. Competent people existed before the player and continue existing.
* **Knowledge is a mechanic.** Objective reality, player knowledge, player belief, and per-NPC knowledge are tracked separately; information travels through plausible channels only.
* **Show, don't announce.** Relationships are behavioral systems with asymmetric permissions, not approval meters that unlock scenes.
* **Romance is opportunity, never outcome.** The relationship emphasis setting controls how much interpersonal proximity and social opportunity the simulation provides; attraction, affection, intimacy, commitment, and compatibility remain separate states, and no NPC is ever designated as a route.
* **Simulation before drama.** Events happen because `state + pressure + actors + time → change` — never because "the player needs something to do."
* **Migration is history, not apocalypse.** The ten-year cycle begins as background pressure (bridge inspections, warehouse reservations) and earns its centrality slowly.
* **Open questions stay open.** The Repository deliberately preserves unresolved canon (the obfuscator lead's final name, Vera's transport, the storm's origin). The RPG must not casually solve them.

## Versioning

The Reference Repository is a living document: setting information can be revised, replaced, expanded, or removed without rewriting the Engine or the Narrative Interaction Model. When a repository version changes mid-campaign, the Engine's §53 governs how new canon applies going forward without silently rewriting play history.
