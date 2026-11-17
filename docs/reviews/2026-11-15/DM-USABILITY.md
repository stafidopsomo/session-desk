# DM usability review and unified workspace direction

Date: 2026-11-15. Review role: experienced practical DM advising a newer DM. Method: read-only source/content review by a separate agent, with primary-agent verification. This is not a live usability study or a claim that the proposed interface is implemented. No campaign data is included in this public report.

## Finding

The product currently has two frontends behind one launcher. The migration preserved authored files but also preserved a separate, plot-specific operating model. A prepared packet with all the facts is not necessarily runnable under table pressure.

`static/app.js` opens imported adventures in a generic reader, but routes prepared workspaces through a second application. `static/prepared/bootstrap.js` hides and renames navigation from campaign content. `static/prepared/app.js` keeps its view in memory; DM map and room selection send shared actions. `prepared_engine.py` turns those map actions into player tabs and shared selection. Two DM tabs therefore interfere. URL duplication cannot retain the current destination.

The prepared chapter renderer displays long authoring lists, source caveats and alternate plans at the same priority as the next thing the DM must say. Missions are represented by loose character threads, with no reliable distinction between offered work, accepted work, completed objectives and paid rewards. `Idea` mixes approved secrets with undecided proposals. Multiple editable files/workspace copies increase context drift.

## Target product contract

One Campaign contains its own evolving Campaign Book and references any number of imported adventures. New and restored campaigns use the SAME stable shell:

- **Book**: Now, Chronicle, Missions, Places/people, next-session preparation and private ideas.
- **Resources**: source books, maps, images and rules references.
- **Party**: character records and their linked personal threads.
- **Open player screen** stays in the header. Settings stays in the header.

Empty campaigns show useful creation prompts inside these stable sections. Story chapters never create/rename/hide top-level application tools. Do not solve the split by embedding the entire old application behind another tab or duplicating its state.

Source books are immutable references. The Campaign Book is editable campaign data that reuses the existing safe book renderer, not a repeatedly re-imported fake source book. Preserve original source IDs, assets, dimensions, map collars, polygons and fog chronology. Compatibility adapters can read old data internally while the shared shell replaces the legacy surface.

## First implementation slice

1. Separate tab-local DM selection from shared presentation. Inspection must never open or activate a player tab. Explicit Present, player-tab selection, reveal/hide, shared notes and drawing have clear shared effects.
2. Route workspace, book entry, resource, map/room, mission and character with stable URLs. Support normal links, Open in new tab, duplicate, reload, Back/Forward. Keep the user-selected camera local until explicit presentation/focus actions.
3. Protect concurrent edits with document revisions and field patches. A conflicting save must retain the draft and explain the conflict; never silently replace an entire character/thread/preparation array.
4. Add the native Campaign Book and mission records to the common workspace storage/backup contract. Migrate old content with provenance, leaving recovery exports intact. Do not derive played outcomes from prepared scenes.
5. Replace the separate prepared launch path with common Book/Resources/Party navigation after migration parity passes. This is a single integration milestone; no release should claim unification merely because a new button opens the old frontend.

## Book and mission model

Book entries have permanent IDs, chapter/parent links, Markdown or structured content, source references, DM/player visibility and revision history. Session reports are dated facts; unknown facts stay unknown. Plans and secrets are distinguishable from confirmed events. Quick notes are captured in seconds and linked later to an entry, mission or NPC.

Missions need giver, participants, objective, completion criteria, next lead, related places/scenes, status and outcome. Use Draft / Offered / Active / Resolved / Set aside; Resolved has a separate success/partial/failure outcome. Rewards offered and rewards awarded are separate. General mysteries can remain threads; do not turn every old Idea into an accepted mission.

The adopted workspace should be the single editable campaign record. Export readable Markdown/JSON context packets for Git and LLM work as projections. During the transition, document the exact authoritative workspace and preserve divergent authoring files rather than overwriting them. AI provider integration remains deferred; this data workflow must work manually.

## Runnable scene standard

The first screen must answer: situation now; who wants what; immediate player options; essential clues; reactions/consequences; and the next possible lead. Put a short optional Greek read-aloud beside this card. Fold source explanations, alternate designs and full room prose below it. Match labels/exits to the actual map and use a finite defender roster. Core clues never require a surviving interrogatee or a successful search roll.

A spirit-based character arc can be tracked through the same records: met spirit, unresolved quest, relationship, resolution and optional boon. Do not build a separate spirit subsystem before mission tracking works, and do not grant permanent abilities from a planning note.

## Release acceptance: demonstrate, do not infer

- New empty campaign and restored prepared campaign use the same Book/Resources/Party shell.
- Party in one tab and a regional map in another remain independent.
- Duplicate/reload a specific book entry and retain its address and selection.
- Browse maps/rooms without changing the TV; Present works explicitly.
- Edit separate notes from two tabs without silent loss; show and preserve a conflicting draft.
- Offer, accept and resolve a mission; link the outcome to a session report and leave unpaid rewards visible.
- Capture an improvised note without leaving the current resource.
- Find an encounter's essential clues within one screen.
- Export/restore and compare all character records, authored files, assets and fog operations.

Use original synthetic fixtures in public CI. Private campaign acceptance stays local. Retain the current release and an untouched recovery export until these tasks pass. AI integrations, docking systems and automatic boon execution are later work.

## Current baseline validation

Thirteen isolated storage/recovery checks passed, including a synthetic newly authored journal and reading view surviving backup/restore with unchanged character and fog bytes. The public product boundary check passed. These checks validate preservation in the current storage format; they do not demonstrate the proposed unified UI, stable navigation or conflict handling. No new runtime build/release was produced for this review.


## November 17 local preview checkpoint

An opt-in shared shell now provides native Book/mission editing, Party notes and independent Resources navigation in an unpublished Windows test build. Legacy map geometry/fog is reused as a component rather than embedding the old desk. Workspace creation records Campaign or One-shot; both retain the same tools. Record revisions reject stale writes and retain drafts. All automated source/frozen browser/package checks pass, including independent tabs, reload, the player window and copied-campaign backup parity. Advanced sheets still use the compatibility editor; full scene-card conversion, cross-source presentation, context projections and onboarding remain acceptance work. This first test slice does not close the complete release checklist above.
