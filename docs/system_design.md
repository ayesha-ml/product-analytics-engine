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
