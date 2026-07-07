# TheLook eCommerce: Data & System Design Reference

**Project:** Product Analytics & Experimentation Engine  
**Dataset:** `bigquery-public-data.thelook_ecommerce`  
**Author:** Ayesha Amer

---

## Dataset Overview & Scope

The Look is a synthetic eCommerce dataset hosted on Google BigQuery. The data architecture consists of 7 tables, scoped based on the structural requirements of our four analytical modules. Production-grade logic is strictly restricted to modular `.py` and `.sql` files; notebooks are used exclusively for scratch work and mathematical prototyping.

### Core Tables & Project Relevance

| Table                  | Row Count | Scope & Utility                                                                                     |
| :--------------------- | :-------- | :-------------------------------------------------------------------------------------------------- |
| `events`               | 2,416,574 | **In Scope**: Primary clickstream source for Funnel Analysis & Experimentation (Modules 1 & 3).     |
| `orders`               | 124,690   | **In Scope**: Order placement logs used for Retention & Experimentation outcomes (Modules 2 & 3).   |
| `order_items`          | 180,520   | **In Scope**: Line-item transaction details for RFM Segmentation & Cohort analysis (Modules 2 & 4). |
| `users`                | 100,000   | **In Scope**: Customer profiles used for identity resolution and cohort mapping (Modules 1 & 2).    |
| `products`             | 29,120    | **Deferred**: Product catalog (deferred to Module 4 category deep dives).                           |
| `inventory_items`      | 487,585   | **Out of Scope**: Individual unit costs and real-time inventory tracking.                           |
| `distribution_centers` | 10        | **Out of Scope**: Warehouse fulfillment locations.                                                  |

---

## Clickstream & Funnel Architecture (`events`)

The `events` table captures granular web interactions. It is the core data asset for user sessionization, identity resolution, and behavioral funnels.

### Schema Attributes & Constraints

- **`id`** (INTEGER): Unique row identifier.
- **`session_id`** (STRING): Session tracking token. Acts as the primary partition key for sessionization.
- **`sequence_number`** (INTEGER): Chronological order of user actions within a single session.
- **`created_at`** (TIMESTAMP): Event timestamp (UTC). Inactivity gaps exceeding 30 minutes define session boundaries (Google Analytics standard).
- **`event_type`** (STRING): User action type (`home`, `department`, `product`, `cart`, `purchase`, `cancel`).
- **`user_id`** (INTEGER): Customer identifier. **Note: 46.54% of rows are NULL**, representing unauthenticated browsing before account authentication.

### Module 1: Sessionization and Identity Resolution Findings

#### Sessionization

The sessionization logic was verified using four automated unit tests against real users, and all of them passed successfully. The test results showed:

- Every user's very first recorded event was correctly initialized with a `session_sequence` of 1.
- The query caught all 41 real session boundaries where a user was inactive for more than 30 minutes.
- All 313 events that happened within that active 30-minute window were correctly grouped together without falsely spinning up new sessions.
- The total session count perfectly matched the number of boundary flags for the test users.

#### Identity Resolution

For the user stitching layer, the logic was implemented using `FIRST_VALUE(user_id IGNORE NULLS)` partitioned strictly by the `session_id`.

During development, an interesting design challenge came up. The initial plan considered partitioning by both `session_id` and the verified `session_sequence`. However, tracing through the data revealed that this would completely orphan any anonymous events that happened right before a user authenticated within that same window. Those early events would never get resolved. Keeping the partition solely on `session_id` fixed this, because identity (tracking who someone is) and session boundaries (counting individual visits) are two entirely different concepts that shouldn't share a partition key.

Testing this on real mixed sessions uncovered a major characteristic of this specific dataset: TheLook's tracking system never lets a single `session_id` cross the anonymous-to-authenticated boundary. Every single `session_id` in the raw data is either entirely anonymous or entirely authenticated, never a mix of both. Because of how the data is generated, the identity resolution query doesn't actually have any unauthenticated rows to stitch backward.

Even though the dataset doesn't trigger the stitching behavior, the module was kept exactly as it is. The SQL architecture is completely correct, computationally sound, and represents a standard data engineering pattern. On a real production clickstream where an anonymous cookie gets linked to a user profile at checkout, this exact query handles the backward propagation flawlessly. Documenting this constraint clearly in the system design shows a solid, honest understanding of data quality auditing, which makes for a great technical talking point.

## Clickstream Funnel & Leakage Analytics (`events`)

### Methodology & Data Grain

To map the user conversion journey, the clickstream event grain (2.4M rows) was aggregated into an order-agnostic Milestone Prevalence Matrix at a strict session grain (`session_id`), yielding 682,025 unique sessions.

Instead of forcing a rigid, linear timestamp sequence, which breaks down under non-linear browsing behaviors like page refreshes and multi-tabbing, the architecture evaluates the total footprint of a session. Binary flags track whether a milestone was reached at any point during the session.

To isolate the exact drop-off point, a derived categorical metric named `abandonment_stage` uses top-down conditional prioritization to tag each session by the highest-intent milestone achieved before termination. The evaluation filters rows sequentially, prioritizing completed purchases first, followed by checkout entries, product views, department browsing, and home page landings.

### Funnel Metrics & Diagnostic Findings

The distribution analysis of milestone flags and final abandonment states yielded the following matrix:

| Milestone / Stage    | Total Sessions | Traffic Exposure (% of Total) | Resulting Abandonment Stage | Share of Total Sessions (%) |
| :------------------- | :------------- | :---------------------------- | :-------------------------- | :-------------------------- |
| `reached_home`       | 88,179         | 12.9%                         | _Abandoned at Department_   | 0.0%                        |
| `reached_department` | 431,551        | 63.3%                         | _Abandoned at Product_      | 0.0%                        |
| `reached_product`    | 682,025        | 100.0%                        | **Abandoned at Cart**       | **36.6%**                   |
| `reached_cart`       | 432,205        | 63.4%                         | **Abandoned at Checkout**   | **36.7%**                   |
| `reached_purchase`   | 182,025        | 26.7%                         | **Completed Purchase**      | **26.7%**                   |

### Data Quality & Architectural Insights

1. **Inverted Funnel Anomaly:** Standard e-commerce funnels exhibit a wide-top pyramid starting at the homepage. Here, product reach sits at exactly 100.0%, while homepage traffic is captured at only 12.9%. In a production ecosystem, this pattern implies a highly optimized deep-linking or performance-marketing model where traffic completely bypasses the landing page. In this specific environment, it highlights a hardcoded constraint within the synthetic data generation engine, which mandates at least one product view per valid session.
2. **Impact on Leakage Math:** Because a product interaction is a universal constant across all sessions, the conditional sorting logic naturally terminates before hitting lower-tier stages. Consequently, "Abandoned at Home," "Abandoned at Department," and "Bounced Immediately" mathematically resolve to 0.0%.
3. **Primary Growth Friction Points:** Growth analytics and optimization efforts should focus entirely on the two true leakage buckets:
   - **Cart Abandonment (36.6%):** High product interest that failed to clear the "Add to Cart" intent barrier. Points to pricing friction, missing reviews, or weak product-page layouts.
   - **Checkout Leakage (36.7%):** High-intent users who built a cart but dropped out during the shipping configuration, account creation, or payment collection phases.

---

## Module 2 — Retention Analytics

### Business Question

Are we keeping the customers we acquire, or is growth entirely dependent
on new customer volume?

### Analytical Approach

Two SQL queries feed this module:

**cohort_retention.sql** — assigns every customer to their acquisition
cohort (the calendar month of their first order) using `MIN(created_at)`
grouped by `user_id`. Then joins every subsequent order back to that
cohort month and calculates `DATE_DIFF` in months to produce a retention
matrix. Filtered to `status IN ('Complete', 'Shipped')` throughout —
cancelled and returned orders do not represent real retained revenue.

**monthly_revenue.sql** — aggregates revenue by month using a JOIN
between orders and order_items, then applies `LAG(revenue) OVER (ORDER
BY month)` to compute month-over-month growth rate using `SAFE_DIVIDE`
to handle the first-month NULL boundary cleanly. Filtered to exclude
the current incomplete month using `WHERE month < DATE_TRUNC
(CURRENT_DATE(), MONTH)` — TheLook's synthetic data is cut off
mid-month, which otherwise produces a large artificial negative MoM
swing in the final data point.

### Key Design Decisions

| Decision                                                       | Reasoning                                                                                                                                                                                                                       |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Use `MIN(created_at)` not `ROW_NUMBER()` for cohort assignment | We need the acquisition month (a date), not the specific row. `MIN()` with `GROUP BY` is the correct, simpler tool here. `ROW_NUMBER()` would be needed only if we required the specific first-order row for a downstream join. |
| Filter to Complete + Shipped only                              | Established Day 2 as the correct revenue definition. Cancelled/Returned orders inflate cohort sizes and distort retention rates.                                                                                                |
| Exclude current month from revenue                             | TheLook is cut off mid-month — the final bar always shows artificially low revenue, making the last MoM figure meaningless.                                                                                                     |

### Findings

| Metric                    | Value                            |
| ------------------------- | -------------------------------- |
| Total cohorts analyzed    | 91 monthly cohorts (2019 — 2026) |
| Average Month-1 retention | 2.49%                            |
| Average Month-3 retention | 2.00%                            |
| Latest MoM revenue growth | 31.29%                           |

### Visualizations

**Cohort heatmap:** Confirms near-zero repeat purchase rates across
almost all 91 cohorts. The most recent cohorts (late 2026) show
artificially elevated retention in early months — this is because
recent cohorts have had less time for attrition to occur, producing
survivorship bias in the short-term metrics.

**Revenue trend:** Consistent upward trajectory from 2019 through
mid-2026. The 600%+ MoM spike at the start of 2019 is a synthetic
data artifact — the dataset starts from near-zero revenue, so early
percentage changes are mathematically extreme. From mid-2019 onward,
MoM growth stabilizes in the 10-40% range, consistent with a scaling
business.

### Diagnosis

Average Month-1 retention of 2.49% indicates near-zero repeat purchase
behavior. Fewer than 3 in 100 customers return within 30 days of their
first purchase. Revenue growth is driven entirely by new customer
acquisition volume, not loyalty — a structurally fragile model where
any slowdown in new user acquisition directly impacts revenue with no
loyal customer base to absorb it.

Primary recommendation: invest in post-purchase retention mechanics
(email sequences, loyalty incentives, personalized re-engagement
campaigns) before scaling paid acquisition spend further.
