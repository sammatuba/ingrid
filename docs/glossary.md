# Glossary

One word for each idea. The pages for people use only these words. The last column gives the
name you will meet in the code, the task files and the older records. When two names exist, the
first column wins on every page for people.

## The grid and the market

| Word | Meaning | Name in code and records |
|---|---|---|
| Grid | The network of power plants, lines and consumers. The Philippines has three grids: Luzon, Visayas and Mindanao. | grid, region |
| Demand | The total power that consumers use at one moment, in megawatts (MW). | demand, load |
| Reserve | Spare power above demand that the operator keeps ready for surprises. | reserve, reserve condition |
| Price | The market price of power at one place and one time, in pesos per megawatt-hour. | LMP, locational marginal price |
| WESM | The Wholesale Electricity Spot Market. It records the price and the schedule of every plant every five minutes. | WESM, `rtd_prices_and_schedules` |
| NGCP | The National Grid Corporation of the Philippines. It operates the grid and posts notices when something happens. | NGCP, system operator, SO |
| Advisory | A short notice from NGCP. Example: "PEDC Unit 2 tripped at 13:34." | advisory, operator message |
| Trip | A sudden shutdown of a power plant unit. | trip, forced outage |
| Yellow alert | The operator's warning that the reserve is low. | yellow alert |
| Load dropping | The operator cuts supply to some areas for a short time to protect the grid. | MLD, manual load dropping |
| Undersea link | A direct-current cable that joins two grids. One joins Luzon and Visayas. One joins Visayas and Mindanao. | HVDC, `VISLUZ1`, `MINVIS1` |
| Register | The official list of plants and the power each unit can supply. | capacity register, IEMOP register, register run |
| Plant site | One place with one or more generating units. The site has a code such as `08PEDC`. | site, site code, resource |

## The review method

| Word | Meaning | Name in code and records |
|---|---|---|
| Outlook | A forecast of supply, demand or prices that an analyst writes and signs. | outlook, outlook head |
| Assumption | One fact that an outlook depends on. Example: "PEDC Unit 2 can supply 83.7 MW on 21 September." | assumption, accepted position, seed |
| Evidence | A source, the passage in it, and the time it became known. | evidence, passage, source version |
| Cutoff time | The moment the desk stops reading new evidence for one judgment. The desk judges each case twice: just before and just after a new advisory. | information cutoff, T0, T1, cutoff pair |
| Question set | Eight short questions that the AI model answers about one piece of evidence and one assumption. Each question comes in four presentation forms. | probe bundle, bundle v5, Q1 to Q8 |
| Judgment | The AI model's answers to the question set, with citations, and the label the desk builds from them. | judgment, JudgmentArtifact, composed answer |
| Label | The result of a judgment. One of: supports, challenges, mixed, unrelated, not enough evidence. | composed label, `supports`, `challenges`, `mixed`, `unrelated`, `insufficient` |
| Stability record | A note that says if the model gave the same top answers in all four presentation forms. Two or more different answers out of four make the judgment unstable. | stability receipt, flip rate, receipt |
| Decision | The analyst's choice after a judgment: keep the assumption, change it, or open it for review. A kept assumption with a reason counts as success. | review decision, disposition, retain, revise |
| History | The saved list of decisions on one case, in time order. | history, outlook revisions |
| Case | One event, its evidence, the assumption it touches, the judgments and the decisions. | case, case pack |
| The PEDC case | Our one real case. PEDC Unit 2 in Visayas tripped at 13:34 on 21 September 2026 and came back at 15:07. | `pedc-u2-2026-09-21`, EVAL-5 |
| Recorded run | Gemini answered the question set once, on 14 October 2026, and we saved the answers. The site shows the saved answers. | live run record, stored run, `live-run-2026-10-14.md` |
| Replay | The site shows recorded data from September 2026 and moves a clock through it. Nothing is live. | replay, as-of time, replay clock |
| Visitor | Anyone who opens the site. The site gives each visitor a private copy of the case on the first action. It needs no sign-in. | judge, anonymous judge, anonymous user |
| Own copy | The visitor's private copy of the case. A decision saved there changes no one else's copy. | sandbox, judge case, tenant |
| Data build | A script turns the September data into files that the site can show. | bake, `build/grid-data`, `scripts/grid/build_data.py` |
| Permission record | The owner's signed note that allows the company data on the demo site. The data never goes into Git. | `perm:wesm-company-copy:2026-10-13`, version 2 |
| Public export | The copy of the repository that we may publish. It leaves out the company data and the internal records. | export, allowlist, REL-5 |

## Where it runs

| Word | Meaning | Name in code and records |
|---|---|---|
| Gemini | Google's AI model. The project used the model `gemini-3.8-flash`. | Gemini, Vertex Gemini |
| Vertex AI | Google Cloud's service for running AI models. | Vertex AI, transport |
| Cloud Run | Google Cloud's service that runs the app server. It starts a server when a visitor arrives and stops it when nobody is there. | Cloud Run, service `grid-nowcast`, Singapore |
| App server | The program that serves the event page and saves decisions. Its language is Python. | API, `src/api`, FastAPI |
| Firebase Hosting | Google's service that serves the site's files fast from a location near the visitor. It sits in front of Cloud Run. | Hosting, `web.app`, CDN |
| Firestore | Google's database. It holds the cases, the decisions and the histories. | Firestore, repository, collection |
| Sign-in service | Google's service that gives each visitor a private identity without a password. | Firebase Auth, anonymous auth, Identity Toolkit |
| Cold start | The delay when a visitor arrives and no app server is running. Google starts one. It took about 7 seconds in our tests. | cold start, instance start, PERF-0 |
| Version (of the app) | One deployed build of the app server. Each has a code such as `00010-66b`. | Cloud Run revision, image digest |
| Deploy | Put a new version of the app on Google Cloud. Only the owner does this, and only once per batch of work. | deploy, `scripts/deploy/deploy.sh` |
| Fingerprint | A short code computed from a file's bytes. Two equal fingerprints mean two identical files. | digest, sha256, checksum |
| Container image | The packed copy of the app server that Cloud Run runs. | image, Dockerfile, Artifact Registry |

## How we work

| Word | Meaning | Name in code and records |
|---|---|---|
| Task | One unit of work with an ID such as `PERF-3`. It lists the files it may change, its acceptance checks and a verify command. | task, `tasks.json`, brief |
| Task record | The file that holds a task's commands, results and decisions. | packet, implementation record |
| Work area | A group of tasks with the same ID prefix, such as `PERF`. | lane |
| Owner approval | An input that only the owner can give, such as the rights to publish. | gate, `GATE-5` |
| Plan note | The written plan for a change, made before the code. | intent, `intent.md` |
| Fixed rule | A data format or a rule that no task may change without a new plan note. | frozen contract |
| Review | An independent check of a task before it merges. The author never reviews their own task. | review, review record, `docs/work/reviews/` |
| Role | Who or what does one kind of work: the owner, the teammate, or one of the AI helpers. | seat |
| Owner | Sam. Decisions, approvals, deploys, money and the submission. | owner |
| Teammate | Ericka. The data foundation and the first replay dashboard. | teammate |
| Coordinator AI | Claude in Claude Code. It picks tasks, writes briefs, runs checks and merges on the owner's word. | orchestrator, orchestrator seat, Claude Opus 5.5 |
| Builder AI | DeepSeek. It builds one task at a time on its own branch. | executor, executor seat, DeepSeek V4.1 Flash |
| Reviewer AI | GPT Sol through Codex. It reads a task and answers accept or rework. | reviewer, reviewer seat, `gpt-6.1-sol` |
| Strategy reviewer | Claude Fable. It checks big decisions and the fixed rules. | guardian, guardian seat |
| Branch | A named line of changes in Git. Each task has one, `task/<ID>`. The shared line is `main`. | branch, integration line, `feat/h1-api-persistence` |
| Work copy | A second folder with the same repository on another branch. | worktree, `.local/wt/<ID>` |
| Local service copy | A program that imitates Firestore or the sign-in service on your computer, for tests. | emulator, `scripts/h1/test.sh` |
| Test data | Made-up or recorded data that the tests use. | fixture, `tests/fixtures/` |
| Repository check | The command that checks links, routes, word budgets and plain language. | `scripts/repo.py check` |
| Plan check | The command that checks the task graph and the task states. | `scripts/plan.py check` |

## The ideas

| Word | Meaning | Name in code and records |
|---|---|---|
| Belief | Something the desk treats as true until evidence changes it. The desk's word for it is an assumption. | belief, assumption, accepted position |
| Claim | What a source says, kept apart from what the desk has checked. | claim, reported claim |
| Forecast | What the desk expects to happen, with its inputs and the moment someone made it. The desk's word for it is an outlook. | forecast, outlook, position |
| Outcome | What actually happened, once the month has settled. The desk's word for it is the settled month. | outcome, settlement, scoring receipt |
| Impact | What a change would cost or save, in the units the company counts in, such as pesos. | impact, exposure, materiality line |
| Presentation form | One of four ways to show the same question in one request. One form changes the option order, or negates a yes-or-no question. One numbers the options of a choice question, and one reverses the passages. No form rephrases the question. | perturbation, form, flip rate, polarity gap |
| Known-at time | The earliest time the desk could read a fact. A stamp from the source backs it, or a named assumption does. | known-at, first availability, A-RT, A-RUN, A-FUEL |
| Evidence grade | How strong the evidence behind a figure is: measured, demonstrated, implemented, specified or absent. | evidence grade, status word |
| Driver card | The conditions present at one time and place, each with the time it became known, ranked by how unusual each was. It names no cause. | driver card, likely drivers, ranking |
