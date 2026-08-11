<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# The exploradora thesis

Exploradora is the human-facing client of a planned distributed ecosystem of
small, verifiable model adapters — a package manager and explorer for
*skills* instead of software. This document describes where the project is
going and, just as deliberately, what is and is not yet true. The project's
credibility model is **claims you can check**; a vision document that
oversold its own state would fail the thesis in its first file.

## A network, not a monolith

The long-term bet: a frontier-class AI system does not have to be one giant
model in one datacenter. It can be a *network* — a shared small base model
(a few GB, runnable on consumer hardware) plus thousands of community-minted
LoRA-family adapters, each teaching one skill, each carrying **checkable
claims** instead of marketing. The base model is the runtime, a frozen
shared adapter frame is the ABI, adapters are the packages, and
*verification* — not central curation — is what makes a stranger's adapter
trustworthy.

The architecture splits in two, and the split is a principle:

- **The client ships via PyPI** (`pip install exploradora`) — the trusted
  computing base: the TUI, the verifier, the manifest tooling. Slow-moving,
  versioned, auditable code.
- **The adapters ship via the exchange** — peer-to-peer, inside the client,
  independent of PyPI. Adapters are *untrusted content by design*: small
  weight files whose identity is a content hash and whose claims are
  replayable computations. **PyPI ships code you execute; the exchange
  ships weights you evaluate.** Different trust models, different channels.

The experience this points at: browse adapters people have published,
inspect their provenance and receipts, *run* a candidate against freshly
minted held-out tasks on your own machine before trusting it, install it,
compose several into a working system, publish your own. Package-manager
verbs: `search`, `install`, `verify`, `compose`, `publish`, and eventually
`check` — the pip-check analog that inspects an installed adapter set for
*conflicts*: adapters that contest each other's answers rather than
factoring cleanly.

**None of that network exists yet.** What exists today is the v0.1 seed: the
manifest schema those claims will live in, and a local explorer that
verifies what is checkable now (see STATUS in the README).

## Why peer-to-peer is safe here

Every adapter's identity is a content hash (tamper-proof), and every claim
it ships ("passes these 40 held-out tasks") is a deterministic, replayable
computation another node can re-run. Trust is settleable **locally, at
install time, by verification** — so no registry has to vouch, and the
exchange can be permissionless. Adapters are small enough to be
torrent/DHT-native. The one pragmatic centralization: the base model itself
is fetched once, hash-pinned, from a conventional host.

## Social proof and verification do different jobs

Exploradora is also designed to be a social network, and that is not a
concession. The model hub's defect is not that it has reputation — it is
that reputation is the *only* recourse, because users cannot cheaply check
anything. Here the two form one funnel: **social proof is the prior that
decides what you spend verification on; verification is the posterior that
decides what you trust.** Signals order by cost and groundedness: installs
and popularity (free, ungrounded) · curation by people you follow (free,
accountable) · **third-party replay attestations** (free to the reader, and
grounded — someone else re-ran the receipt) · your own verification against
the publisher's tasks · your own verification against tasks you mint on the
spot. The attestation tier is the one this architecture can build and a hub
cannot: *"27 independent nodes replayed this manifest's claims and agreed"*
is simultaneously a social fact and a checkable one.

The right economics is **spot-check, not universal verification**: nobody
audits their whole npm tree, and the ecosystem stays honest because anyone
*can* and enough do that lying is unprofitable. Published attestations turn
redundant re-verification into evidence accumulation.

## Local-first, and therefore private

The base model runs on your hardware; your prompts and data never leave
your machine; adapters you mint from your own text are yours and leave only
if you publish them; verification of other people's adapters happens
locally — you don't send your test cases anywhere. No telemetry in v0.1 at
all; any future telemetry would be opt-in, anonymized, and scientific in
purpose. The aspiration: the entire loop — explore, verify, compose, mint —
runs on an air-gapped machine given a synced snapshot of the exchange.

## The research bets underneath, with honest status

Exploradora is the product face of an active research program. The
load-bearing bets, all open — presented as bets the project is built to
test, not as achieved features:

1. **Verification-grounded trust** — executable checks, not reputation
   alone, as the trust primitive. *Status: working today at small scale,
   same-machine/same-stack. Across heterogeneous nodes bit-identity is not
   owed, so an attestation must state which agreement relation it asserts —
   the manifest schema's `agreement_relation` field exists for exactly
   this, and the honest default is verdict-level agreement.*
2. **The frozen-frame ABI** — all adapters share one frozen down-projection,
   so an adapter *is* its coordinates: comparable, mergeable,
   geometry-readable. *Status: the frame-tag compatibility system is
   designed into the schema now (including the load-bearing, one-way
   `parameterization` field: LoRA converts to DoRA exactly, DoRA has no
   exact low-rank inverse); no resolver exists yet.*
3. **The contest fingerprint** — that *contestation* (two corpora or
   adapters that disagree rather than factor) has a detectable signature,
   making a cheap `check` possible. *Status: measured, and the result is
   partial — weak as a classifier, usable as a filter. Its primary use is
   improving corpus quality by splitting contested corpora into cleaner
   ones. Of that splitting pipeline: the localization gate is validated
   out-of-sample; the splitter refuses harmful cuts; the stopping rule
   survives realistic (correlated) detector error only with a small fixed
   slack — a zero-tolerance rule is a knife edge; and under that same
   correlated error the cut is taken correctly while each misread row lands
   in the wrong child — a purity cost measured to equal the detector's
   row-misread rate, exactly. No triage product exists yet.*
4. **Composition improves with experience** — a network that only
   accumulates skills is a library; it becomes frontier-like only if
   composition itself is learned. *Status: routing + verify works today on
   synthetic substrates, and it is the floor that survived measurement, not
   the destination — verification costs real compute per candidate, so a
   purely route-and-verify network is plausibly too slow to be practical at
   scale. The learned weight-space route remains a major open research
   direction: static merging is winner-take-all at greedy decode, yet both
   skills stay present in the merged weights and reweighting exposes bands
   where both express — the barrier looks like decode expression, not
   capacity. One specific learned form (predicting a merged adapter from
   its parents, at family grain) was falsified and priced out in a measured
   attempt; the broader program's evidence is mixed — it doesn't work yet,
   and it doesn't not work. Near-term shipping follows what is verified:
   routing first, learned composition as it earns its way in.*
5. **Single-skill minting from wild text** — that contest-free corpora
   within a tunable neighborhood can teach clean single skills cheaply.
   *Status: partially supported synthetically; external validity untested —
   the largest untouched gap in the program.*

## What v0.1 deliberately is

A name-claiming, foundation-laying release that is real: a local adapter
library explorer with an honest verifier and a manifest schema designed so
that attestations, payment/licensing metadata, and claim replay can attach
later without redesign. No network code, no p2p, no model inference, no
telemetry. The schema is the release's most important artifact; the fields
that could never be retrofitted once adapters circulate (`parameterization`,
graded `verification`, `oracle_basis`, `agreement_relation`) are in it now,
even though v0.1 verifies none of them — and the verifier says so rather
than blessing what it did not check.
