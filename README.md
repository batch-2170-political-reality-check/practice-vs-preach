# Practice What You Preach: A Political Reality Check

Phase 1 — Summary & Alignment
Generate a topic-level summary of what each party talks about in parliamentary speeches.
Then calculate a Similarity Score showing how closely these speeches align with the party’s official manifesto positions. Goal: Answer the question “What does the party actually talk about — and how close is that to what they promised?”

Depending on complexity of Phase 1, further ideas (not decided on):

Phase 2 — Subtopics & Tonality
Break broad political topics into data-driven subtopics using e.g. clustering (e.g., “CO₂ pricing,” “family reunification,” “hospital financing”)
For each subtopic, classify the tonality/stance expressed in speeches (supportive, critical, conditional, etc.).
Goal: Reveal how parties talk about an issue — not just that they talk about it.

Phase 3 — Quotes & Context
Provide short, contextual speech excerpts that illustrate why a subtopic was assigned a particular tonality.
Each quote includes speaker name, party, date, and a link to the full speech.
Goal: Give users transparent evidence behind the classifications.


## Project Status

**Status**: MVP in progress for Phase 1

**Timeline**: 2 weeks


## Tech Stack

- [Technology 1]
- [Technology 2]
- [Technology 3]
- [etc.]

## Project Structure


**data**: downloaded and renamed manifestos from 2025

**Fetch_PlenaryMinutes**: API call to fetch speeches. Can be adjusted to election period of choice.

**poc_manifesto_summary**: First proof of concept by applying challenge to manifesto texts.

**requirements.txt**: requirements adapted from RAG challenge

**dbtplenarprotokoll_kommentiert**: schema specification for https://www.bundestag.de/services/opendata that defines how all parliamentary debates and their components (who spoke, what they said, reactions, votes, etc.) are structured in machine-readable XML format for the German Bundestag's digital archives.
(for fetching the plenary minutes I have used the API, not the structured xml)

```
pratice-vc-preach/
├── data
│   └── ...
├── notebooks
│   ├── Fetch_PlenaryMinutes.ipynb
│   └── poc_manifesto_summary.ipynb
├── pitchdeck
│   └── practice-vs-preach-pitch-deck.pdf
├── README.md
├── requirements.txt
└── research
│   └── ...
└── resources
    └── dbtplenarprotokoll_kommentiert.pdf
```
