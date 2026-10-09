# Software Architecture Styles

This project is small enough that its architecture (see
`ARCHITECTURE.md`) barely needed a name — a handful of files, one
composition root, done. Bigger projects need to make that same kind of
decision much more deliberately, because the wrong structure doesn't just
look messy, it actively slows the team down. This doc covers two things:
why size changes the calculus at all, and then a tour of the standard
named answers to "how do we structure this" — what each one is, when it
earns its cost, and where it tends to hurt.

## Why does project size change what "good structure" means?

**The concrete, small-scale version of this problem, from this project's
own history:** before the `src/` layout change, `natural_mouse` sat
directly at the repo root (a "flat layout"). That's completely fine at
this size. But it's a known trap at larger scale: if a *different*,
possibly older or broken copy of a same-named package exists anywhere
else on `sys.path` — another project's checkout, something installed
globally, a stale build artifact — Python will happily import whichever
one it finds first, and you can end up testing or running against code
that isn't the code you're looking at, with no error to warn you. A `src/`
layout makes that structurally harder to do by accident: nothing gets
imported by "happens to be in the current directory," only through an
explicit, deliberate path. At one file and one contributor, this risk is
close to zero. At dozens of contributors, multiple environments (a
laptop, CI, a deploy server), and packages that need to be built and
installed rather than just run in place, it stops being theoretical.

**The more general pattern behind that example:** every problem below
gets worse specifically as size (in code, in people, or in both) grows,
and mild architectural discipline is what keeps each one in check:

- **Coupling compounds silently.** In a 10-file project, "anything can
  import anything" is harmless — you can hold the whole dependency graph
  in your head. In a 10,000-file project, the same lack of enforced
  boundaries means a change in one place can break something arbitrarily
  far away, in a way nobody predicted, because nothing ever stopped that
  distant code from reaching in and depending on an implementation
  detail.
- **Testability degrades without enforced seams.** This project's own
  `UIAutomator` is only unit-testable in isolation because Dependency
  Inversion (see `LEARNING_RESOURCES.md` §"Dependency Inversion") drew a
  hard boundary between orchestration and real I/O. Skip that boundary at
  scale and you get a codebase where "just write a test" requires
  standing up half the system first.
- **Build/test/deploy time scales with what's coupled together, not with
  what actually changed.** A true monolith means a one-line fix still
  requires rebuilding, retesting, and redeploying everything — fine at
  small scale, a real cost once a build takes an hour and a hundred
  people are shipping changes daily.
- **Team ownership needs boundaries to mean anything.** "Team A owns this
  part" is only enforceable if there's an actual seam — a module
  boundary, a service boundary — that Team B's code can't casually reach
  across. Without one, "who owns this" becomes an argument, not a fact.
- **Onboarding gets harder without a documented shape.** A new
  contributor to a small project can just read all of it. Nobody reads
  all of a large one — they need the architecture itself (named layers,
  documented boundaries) to tell them where to look.

The throughline: **architecture styles are fundamentally about deciding,
in advance, what's allowed to depend on what.** A small project can get
away with not deciding, because there isn't enough code yet for the lack
of a decision to actually hurt. Every style below is a different answer
to that same underlying question, trading flexibility for structure in
different amounts and in different places.

## The styles

### Monolith

One codebase, one deployable unit. This is the default, and — contrary
to its reputation — usually the *correct* starting point, not a mistake
to avoid. Everything runs in one process, so cross-cutting changes are a
single commit, there's no network between components to add latency or
failure modes, and there's exactly one thing to build, test, and deploy.
The downside only shows up at scale: as the codebase and team grow, a
monolith with no *internal* structure becomes a single tangled blob where
everything can reach everything, builds get slow, and independent teams
keep stepping on each other. The fix for that is usually **internal**
structure (the layered/hexagonal/clean styles below, applied *inside* the
one deployable), not necessarily splitting into separate services — see
"How to choose" at the bottom.

- [Martin Fowler — MonolithFirst](https://www.martinfowler.com/bliki/MonolithFirst.html) — the canonical argument for starting here even when you expect to outgrow it.

### Layered (N-Tier) architecture

Code is split into horizontal layers — typically presentation → business
logic → data access — where each layer may only call the layer directly
below it, never skip one, never call upward. Extremely common in
traditional enterprise applications, and easy to explain to a new hire.
The recurring failure mode: layers tend to get "leaky" over time without
discipline (business rules quietly creeping into the presentation layer
because it was faster that day), and a single "business logic" layer can
itself silently become an undifferentiated monolith internally, just one
layer removed from the mess it was meant to prevent.

### MVC, MVP, and MVVM

Three closely related answers to one specific question — how do you
structure the code *behind a UI* — that get confused with each other
constantly:

- **MVC (Model-View-Controller)** — the Controller receives input and
  updates the Model; the View can read the Model directly to render
  itself. Simple, widely taught, but the View's direct dependency on the
  Model makes the View harder to unit test in isolation.
- **MVP (Model-View-Presenter)** — the View never touches the Model
  directly; the Presenter mediates every interaction between them. This
  makes the View trivially fake-able in tests (it's reduced to "receive
  instructions from the Presenter, display them"), at the cost of the
  Presenter needing an explicit reference to the View.
- **MVVM (Model-View-ViewModel)** — the ViewModel exposes observable
  state, and the View *binds* to it (typically via a framework's data
  binding, rather than by being told what to do explicitly). This is
  what most modern UI frameworks lean toward (WPF, SwiftUI, Vue, React's
  hooks are all recognizably MVVM-shaped), at the cost of a steeper
  learning curve around the binding mechanism itself.

- [Martin Fowler — GUI Architectures](https://www.martinfowler.com/eaaDev/uiArchs.html) — the deep, canonical treatment of this entire family (MVC, MVP, Presentation Model, and more), written by someone who traced their actual history.

### Hexagonal architecture (Ports & Adapters)

Already covered in depth in `ARCHITECTURE.md` — this project's own
`natural_mouse` (the core) plus `main.py`/`gui/app.py` (two adapters) is
a working, if small, example of this style: a core that knows nothing
about how it's driven, with separately swappable "adapters" translating
different kinds of input into calls against that same core. Generalizes
past UI adapters specifically — a database, a message queue, a test
double are all just different adapters plugged into the same ports.

- [Alistair Cockburn — Hexagonal Architecture (the original article)](https://alistair.cockburn.us/hexagonal-architecture)

### Clean Architecture

Uncle Bob's (Robert C. Martin's) generalization of the same underlying
idea as hexagonal architecture, usually drawn as concentric circles
(entities → use cases → interface adapters → frameworks/drivers). The one
rule that matters: **the Dependency Rule** — source code dependencies may
only point inward, toward the business logic, never outward toward a
framework or a database. A controller can depend on a use case; a use
case must never depend on a controller, or on a specific database
library. This is the same Dependency Inversion this project already uses
at a small scale (`UIAutomator` depending on abstractions, never on
`Win32InputExecutor` directly), generalized to an entire large
application's worth of layers.

- [Robert C. Martin — The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

### Event-driven architecture

Components communicate by publishing and reacting to events rather than
calling each other directly — a producer doesn't know or care who (if
anyone) is listening. Martin Fowler breaks this umbrella term into four
genuinely distinct patterns worth knowing apart: **event notification**
(a lightweight "something happened" ping), **event-carried state
transfer** (the event carries enough data that the receiver doesn't need
to call back for more), **event sourcing** (every state change is stored
as an event, and current state is derived by replaying them — the event
log itself becomes the source of truth), and **CQRS** (splitting the
component that handles writes from the component(s) that handle reads).
The appeal is real decoupling and independent scalability; the real cost
Fowler himself names is losing any single place that shows "what happens
when X occurs" — that behavior is now scattered across every listener,
which makes a system's overall behavior much harder to trace and debug.

- [Martin Fowler — The Many Meanings of Event-Driven Architecture (GOTO 2017)](https://www.youtube.com/watch?v=STKCRSUsyP0)

### Service-Oriented Architecture (SOA) and microservices

**SOA** is the older, heavier-weight ancestor: independent services
communicating over a network, often through a centralized "enterprise
service bus" that handles routing, transformation, and orchestration
between them. **Microservices** is the leaner modern descendant: small,
independently deployable services, each typically owning its own data,
communicating directly (often over plain HTTP/REST or lightweight
messaging) rather than through a heavy central bus. The genuine payoff is
independent scaling, independent deployment, and clear team ownership
boundaries enforced by an actual network boundary, not just a folder.
The genuine cost is that you've traded in-process function calls for
network calls — meaning the CAP theorem, idempotency concerns, and
general distributed-systems complexity (`PROGRAMMING_ROADMAP.md` §1.7)
are now unavoidably part of your everyday problem, not an edge case.

- [Martin Fowler & James Lewis — Microservices](https://martinfowler.com/articles/microservices.html)

### Serverless (Function-as-a-Service)

Deploy individual functions; the cloud provider handles provisioning,
scaling, and availability entirely, and you're billed per invocation
rather than for an always-on server. Genuinely excellent fit for
spiky, event-driven workloads (a function that only runs when a file
lands in a bucket) where paying for idle capacity would be wasteful. The
tradeoffs: "cold start" latency on a function that hasn't run recently,
real difficulty testing the full system locally (much of its behavior is
defined by how the cloud provider's infrastructure wires functions
together), and a meaningful degree of vendor lock-in once a system leans
on a specific provider's event/trigger model.

- [AWS — What is Serverless Computing?](https://aws.amazon.com/what-is/serverless-computing/)

### Monorepo vs. polyrepo

A different axis entirely from the styles above — this is about how
source code is *organized across repositories*, not how a single
system's internals are structured, but it's a decision every large,
multi-project effort has to make. **Monorepo**: every project/service
lives in one repository. Cross-cutting changes (touching a shared library
and every consumer of it) can be one commit; tooling and standards are
naturally shared. The cost is that the repository and its build/CI
tooling need real investment to stay fast as it grows — without that
investment, "check out the repo" and "run CI" both get slow for everyone,
for every change, regardless of which project it touched. **Polyrepo**:
one repository per project/service. Clean isolation, independent access
control, simple per-project CI — at the cost of any cross-cutting change
needing multiple coordinated PRs across multiple repos, and shared
tooling/standards tending to drift apart over time without deliberate
effort to keep them aligned.

- [Sourcegraph — Monorepo vs Polyrepo: How to Choose](https://sourcegraph.com/blog/monorepo-vs-polyrepo)

## How to choose

The single most common real-world mistake isn't picking the "wrong" style
— it's reaching for a heavyweight one (microservices, in particular)
*before* a project has actually earned it. Fowler's own observation
(`MonolithFirst`, linked above): almost every successful microservices
system he'd seen started life as a monolith that grew large enough to
justify the split, while teams that started with microservices from day
one — before they even knew where the real boundaries in their domain
were — routinely got into serious trouble. The practical default: start
as a monolith with real *internal* structure (layered, or hexagonal/clean
— pick one and actually enforce it), and only pay the network-boundary
cost of splitting into separate services once a specific, concrete
scaling or team-ownership problem demands it, not preemptively because it
sounded more "proper."
