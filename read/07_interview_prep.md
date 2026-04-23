# Interview Prep — AML Questions You'll Be Asked

> When you interview for a financial crime tech role,
> expect a mix of domain questions and technical questions.
> This document prepares you for both.

---

## Domain questions

### "Walk me through a SAR filing."
Answer structure:
1. Detection: system flags suspicious activity (explain your rules + graph approach)
2. Level 1 review: analyst reviews the queue, investigates account detail
3. Level 2 escalation: investigator does deeper analysis (subpoenas, external data)
4. SAR filing: MLRO signs and submits to FinCEN via BSA e-filing system
5. 30-day deadline from detection, 60 days if no suspect
6. Confidentiality: bank CANNOT notify the subject (tipping off is a crime)

### "What's the difference between KYC and AML?"
- KYC (Know Your Customer): verifying WHO opens an account (done at onboarding)
- AML (Anti-Money Laundering): monitoring WHAT the account does (ongoing)
- Both are part of the BSA/AML compliance program
- Your system does transaction monitoring (the AML part)

### "What is the false positive rate problem?"
- Legacy rule-based systems flag 95-99% false positives
- Analysts review 1,000 alerts to find 10 real cases
- Alert fatigue: analysts stop reading carefully
- Your solution: weighted scoring with evidence strings, so analysts prioritize better
- Evaluation: track FPR per rule, tune weights accordingly

### "Why use graph analysis for AML?"
- Individual account analysis is blind to relationships
- Layering uses multiple accounts — looks innocent individually
- Graph reveals the flow pattern across accounts
- PageRank finds central accounts (funnels)
- Community detection finds isolated clusters (shell companies)
- Cycle detection finds round-tripping

---

## Technical questions

### "How would you scale this to 1 billion transactions?"
Current (portfolio):
- NetworkX in-memory, 100k transactions, runs in seconds

At scale:
- Replace NetworkX with GraphX (Spark) or AWS Neptune
- Replace SQLite with Postgres or Redshift
- Run detection as a Spark streaming job (Flink/Kafka)
- Use approximate algorithms: sketch-based cycle detection, approximate PageRank
- Shard accounts by branch/geography for parallelism

### "How would you handle real-time detection?"
Current: batch pipeline, runs daily.
Production options:
- Rule-based: run structuring/velocity rules in real-time as transactions arrive
- Graph-based: refresh nightly (graph signals are expensive to compute in real-time)
- ML layer: a lightweight model (logistic regression on rule outputs) for real-time scoring

### "How do you evaluate your detection system?"
Your answer:
- Ground truth: we generated the data, so we know which accounts are dirty
- Metrics: Precision@K (what fraction of top-K are actually dirty?)
- Recall@K (what fraction of all dirty accounts appear in top-K?)
- AUC-ROC: overall discrimination ability
- Per-typology recall: which patterns are we catching vs. missing?
- Per-rule FPR: which rules generate the most noise?

### "What would you do if your structuring rule had 90% false positive rate?"
1. Look at the dismissed cases — what's the common explanation? (Maybe salary patterns?)
2. Add an exclusion: if the account shows regular salary deposits matching a known employer, reduce score
3. Tune the threshold: require 7 deposits instead of 5
4. Add a "known legitimate" account list (suppression list)
5. Add context signals: is the account new? (new accounts structuring = worse)

### "How is this different from a real bank's AML system?"
Real bank differences:
- Scale: millions of transactions per day, not 100k total
- Real data: messy, missing fields, inconsistent formatting
- External data: sanctions lists, negative news, beneficial ownership
- Real-time requirements: some rules run in milliseconds
- Regulatory reporting: actual FinCEN integration
- Model governance: model validation, approval process, change control
- Data privacy: customer data is highly regulated

Your system demonstrates:
- The CONCEPTS are right (typologies, rules, graph, scoring, evidence, dispositions)
- The ARCHITECTURE is sound (pipeline → scoring → API → dashboard)
- You understand the DOMAIN (SAR workflow, false positive problem, evaluation)

---

## Portfolio talking points

1. "I implemented 6 typologies from FATF reports with realistic parameter ranges."
2. "I combined rules-based and graph-based detection — neither alone is sufficient."
3. "The scoring engine produces human-readable evidence strings, not just numbers."
4. "I evaluated against ground truth using Precision@K and Recall@K."
5. "I tracked false positive rate per rule to show I understand the operational pain."
6. "The disposition workflow mirrors what real analysts do at banks."
