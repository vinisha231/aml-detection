# Reading Guide 17 — Advanced Graph Analysis for Financial Crime Detection

## Why graph analysis outperforms rule-based detection alone

Rule-based detection examines each account in isolation. An account that structures
deposits is flagged. An account that has high velocity is flagged. But what about
an account that does *nothing suspicious by itself* — it simply sits in the middle
of a network where every account around it is suspicious?

Graph analysis finds these "connector" accounts that are structurally important
to the laundering network but would never trigger a simple threshold rule.

---

## PageRank — measuring influence in a directed graph

PageRank was invented by Google to rank web pages. In a transaction network:

- **Nodes** = accounts
- **Edges** = money flows (directed: from sender to receiver)
- **Edge weight** = total amount transferred

PageRank answers: "Which accounts receive the most money from the most influential
accounts?" In the web analogy, a page is important if important pages link to it.
In AML, an account is important if important accounts send money to it.

### Why PageRank matters for AML

Legitimate high-volume accounts (payroll processors, large retailers) also have
high PageRank. But they receive money from *many different unrelated sources*.

Money laundering networks tend to route funds toward a small number of exit
points — the accounts that cash out or invest the proceeds. These exit accounts
have very high PageRank within the suspicious subgraph.

### PageRank formula

```
PR(A) = (1 - d) / N  +  d × Σ(PR(B) / out_degree(B))
```

Where:
- `PR(A)` = PageRank of account A
- `d` = damping factor (0.85 is standard — models the probability of following a link)
- `N` = total nodes
- Sum is over all accounts B that send money to A
- `out_degree(B)` = total accounts B sends to (normalizes B's influence)

NetworkX implementation: `nx.pagerank(G, weight='weight', alpha=0.85)`

---

## Community Detection — finding clusters of related accounts

### The Louvain algorithm

Louvain community detection finds groups of nodes that are more densely connected
to each other than to the rest of the network. It optimizes a measure called
**modularity**:

```
Q = (1/2m) × Σ[A_ij - (k_i × k_j)/2m] × δ(c_i, c_j)
```

Where `A_ij` is edge weight, `k_i` is node degree, `m` is total edge weight,
and `δ` is 1 if nodes i and j are in the same community.

### What communities reveal in AML

**Healthy network**: Accounts cluster naturally by geography, business type, or
social circle. A payroll company sends to hundreds of employees — they're a hub,
but not a criminal hub.

**Money mule network**: A group of 10–30 accounts that heavily transact among
themselves but have very few connections to the wider network. Funds enter from
one source and exit to one destination. This closed-loop structure creates a
tightly-knit community.

**Shell company cluster**: Multiple entities at the same registered address, sharing
the same beneficial owner, transacting in circles to create the appearance of
business activity. They form an isolated community with suspicious circular flows.

### Implementation in Python

```python
import networkx.algorithms.community as nx_comm

# Convert to undirected for community detection (Louvain works on undirected graphs)
G_undirected = G.to_undirected()

# Run Louvain algorithm
communities = nx_comm.louvain_communities(G_undirected, seed=42)

# communities is a list of sets: [{node1, node2, ...}, {node3, node4, ...}, ...]
for i, community in enumerate(communities):
    print(f"Community {i}: {len(community)} members")
```

---

## Cycle Detection — finding circular fund flows

### What is a cycle in a transaction graph?

A cycle is a path through the graph that starts and ends at the same node:
`A → B → C → A`

In legitimate finance, this almost never happens. Money flows in one direction:
from income sources → personal accounts → expenses. The concept of "paying yourself"
through multiple intermediaries has no legitimate purpose.

### Why cycles indicate money laundering

**Round-tripping**: A company sends $100k to a subsidiary, which sends $80k to a
"consultant" (which is actually the original company). The $80k comes back appearing
as "consulting revenue" — a legitimate-looking income that's actually the original
funds laundered.

**Wash trading**: In securities markets, buying and selling to yourself to create
the appearance of activity. The transaction graph shows cycles.

**Integration stage**: In the final stage of laundering, cleaned money is returned
to the original criminal through apparently legitimate channels — creating cycles.

### Finding cycles with NetworkX

```python
# Find all simple cycles (no repeated nodes)
# WARNING: This is exponential in the number of cycles — use carefully on large graphs
cycles = list(nx.simple_cycles(G))

# For large graphs, find if any cycles exist (faster)
try:
    nx.find_cycle(G)
    has_cycle = True
except nx.NetworkXNoCycle:
    has_cycle = False
```

### The cycle detection challenge

Real graphs can have millions of cycles. Our implementation:
1. Checks if cycles exist at all (fast)
2. Finds short cycles (length 2–6) involving high-value transactions
3. Scores accounts participating in cycles by cycle length and value

---

## Betweenness Centrality — finding broker accounts

### What is betweenness centrality?

Betweenness centrality measures how often a node lies on the *shortest path*
between other pairs of nodes.

```
BC(v) = Σ(σ_st(v) / σ_st)  for all s ≠ v ≠ t
```

Where `σ_st` = total shortest paths from s to t, and `σ_st(v)` = those paths that
pass through v.

### Why betweenness matters for AML

An account with high betweenness centrality is a **broker** — all communication
(money flow) between different parts of the network flows through it.

Legitimate brokers exist (banks, payment processors), but they're well-known and
expected. An anonymous personal account with high betweenness centrality is a
strong anomaly — it suggests the account is being used as a "pass-through node"
that funnels money between disconnected parts of the laundering network.

### The computational challenge

Computing exact betweenness centrality is O(V × E) using the Brandes algorithm.
For a graph with 10,000 nodes and 50,000 edges, this takes seconds.
For a graph with 1,000,000 nodes, this takes hours.

**Approximation**: Use k random pivot nodes instead of all pairs.
`nx.betweenness_centrality(G, k=200)` is much faster and produces good approximations.

---

## Hub-and-Spoke Detection — identifying money collection points

### The hub-and-spoke pattern

```
Spoke1 ↘
Spoke2  → Hub → Single exit
Spoke3 ↗
```

Multiple accounts (spokes) all send money to a single hub, which then forwards
the aggregated funds to a single exit point. This is the mule network pattern.

### Detection approach

1. Find nodes with high in-degree (many senders) or high out-degree (many receivers)
2. Check if the account handles a disproportionate share of the total network volume
3. Verify that the spokes themselves have low connectivity (not themselves hubs)

### Why this matters

In a legitimate payment network, hubs are recognizable entities (Venmo, PayPal, banks).
An anonymous personal account acting as a hub — receiving from 20 other accounts
and forwarding to a single destination — has no legitimate explanation.

---

## Temporal Graph Analysis — when timing reveals intent

Traditional graph analysis is static: it shows structure, not timing. Temporal
graph analysis adds the time dimension.

### Rapid forwarding detection

For each account, compare:
- Time of incoming transactions (when money arrives)
- Time of outgoing transactions (when money leaves)

If an account consistently forwards received funds within hours, it's acting as
a pure pass-through — consistent with wire layering where speed is essential to
avoid tracking.

```
Rapid forward = |outflow_time - inflow_time| < 6 hours
```

### Synchronized activation

If 10 accounts all make their first-ever transaction on the same day:
- Scenario A (benign): A new business opened and hired employees (paid on day 1)
- Scenario B (suspicious): A criminal opened 10 mule accounts and funded them all at once

Scenario B is identifiable because the new accounts:
1. All start on the same day
2. Are interconnected (transact with each other)
3. Have no other prior history

---

## Combining Graph Signals in the Ensemble

Our system generates one signal per graph algorithm. The ensemble combines them:

| Signal | Detects | Weight |
|--------|---------|--------|
| PageRank | High-influence exit points | 1.2 |
| Community isolation | Shell clusters, mule networks | 1.3 |
| Cycle detection | Round-tripping | 1.5 |
| Betweenness | Pass-through brokers | 1.4 |
| Hub-spoke | Collection hubs, distribution hubs | 1.3 |
| Temporal | Rapid forwarding, synchronized activation | 1.4 |

No single graph signal is conclusive on its own. But when an account scores high
on 3+ graph signals simultaneously, the ensemble's pile-up bonus elevates the
final score significantly — reflecting high confidence that the account is
structurally embedded in a suspicious network.

---

*This concludes the reading materials. Start with 01_fincen_sar_guide.md and work forward.*
