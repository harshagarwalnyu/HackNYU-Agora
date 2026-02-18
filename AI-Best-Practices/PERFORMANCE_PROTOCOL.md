# PERFORMANCE_PROTOCOL.md

## 1. OVERVIEW

**Role:** Performance Optimization Auditor  
**Objective:** Systematically reduce latency and resource usage across the full application stack — infrastructure, database, backend, frontend, and code.

**Target Thresholds:**

| Metric | Target | Measurement Tool |
|---|---|---|
| Time to First Byte (TTFB) | < 100ms | Chrome DevTools / WebPageTest |
| First Contentful Paint (FCP) | < 1.0s | Lighthouse |
| Largest Contentful Paint (LCP) | < 2.5s | Lighthouse / CrUX |
| Total Blocking Time (TBT) | < 200ms | Lighthouse |
| Cumulative Layout Shift (CLS) | < 0.1 | Lighthouse |
| Lighthouse Performance Score | > 95 | Chrome DevTools |
| Max single asset size (network) | < 500KB | Network Tab |

Work through each section in order. Sections are ordered from highest to lowest typical impact.

---

## 2. INFRASTRUCTURE & NETWORK

Fixing infrastructure issues yields the highest return before touching any application code.

### 2.1 CDN for Static Assets

Static assets (CSS, JS, images, fonts) must never be served directly from the application server.

1. Configure your upload/build pipeline to push static assets to a CDN (e.g., AWS CloudFront + S3, Cloudflare R2, Fastly).
2. Update all asset references to use the CDN origin URL.
   - Before: `/assets/logo.webp`
   - After: `https://cdn.yourdomain.com/assets/logo.webp`
3. Set long-lived `Cache-Control` headers on the CDN for versioned/hashed assets:
   ```
   Cache-Control: public, max-age=31536000, immutable
   ```

### 2.2 HTTP Protocol Version

1. **Enable HTTP/2** on your server or load balancer. HTTP/2 multiplexes multiple requests over a single TCP connection, eliminating the per-request connection overhead of HTTP/1.1.
2. **Enable TLS 1.3.** It reduces the handshake from 2 round-trips (TLS 1.2) to 1, meaningfully improving TTFB for new connections.
3. Verify in Chrome DevTools → Network tab → "Protocol" column. Values should read `h2`, not `http/1.1`.

### 2.3 Compression

Verify Gzip or Brotli compression is enabled at the server or reverse proxy level. Brotli achieves ~20% better compression than Gzip on text assets.

**Express (Node.js):**
```javascript
// npm install compression
const compression = require('compression');
app.use(compression()); // Must be registered before other middleware
```

**Nginx:**
```nginx
gzip on;
gzip_comp_level 6;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;
gzip_min_length 1000;
gzip_vary on;
```

**Brotli (Nginx, if module available):**
```nginx
brotli on;
brotli_comp_level 6;
brotli_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;
```

Verify: In the Network tab, check response headers for `Content-Encoding: gzip` or `Content-Encoding: br`.

---

## 3. DATABASE OPTIMIZATION

Database queries are the most common source of backend latency. Fix these before optimizing application logic.

### 3.1 Eliminate N+1 Queries

An N+1 query occurs when one query fetches a list of records and then a separate query is issued for each record in a loop.

**How to detect:** Look for any database call inside a `for`, `while`, or `.forEach` loop.

```python
# BAD — N+1 pattern: 1000 users = 1001 queries
for user in users:
    details = db.execute("SELECT * FROM details WHERE user_id = ?", user.id)
```

**Fix:** Batch the lookup into a single query using `WHERE ... IN (...)` or a `JOIN`.

```python
# GOOD — exactly 1 query regardless of list size
user_ids = [u.id for u in users]
all_details = db.execute(
    "SELECT * FROM details WHERE user_id = ANY(%s)", (user_ids,)
)
# Then build a dict for O(1) lookup in the loop
details_by_user = {d['user_id']: d for d in all_details}

for user in users:
    details = details_by_user.get(user.id)
```

ORM-specific shortcuts: `select_related` / `prefetch_related` (Django), `eager loading` with `includes` (Rails), `joinedload` (SQLAlchemy).

### 3.2 Add Missing Indexes

Missing indexes cause full table scans, which scale linearly with table size.

**How to detect:**
1. Identify every column referenced in a `WHERE`, `ORDER BY`, `GROUP BY`, or `JOIN ON` clause.
2. Confirm each of those columns has an index (or is part of a composite index). Primary keys are indexed automatically; foreign keys and filter columns often are not.
3. Run `EXPLAIN ANALYZE <query>` (Postgres) or `EXPLAIN <query>` (MySQL) and look for `Seq Scan` on large tables — this indicates a missing index.

**Action:**
```sql
-- Single-column index
CREATE INDEX idx_orders_user_id ON orders (user_id);

-- Composite index when two columns are frequently filtered together
CREATE INDEX idx_orders_user_status ON orders (user_id, status);
```

> **Note:** Indexes speed up reads but slow down writes. Do not index every column — only columns with high cardinality that are queried frequently.

### 3.3 Remove `SELECT *`

`SELECT *` retrieves all columns, including large `TEXT`, `BLOB`, and `JSONB` fields that are often unused.

**Action:** Replace every `SELECT *` with an explicit column list of only what the application actually uses.

```sql
-- Bad
SELECT * FROM users;

-- Good
SELECT id, name, email, created_at FROM users;
```

### 3.4 Use a Connection Pool

Opening a new database connection per request is expensive (typically 20–100ms). A connection pool maintains a set of reusable connections.

**Node.js (pg-pool):**
```javascript
const { Pool } = require('pg');
const pool = new Pool({
  max: 20,               // Maximum simultaneous connections
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});
```

**Python (SQLAlchemy):**
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Reconnects stale connections automatically
)
```

**Go (`database/sql`):**
```go
db.SetMaxOpenConns(25)
db.SetMaxIdleConns(25)
db.SetConnMaxLifetime(5 * time.Minute)
```

---

## 4. BACKEND & API CACHING

### 4.1 HTTP Response Caching

For endpoints that return data which does not change per-request (product listings, configuration, public content), set `Cache-Control` headers so that CDNs and browsers can serve cached responses instead of hitting the origin.

```javascript
// Publicly cacheable, revalidated after 1 hour
res.set('Cache-Control', 'public, max-age=3600, stale-while-revalidate=60');

// Private to the user, cached in browser only
res.set('Cache-Control', 'private, max-age=300');

// Versioned/hashed assets — cache forever
res.set('Cache-Control', 'public, max-age=31536000, immutable');
```

For user-specific or frequently changing data, use `Cache-Control: no-store` to prevent stale reads.

### 4.2 Application-Layer Caching (Redis / Memcached)

For expensive computed results (e.g., aggregated reports, external API responses), cache results in Redis rather than recalculating on every request.

```python
import redis, json

cache = redis.Redis()
CACHE_TTL = 300  # seconds

def get_dashboard_stats(org_id: str):
    cache_key = f"dashboard_stats:{org_id}"
    cached = cache.get(cache_key)
    if cached:
        return json.loads(cached)

    stats = compute_expensive_stats(org_id)  # DB-heavy operation
    cache.setex(cache_key, CACHE_TTL, json.dumps(stats))
    return stats
```

When caching, define a cache invalidation strategy — either TTL-based (as above) or event-driven (invalidate on write).

---

## 5. FRONTEND ASSET OPTIMIZATION

### 5.1 Images

Images are typically the largest contributor to page weight. Apply all of the following:

**Format:** Convert `.png` and `.jpg` files to `.webp` (broad browser support) or `.avif` (better compression, slightly less support). Use a `<picture>` element to provide fallbacks.

```html
<picture>
  <source srcset="hero.avif" type="image/avif">
  <source srcset="hero.webp" type="image/webp">
  <img src="hero.jpg" alt="Hero image" width="1920" height="1080">
</picture>
```

**Dimensions:** No image served to a browser needs to exceed 1920px in its largest dimension for a hero, and most content images need far less. Resize at build time using `sharp`, `imagemagick`, or your CDN's image transformation features.

**Responsive images:** Use `srcset` to serve appropriately sized images based on viewport width.

```html
<img
  src="photo-800.webp"
  srcset="photo-400.webp 400w, photo-800.webp 800w, photo-1200.webp 1200w"
  sizes="(max-width: 600px) 400px, (max-width: 1000px) 800px, 1200px"
  alt="..."
  loading="lazy"
  decoding="async"
/>
```

**Lazy loading:** Add `loading="lazy"` and `decoding="async"` to every `<img>` that is not in the initial viewport. Do not lazy-load the LCP image (typically the hero image).

**Explicit dimensions:** Always set `width` and `height` attributes to prevent layout shift (CLS).

### 5.2 JavaScript Bundle Splitting

Delivering one large `bundle.js` delays interactivity. Split it by route and load chunks on demand.

**Dynamic imports (React):**
```javascript
import { lazy, Suspense } from 'react';

// Before
import Dashboard from './Dashboard';

// After — Dashboard JS is only downloaded when the route is visited
const Dashboard = lazy(() => import('./Dashboard'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Dashboard />
    </Suspense>
  );
}
```

**Vite / Webpack:** Code splitting happens automatically for dynamic imports. Confirm by running the bundle analyzer after build:
```bash
# Vite
npx vite build --mode analyze

# Webpack
npx webpack-bundle-analyzer stats.json
```

Look for: duplicate packages (e.g., two versions of `lodash`), unexpectedly large chunks, vendor libraries that should be externalized.

### 5.3 Font Loading

Fonts are a common cause of invisible text (FOIT) and layout shifts.

1. Add `font-display: swap` to all `@font-face` declarations. This renders text in a fallback font immediately and swaps to the custom font once loaded.
   ```css
   @font-face {
     font-family: 'MyFont';
     src: url('/fonts/myfont.woff2') format('woff2');
     font-display: swap;
   }
   ```

2. Preconnect to font origins (if using a third-party font service) so the DNS + TLS handshake happens early:
   ```html
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   ```

3. Preload the most critical font file (the one used for body text above the fold):
   ```html
   <link rel="preload" href="/fonts/myfont.woff2" as="font" type="font/woff2" crossorigin>
   ```

4. Self-hosting fonts eliminates the third-party DNS round-trip entirely and is preferred over using a CDN like Google Fonts.

---

## 6. CODE-LEVEL OPTIMIZATIONS

Apply these after infrastructure, database, and asset issues are resolved.

### 6.1 Move Invariant Calculations Out of Loops

If a value does not change between loop iterations, compute it once before the loop.

```javascript
// Bad — Math.pow is called on every iteration
for (let i = 0; i < arr.length; i++) {
  arr[i] += Math.pow(base, exp);
}

// Good — computed once
const factor = Math.pow(base, exp);
for (let i = 0; i < arr.length; i++) {
  arr[i] += factor;
}
```

Also avoid reading `arr.length` on every iteration in performance-critical loops — cache it in a variable.

### 6.2 String Building in Loops

Repeated string concatenation in a loop creates a new string object on every iteration.

| Language | Avoid | Use Instead |
|---|---|---|
| Python | `result += chunk` in a loop | `result = "".join(chunks)` |
| Java / C# | `str += part` in a loop | `StringBuilder` |
| JavaScript | `str = str + part` | Template literals or `Array.join()` |

### 6.3 Clean Up Event Listeners and Timers

Unremoved event listeners and intervals cause memory leaks, which degrade performance over time.

```javascript
// React — correct cleanup pattern
useEffect(() => {
  const handler = () => { /* ... */ };
  window.addEventListener('resize', handler);

  const interval = setInterval(pollData, 5000);

  return () => {
    window.removeEventListener('resize', handler); // Cleanup
    clearInterval(interval);                        // Cleanup
  };
}, []);
```

**How to detect leaks:** In Chrome DevTools → Memory tab, take a Heap Snapshot, interact with the app, take another snapshot, and compare. Growing listener or timer counts between snapshots indicate a leak.

### 6.4 Debounce and Throttle High-Frequency Events

Event handlers attached to `scroll`, `resize`, `mousemove`, or `input` can fire hundreds of times per second. Wrap them appropriately.

```javascript
import { debounce, throttle } from 'lodash';

// Search input — wait until user stops typing for 300ms
const handleSearch = debounce((value) => fetchResults(value), 300);

// Scroll handler — fire at most once every 100ms
const handleScroll = throttle(() => updateScrollPosition(), 100);
```

---

## 7. VERIFICATION CHECKLIST

Run all checks before marking optimization work complete.

### Lighthouse (Chrome DevTools)

1. Open Chrome DevTools → Lighthouse tab.
2. Select "Performance" category only.
3. Run in Incognito mode with extensions disabled.
4. Target scores: Performance > 95, all Core Web Vitals in green.

### Network Tab Audit

1. Load the page with the Network tab open. Disable cache (`Cmd+Shift+P` → "Disable cache").
2. Sort by **Size** — flag anything over 500KB (uncompressed).
3. Sort by **Time** — flag any request with TTFB > 200ms.
4. Confirm the "Protocol" column shows `h2` for all requests.
5. Confirm `Content-Encoding` response headers show `gzip` or `br`.

### Bundle Analysis

```bash
# Vite
npx vite build --mode analyze

# Create React App
npm install -g source-map-explorer
npm run build && source-map-explorer 'build/static/js/*.js'
```

Flag: duplicate packages (e.g., two versions of `lodash`), any single chunk > 250KB (parsed, not gzipped).

### Database Query Audit

1. Enable slow query logging:
   - **Postgres:** `log_min_duration_statement = 100` (logs any query over 100ms)
   - **MySQL:** `slow_query_log = 1`, `long_query_time = 0.1`
2. Run `EXPLAIN ANALYZE` on the slowest queries. Confirm no `Seq Scan` on large tables.

### Console Warnings

Open the browser console and confirm there are no:
- `[Violation] 'setTimeout' handler took Nms` warnings (indicates long-running JS on the main thread)
- `[Violation] Forced reflow while executing JavaScript` (indicates layout thrashing)

---

**END OF PROTOCOL**
