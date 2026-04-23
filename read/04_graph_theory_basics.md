# Graph Theory Basics for AML Developers

> You don't need a math degree. You need enough graph theory to understand
> what NetworkX is doing and why it helps detect money laundering.

---

## What is a graph?

A graph is a way of representing RELATIONSHIPS between things.

```
Things = nodes (also called vertices)
Relationships = edges (also called links or connections)
```

Example — a simple transaction graph:

```
[Alice] --$500--> [Bob] --$490--> [Charlie] --$480--> [Alice]
```

- Alice, Bob, Charlie are NODES
- The $500 transfer is an EDGE from Alice to Bob
- Because edges have direction (money flows one way), this is a DIRECTED graph
- Because edges have amounts, this is a WEIGHTED graph

In our system:
- Every bank account = one node
- Every transaction = one directed, weighted edge

---

## Types of graphs we use

### Directed Graph (DiGraph)
Edges have direction: A → B is different from B → A.
We use this because "$100 from Alice to Bob" is very different from "$100 from Bob to Alice."

```python
# In NetworkX:
import networkx as nx
G = nx.DiGraph()           # "Di" = directed
G.add_edge("Alice", "Bob", weight=500, date="2024-01-01")
```

### Weighted Graph
Edges have numerical values (transaction amounts).
We use weight for: detecting high-value flows, community detection.

---

## PageRank — finding the most "important" accounts

PageRank was invented by Larry Page (Google's co-founder) to rank web pages.
The idea: a page is important if many other important pages link to it.

For AML:
- An account is "central" if many other accounts send money to it
- A funnel account (receiving from 50 senders) gets a high PageRank
- A dormant account with few connections gets a low PageRank

```
PageRank formula (simplified):
PR(A) = (1 - d) + d × Σ PR(i)/out_degree(i)
         ↑ base score    ↑ sum of pageranks of all accounts sending to A
```

Where d = damping factor (usually 0.85). Don't memorize the formula — just know:
**High PageRank = many accounts funnel money here = suspicious.**

```python
# In NetworkX — one line!
pageranks = nx.pagerank(G, weight='weight')
# Returns: {"Alice": 0.003, "Bob": 0.0089, ...}
```

---

## Louvain Community Detection — finding shell clusters

Community detection finds groups of nodes that are MORE connected to each other
than to the rest of the network.

Think of it like finding cliques at a party: groups that only talk to each other.

For AML:
- A shell company cluster of 4 accounts that ONLY transact with each other
- Will form a tight community (all edges internal, no external edges)
- Louvain algorithm finds these communities automatically

```python
# In NetworkX with community module:
import networkx.algorithms.community as nx_comm

# Convert to undirected for community detection
G_undirected = G.to_undirected()
communities = nx_comm.louvain_communities(G_undirected, seed=42)

# communities = [{"Alice", "Bob"}, {"Charlie", "Dave", "Eve"}, ...]
# Each set = one community
```

Suspicious community = small size (3–6 nodes) + no connections to outside.

---

## Cycle Detection — finding round-tripping

A cycle is a path that starts and ends at the same node.

```
Normal:    A → B → C  (no cycle, money flows out)
Suspicious: A → B → C → A  (cycle! money returned to A)
```

For AML:
- Money completing a full circle = round-tripping
- Criminal makes money "look like" it came from a business transaction
- NetworkX has a built-in cycle finder

```python
# Find all simple cycles in the graph
cycles = list(nx.simple_cycles(G))
# Returns: [["Alice", "Bob", "Charlie"], ...]
# Filter for cycles that complete within N days (time-constrained)
```

Challenge: large graphs have MANY cycles. We filter by:
1. Maximum cycle length (≤ 8 hops)
2. Maximum time to complete (≤ 30 days)
3. Minimum amount ($5,000+)

---

## Shortest Path — finding layering chains

Layering moves money through intermediate accounts quickly.

We detect this by finding the SHORTEST PATH between two accounts where:
- The starting account is high-risk (known bad actor, or flagged by rules)
- The ending account is also high-risk
- The path goes through 2+ intermediate accounts

```python
# Find shortest path between two nodes
path = nx.shortest_path(G, source="dirty_account", target="final_dest")
# Returns: ["dirty_account", "intermediate_1", "intermediate_2", "final_dest"]
```

If this path completes within hours, it's a layering chain.

---

## Graph metrics we compute

| Metric | What it measures | AML use |
|--------|-----------------|---------|
| **PageRank** | Global importance | Funnel detection |
| **In-degree** | # of incoming edges | Funnel fan-in |
| **Out-degree** | # of outgoing edges | Funnel fan-out |
| **Betweenness centrality** | How often on shortest paths | Layering intermediaries |
| **Clustering coefficient** | How connected are neighbors? | Shell cluster isolation |
| **Community label** | Which cluster do I belong to? | Shell company grouping |
| **Cycle membership** | Am I in a cycle? | Round-trip detection |

---

## Why NetworkX instead of Neo4j?

Neo4j is a purpose-built graph database — very fast for huge graphs in production.
NetworkX is a Python library — simpler, runs in-memory, no separate database needed.

For our portfolio (5,000 nodes, 100,000 edges):
- NetworkX handles this easily in seconds
- No database setup required
- All analysis is pure Python
- Perfect for demonstrating graph concepts

Switch to Neo4j only if you need:
- Billions of edges (bank scale)
- Real-time queries (< 100ms)
- Persistence across multiple processes

```python
# NetworkX installation
pip install networkx[default]  # includes scipy for fast algorithms

# What "networkx[default]" includes:
# - scipy (fast matrix operations)
# - numpy (numerical operations)
# - matplotlib (graph visualization)
```

---

## Building our transaction graph

```python
import networkx as nx

# Create directed graph (transactions have direction)
G = nx.DiGraph()

# Add each transaction as an edge
for tx in transactions:
    G.add_edge(
        tx['sender_account_id'],      # From this account
        tx['receiver_account_id'],    # To this account
        weight=tx['amount'],          # Transaction amount
        date=tx['transaction_date'],  # When it happened
        tx_id=tx['transaction_id']    # For traceability
    )

# Basic stats
print(f"Accounts (nodes): {G.number_of_nodes()}")
print(f"Transactions (edges): {G.number_of_edges()}")
```

That's it. From here, every graph algorithm is one function call away.

---

## Visualization note

For the dashboard, we use `react-force-graph` (JavaScript) to draw account subgraphs.
NetworkX can also export to formats that JavaScript libraries can read:

```python
# Export to JSON for the frontend
import json
from networkx.readwrite import json_graph
data = json_graph.node_link_data(G)
json.dump(data, open("graph.json", "w"))
```
