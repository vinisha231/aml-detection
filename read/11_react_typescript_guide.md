# 11 — React + TypeScript Guide for This Project

## Why TypeScript Over Plain JavaScript?

TypeScript adds static types to JavaScript. The compiler catches errors before you run the code.

```typescript
// Without TypeScript — crashes at runtime
const account = fetchAccount("ACC_001");
console.log(account.risk_scroe);  // typo! crashes silently

// With TypeScript — caught at compile time
const account: AccountDetail = await fetchAccount("ACC_001");
console.log(account.risk_scroe);  // ❌ ERROR: Property 'risk_scroe' does not exist
                                   // Did you mean 'risk_score'?
```

For a data-heavy dashboard consuming a REST API, TypeScript is invaluable — every API response is typed, so the editor knows exactly what fields exist.

---

## Project Structure

```
frontend/src/
├── api/
│   └── client.ts          # axios instance + all API functions + TypeScript interfaces
├── components/            # Reusable UI pieces
│   ├── Navbar.tsx
│   ├── StatsHeader.tsx
│   ├── FilterBar.tsx
│   ├── ScoreCircle.tsx
│   ├── SignalTimeline.tsx
│   ├── TransactionTable.tsx
│   ├── GraphViewer.tsx
│   ├── RiskBadge.tsx
│   ├── TypologyBadge.tsx
│   ├── SearchBar.tsx
│   ├── LoadingSpinner.tsx
│   └── ErrorBanner.tsx
├── hooks/                 # Custom React hooks
│   ├── useQueue.ts
│   ├── useAccountDetail.ts
│   └── useStats.ts
├── pages/                 # Full page components (routed)
│   ├── QueuePage.tsx
│   ├── AccountDetailPage.tsx
│   └── AnalyticsPage.tsx
├── utils/
│   ├── formatters.ts      # Currency, date, score formatters
│   └── constants.ts       # App-wide constants
├── App.tsx                # Router setup
└── main.tsx               # React DOM entry point
```

---

## Key React Concepts Used

### useState — Local Component State
```typescript
const [loading, setLoading] = useState(true);
const [filters, setFilters] = useState<FilterState>({
  minScore: 0, disposition: 'all', sortAscending: false
});
```

### useEffect — Side Effects and Data Fetching
```typescript
useEffect(() => {
  let cancelled = false;  // prevent stale state updates

  fetchQueue({ minScore, disposition })
    .then(data => {
      if (!cancelled) setAccounts(data.accounts);
    });

  return () => { cancelled = true; };  // cleanup on unmount
}, [minScore, disposition]);  // re-run when these change
```

### useCallback — Stable Function References
```typescript
// Without useCallback — new function on every render → infinite loops in useEffect
const refetch = () => setTrigger(n => n + 1);

// With useCallback — same function identity, safe in dependency arrays
const refetch = useCallback(() => setTrigger(n => n + 1), []);
```

### Custom Hooks — Reusable Stateful Logic
```typescript
// Instead of repeating fetch + loading + error logic in every component:
const { accounts, loading, error, refetch } = useQueue({ minScore: 70 });
```

---

## TypeScript Patterns Used

### Interface Definitions (api/client.ts)
```typescript
export interface AccountSummary {
  account_id:   string;
  holder_name:  string;
  risk_score:   number | null;  // null = not yet scored
  typology:     string | null;
  disposition:  string | null;
}

// Async function with typed return
export async function fetchQueue(params: QueueParams): Promise<QueueResponse> {
  const { data } = await api.get<QueueResponse>('/queue', { params });
  return data;
}
```

### Discriminated Unions
```typescript
type RiskTier = 'critical' | 'high' | 'medium' | 'low';

// TypeScript knows these are the only valid values
const tier: RiskTier = 'critical';
const invalid: RiskTier = 'extreme';  // ❌ Type error!
```

### Generics with useState
```typescript
const [accounts, setAccounts] = useState<AccountSummary[]>([]);
// TypeScript knows setAccounts only accepts AccountSummary[]
```

---

## Tailwind CSS Approach

We use utility classes directly in JSX — no separate CSS files:

```tsx
<div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
  <span className="text-red-400 font-bold text-2xl">{score}</span>
</div>
```

**Why Tailwind?**
- No naming CSS classes (no `.riskScoreCard` vs `.risk-score-card` debates)
- All styling co-located with the component (easier to understand)
- Purges unused CSS in production (tiny bundle size)

**Colour system used:**
- `gray-900` / `gray-800` — card backgrounds
- `gray-600` / `gray-500` — secondary text
- `blue-400` — links and interactive elements
- `red-400` / `orange-400` / `yellow-400` / `green-400` — risk tiers
- `white` — primary text

---

## React Router v6 Patterns

```tsx
// App.tsx — define routes
<Routes>
  <Route path="/"                    element={<Navigate to="/queue" />} />
  <Route path="/queue"               element={<QueuePage />} />
  <Route path="/accounts/:accountId" element={<AccountDetailPage />} />
  <Route path="/analytics"           element={<AnalyticsPage />} />
</Routes>

// AccountDetailPage.tsx — read URL parameter
const { accountId } = useParams<{ accountId: string }>();

// Any component — navigate programmatically
const navigate = useNavigate();
navigate(`/accounts/${account.account_id}`);

// Any component — render a link
<Link to={`/accounts/${account.account_id}`}>View Details</Link>
```

---

## Component Design Principles Used

### Controlled Components
Child components read state from props and notify parent via callbacks:
```tsx
// Parent owns the state
const [filters, setFilters] = useState(defaultFilters);

// FilterBar doesn't own state — it just calls onChange
<FilterBar filters={filters} onChange={setFilters} />
```

### Compound Components (sections within a page)
Page components are broken into sections, each with its own sub-component:
```tsx
// AccountDetailPage renders:
<ScoreCircle score={account.risk_score} />
<SignalTimeline signals={account.signals} />
<TransactionTable transactions={account.transactions} accountId={account.account_id} />
<DispositionPanel accountId={account.account_id} onSubmit={refetch} />
```

### Null Safety
API data can be null — always handle it:
```tsx
{account.risk_score !== null && (
  <ScoreCircle score={account.risk_score} />
)}
{/* or */}
<TypologyBadge typology={account.typology} />  // component returns null if no typology
```
