# AML Fundamentals — A Developer's Cheat Sheet

> This is the domain knowledge you need to understand WHY we're building what we're building.
> A good AML engineer understands the business problem, not just the code.

---

## The three-line summary of money laundering

1. Criminals earn money illegally (drugs, fraud, corruption, trafficking).
2. They need to make it look like it came from legal sources.
3. Banks are the gatekeepers — they must detect and report suspicious patterns.

---

## Key actors in AML compliance

| Actor | Role |
|-------|------|
| **Analyst (Level 1)** | Reviews flagged accounts daily, decides to escalate or dismiss |
| **Investigator (Level 2)** | Deep-dives complex cases, files SARs |
| **MLRO** | Money Laundering Reporting Officer — responsible for all SAR filings |
| **FinCEN** | US regulator — receives SARs, shares with law enforcement |
| **FATF** | Sets global standards, evaluates countries |
| **Compliance tech team** | Builds and maintains detection systems (that's us) |

---

## The analyst's daily workflow (what our dashboard replicates)

```
Morning queue loads
    ↓
Analyst sees top-N accounts sorted by risk score
    ↓
Clicks into Account #A1042
    ↓
Reviews transaction history + evidence strings
    ↓
Looks at the graph: who does this account talk to?
    ↓
Decision:
    ├── "This is clearly money laundering" → Escalate to Investigator → SAR filed
    ├── "This is a false positive" → Dismiss + leave note explaining why
    └── "Need more info" → Add to watchlist, revisit tomorrow
```

This is EXACTLY what our dashboard's three screens do:
1. Queue screen = morning queue
2. Account detail = the investigation step
3. Disposition screen = the decision step

---

## False positives — the real-world pain point

**False positive rate** = how often the system flags innocent customers.

This is the most important metric in production AML:

- Too many false positives → analysts waste time, customers get wrongly scrutinized
- Too few flags → criminals slip through, bank faces regulatory fines

Real bank numbers:
- Legacy rule-based systems: 95–99% false positive rate (!)
- Better ML systems: 70–90% false positive rate
- Best-in-class: 30–50% false positive rate

This is why we track false positive rate per rule in our evaluation script.
It tells you WHICH rules are generating noise vs. signal.

---

## The "$10,000 rule" in more depth

The CTR (Currency Transaction Report) threshold is $10,000 per BSA regulation.

BUT — the law also prohibits "structuring to evade" — which means it's illegal to
break up a transaction SPECIFICALLY to stay under the threshold. So the crime isn't
just making deposits over $10k — the crime is intentionally staying under $10k.

This creates a detection challenge: you can't just flag every deposit over $9,000.
You need to look at PATTERNS:
- Frequency (multiple deposits within days)
- Consistency (amounts are suspiciously similar)
- History (account never did this before)

Our structuring rule uses all three signals.

---

## KYC vs. AML — what's the difference?

**KYC** (Know Your Customer) = verifying who someone IS when they open an account.
- Photo ID, proof of address, source of funds declaration
- Happens at onboarding
- Prevents fake accounts

**AML** (Anti-Money Laundering) = monitoring what they DO with the account.
- Transaction monitoring (what our system does)
- Ongoing, real-time or near-real-time
- Catches behavior that looks suspicious regardless of identity

Our system is transaction monitoring — the AML layer, not KYC.

---

## Graph theory in AML — why networks matter

Money laundering almost always involves MULTIPLE accounts. Understanding the
RELATIONSHIPS between accounts reveals patterns that individual account analysis misses.

Example: Account A looks totally clean — normal salary, normal spending.
But Account A is the final destination of a 4-hop chain from a high-risk account.
You'd never catch this looking at Account A alone.

Graph vocabulary for AML:
- **Node** = account
- **Edge** = transaction (directed: money flows from → to)
- **Weight** = transaction amount
- **In-degree** = how many accounts send to this one (funnel detection)
- **Out-degree** = how many accounts this one sends to
- **Centrality** = how "important" a node is in the network (PageRank)
- **Community** = cluster of nodes more connected to each other than outsiders
- **Cycle** = path from A → ... → A (round-tripping)

These are the exact concepts we implement in `backend/detection/graph/`.

---

## Scoring philosophy — why 0–100 with evidence

Pure rule triggers (yes/no) don't help analysts prioritize.
Pure ML black boxes don't help analysts explain decisions.

Our hybrid approach:
- Each signal produces a 0–100 score with an evidence string
- Scores are combined with weights
- Final score tells you HOW suspicious
- Evidence strings tell you WHY

This mirrors how real-world analytical platforms like NICE Actimize, Temenos, and
Oracle FCCM work — hybrid rules+ML with explainability.

---

## Regulatory consequences banks face

Understanding consequences explains why banks invest millions in AML:

| Fine | Bank | Year | Reason |
|------|------|------|--------|
| $1.9B | HSBC | 2012 | Mexican drug cartel laundering |
| $630M | Deutsche Bank | 2017 | "Mirror trading" scheme |
| $185M | Capital One | 2021 | BSA/AML program failures |
| $140M | Signature Bank | 2023 | AML program deficiencies |

Banks pay these fines when their AML programs are inadequate — not necessarily
when they catch every criminal. The standard is "reasonable diligence."

---

## Concepts to understand before our code makes sense

1. **Batch processing vs. real-time**: Our pipeline runs daily (batch). Real systems
   often run in near-real-time (streaming). Batch is fine for a portfolio project.

2. **Ground truth**: Because we generate the data, we KNOW which accounts are dirty.
   This lets us evaluate our detection. In production, ground truth is the eventual
   SAR filing result (but that takes months to know).

3. **Risk score calibration**: A score of 80 should mean "80% of accounts at this
   score are genuinely suspicious." Calibration is hard. We'll do a basic version.

4. **Alert fatigue**: Too many alerts → analysts stop reading them carefully.
   This is the #1 operational problem in AML. Our queue sorts by score so the
   highest-confidence cases are always at the top.
