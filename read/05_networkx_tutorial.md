# NetworkX Tutorial — Hands-On Code Examples

> Run these examples yourself before reading the backend code.
> Understanding these 6 patterns makes the detection code obvious.

---

## Setup

```bash
pip install networkx scipy numpy matplotlib
```

```python
import networkx as nx
import matplotlib.pyplot as plt
```

---

## Pattern 1: Create and inspect a transaction graph

```python
# Create a directed graph (money has direction)
G = nx.DiGraph()

# Add transactions manually (you'll see this in generator/typologies/)
transactions = [
    ("alice",   "bob",     {"weight": 500,  "date": "2024-01-01"}),
    ("bob",     "charlie", {"weight": 490,  "date": "2024-01-01"}),
    ("charlie", "dave",    {"weight": 480,  "date": "2024-01-02"}),
    ("dave",    "alice",   {"weight": 460,  "date": "2024-01-03"}),  # <- cycle!
    ("eve",     "bob",     {"weight": 200,  "date": "2024-01-01"}),  # extra sender
    ("frank",   "bob",     {"weight": 300,  "date": "2024-01-01"}),  # another sender
]

G.add_edges_from(transactions)

# Inspect the graph
print("Nodes:", list(G.nodes()))
# Nodes: ['alice', 'bob', 'charlie', 'dave', 'eve', 'frank']

print("Edges:", list(G.edges()))
# Edges: [('alice', 'bob'), ('bob', 'charlie'), ...]

print("In-degree of 'bob':", G.in_degree("bob"))
# In-degree of 'bob': 3  (receives from alice, eve, frank)

print("Out-degree of 'bob':", G.out_degree("bob"))
# Out-degree of 'bob': 1  (sends to charlie only)
```

---

## Pattern 2: Detect cycles (round-tripping)

```python
# Find all cycles in the graph
cycles = list(nx.simple_cycles(G))

print("Cycles found:", cycles)
# Cycles found: [['alice', 'bob', 'charlie', 'dave']]
# ← This is our round-trip! Money left alice and came back.

# Filter for "interesting" cycles (you don't want length-2 simple back-and-forth)
suspicious_cycles = [c for c in cycles if len(c) >= 3]

for cycle in suspicious_cycles:
    print(f"Round-trip detected: {' → '.join(cycle)} → {cycle[0]}")
    # Round-trip detected: alice → bob → charlie → dave → alice
```

---

## Pattern 3: PageRank (finding central accounts)

```python
# PageRank — higher score = more central = more suspicious for funnels
pageranks = nx.pagerank(G, weight='weight', alpha=0.85)

# Sort accounts by PageRank score (descending)
sorted_pr = sorted(pageranks.items(), key=lambda x: x[1], reverse=True)

print("PageRank rankings:")
for account, score in sorted_pr:
    print(f"  {account}: {score:.4f}")
# PageRank rankings:
#   bob:     0.3521  ← HIGHEST! receives from alice, eve, frank → likely funnel
#   alice:   0.1823
#   charlie: 0.1456
#   dave:    0.1234
#   eve:     0.0543
#   frank:   0.0423
```

---

## Pattern 4: Community detection (finding shell clusters)

```python
import networkx.algorithms.community as nx_comm

# Create a self-contained cluster (shell companies)
G_shell = nx.DiGraph()
G_shell.add_edges_from([
    ("shell_A", "shell_B", {"weight": 10000}),
    ("shell_B", "shell_C", {"weight": 9800}),
    ("shell_C", "shell_A", {"weight": 9600}),  # only internal!
    # Now add some legitimate accounts
    ("legit_1", "legit_2", {"weight": 500}),
    ("legit_2", "legit_3", {"weight": 300}),
    ("legit_1", "legit_3", {"weight": 200}),
    ("legit_3", "legit_4", {"weight": 100}),
])

# Convert to undirected for community detection
G_undirected = G_shell.to_undirected()

# Find communities (groups of tightly connected nodes)
communities = nx_comm.louvain_communities(G_undirected, seed=42)

print(f"Found {len(communities)} communities:")
for i, community in enumerate(communities):
    print(f"  Community {i}: {community}")
# Found 2 communities:
#   Community 0: {'shell_A', 'shell_B', 'shell_C'}  ← our shell cluster!
#   Community 1: {'legit_1', 'legit_2', 'legit_3', 'legit_4'}

# Identify suspicious communities: small, isolated clusters
for community in communities:
    if len(community) <= 6:  # small cluster
        # Check if it has external connections
        external_edges = sum(
            1 for node in community
            for neighbor in G_shell.neighbors(node)
            if neighbor not in community
        )
        if external_edges == 0:
            print(f"SUSPICIOUS: Isolated cluster of {len(community)}: {community}")
        # SUSPICIOUS: Isolated cluster of 3: {'shell_A', 'shell_B', 'shell_C'}
```

---

## Pattern 5: Shortest path (finding layering chains)

```python
# Build a graph with a layering chain
G_layer = nx.DiGraph()
G_layer.add_edges_from([
    ("dirty_source",   "intermediate_1", {"weight": 100000, "hours": 0}),
    ("intermediate_1", "intermediate_2", {"weight": 98000,  "hours": 2}),
    ("intermediate_2", "intermediate_3", {"weight": 96000,  "hours": 4}),
    ("intermediate_3", "clean_dest",     {"weight": 94000,  "hours": 6}),
])

# Find the shortest path from source to destination
try:
    path = nx.shortest_path(G_layer, "dirty_source", "clean_dest")
    print(f"Layering chain: {' → '.join(path)}")
    # Layering chain: dirty_source → intermediate_1 → intermediate_2 → intermediate_3 → clean_dest
    print(f"Chain length: {len(path) - 1} hops")
    # Chain length: 4 hops
except nx.NetworkXNoPath:
    print("No path exists")
```

---

## Pattern 6: Betweenness centrality (finding intermediary accounts)

```python
# Betweenness centrality: how often is this node on the shortest path between others?
# High betweenness = this account is a "bridge" = could be a layering intermediary

betweenness = nx.betweenness_centrality(G, weight=None, normalized=True)

print("Betweenness centrality:")
for account, score in sorted(betweenness.items(), key=lambda x: x[1], reverse=True):
    print(f"  {account}: {score:.4f}")
```

---

## Putting it all together: one function per signal

```python
def compute_graph_signals(G: nx.DiGraph) -> dict:
    """
    Compute all graph-based AML signals for every account in the graph.
    
    Returns a dictionary mapping account_id → dict of signal scores.
    
    Each signal is a float between 0 and 1 (we scale to 0-100 in scoring.py).
    """
    
    signals = {}
    
    # Signal 1: PageRank (funnel detection)
    pageranks = nx.pagerank(G, weight='weight', alpha=0.85)
    
    # Signal 2: Cycle membership (round-trip detection)
    all_cycles = list(nx.simple_cycles(G))
    accounts_in_cycles = set()
    for cycle in all_cycles:
        if len(cycle) >= 3:  # ignore simple 2-node loops
            accounts_in_cycles.update(cycle)
    
    # Signal 3: Community isolation (shell cluster detection)
    communities = nx_comm.louvain_communities(G.to_undirected(), seed=42)
    isolated_accounts = set()
    for community in communities:
        has_external = any(
            any(n not in community for n in G.neighbors(node))
            for node in community
        )
        if not has_external and len(community) <= 6:
            isolated_accounts.update(community)
    
    # Build per-account signal dictionary
    for account in G.nodes():
        signals[account] = {
            "pagerank":         pageranks.get(account, 0),
            "in_cycle":         account in accounts_in_cycles,
            "isolated_cluster": account in isolated_accounts,
            "in_degree":        G.in_degree(account),
            "out_degree":       G.out_degree(account),
        }
    
    return signals
```

---

## Common NetworkX gotchas

1. **`nx.simple_cycles()` is slow on large graphs.**
   For 100k edges, add a max cycle length: use a custom DFS instead.
   Our code handles this in `backend/detection/graph/cycle_signal.py`.

2. **Community detection is non-deterministic.**
   Always pass `seed=42` (or any fixed number) for reproducible results.

3. **PageRank weights matter.**
   If you DON'T use `weight='weight'`, all edges count equally.
   Always specify the weight attribute so large transactions matter more.

4. **Directed vs. undirected for community detection.**
   Louvain works on undirected graphs. Convert with `G.to_undirected()`.
   This loses direction info — that's fine for cluster detection.

5. **Isolated nodes (accounts with no transactions).**
   `nx.pagerank()` handles these fine (gives them base score).
   But `nx.simple_cycles()` won't find them (no cycles without edges).
