# Research Literature Agent
Public PubMed metadata only; never supply patient data.
## Operation
GitHub Actions runs Fridays at 13:00 UTC (08:00 EST, 09:00 EDT), and can be triggered manually.
The job searches PubMed E-utilities, writes `data/literature_digest.json`, and opens a pull request for human review. Merge the PR to publish at `research_literature.html`.
Configure repository variable `NCBI_EMAIL` with a valid contact address. In GitHub Actions settings, enable workflows to create pull requests. Review branch protection and the workflow's write permissions. Do not store API keys in source code.
This initial release retrieves abstracts and bibliographic metadata; it does not claim to perform full-text critical appraisal or AI-generated evidence synthesis.
The job uses a fixed 10-day Entrez-indexing lookback; repeated records can appear across runs. A future release can track historical PMIDs and introduce relevance review.
Schedule uses UTC and does not shift automatically for daylight saving time.
