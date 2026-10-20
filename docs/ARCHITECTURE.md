# 🏛️ FridgeMind — Technical Architecture & Machine Learning Specification

This document details the architectural decisions, machine learning algorithms, database schemas, and data pipelines powering **FridgeMind**.

---

## 1. High-Level System Architecture

```mermaid
flowchart TD
    subgraph Client["Frontend Client (React 19 + Tailwind v4 + Vite)"]
        UI1["Screen 1: Landing & Hero"]
        UI2["Screen 2: Multi-Modal Photo / Manual Input"]
        UI3["Screen 3: Pantry & Shelf Management"]
        UI4["Screen 4: Vibe, Taste & Dietary Selection"]
        UI5["Screen 5: Ranked Results & Substitutions"]
        UI6["Screen 6: Cook-Along Interactive Timers"]
        ApiClient["src/services/api.ts (Type-Safe API Client)"]
    end

    subgraph Gateway["FastAPI Application Gateway (:8000)"]
        CORS["CORS & Content Negotiation"]
        Router["API Routers: /health, /ingredients, /recipes"]
        StaticServe["SPA Static Asset Server (/assets, dist/index.html)"]
    end

    subgraph ML_Services["ML Intelligence & Culinary Engines"]
        Vision["Gemini 2.0 Flash Vision<br/>(Multimodal Photo Recognition)"]
        Normalizer["Canonical Normalizer & Alias Engine<br/>(400+ Regional Terms)"]
        FTS["SQLite FTS5 Full-Text Engine<br/>(&lt; 2ms Candidate Retrieval)"]
        Ranking["4-Signal Hybrid Ranking Engine<br/>(Coverage, Taste, Effort, Practicality)"]
        Perishability["Zero-Waste Perishability Optimizer<br/>('Use First' Rescued Boost)"]
        SubEngine["Culinary Substitutions Engine<br/>(Ratios, Notes & 1-Click Adaptation)"]
        Nutrition["USDA Food Composition Engine<br/>(Dynamic Macro & Serving Scaler)"]
        LLMAdapter["Dynamic Gemini Recipe Synthesizer<br/>(Multi-Cuisine Structured JSON)"]
    end

    subgraph Storage["Persistence & Catalog Layer"]
        DB[(SQLite 3 + FTS5 Table<br/>1,122+ Seeded Recipes)]
        BaselineJSON[("recipes_baseline.json<br/>Decoupled Seed Catalog")]
    end

    UI2 -->|Photo Upload| ApiClient
    UI3 -->|Pantry State| ApiClient
    UI4 -->|Preferences & Diets| ApiClient
    ApiClient --> CORS --> Router

    Router -->|POST /ingredients/recognize| Vision
    Vision --> Normalizer
    Router -->|POST /ingredients/normalize| Normalizer

    Router -->|POST /recipes/recommend| FTS
    FTS -->|Top Candidates| DB
    DB --> Ranking
    Normalizer -->|Shelf Priority| Perishability
    Perishability --> Ranking
    Ranking --> SubEngine
    Router -->|Dynamic AI Prompt| LLMAdapter
    LLMAdapter --> DB

    Router -->|GET /recipes/:id/nutrition| Nutrition
    Router -->|POST /recipes/:id/substitute| SubEngine

    Router --> ApiClient
    ApiClient --> UI5 --> UI6
```

---

## 2. Hybrid Recommendation Engine Formulation

The recommendation engine scores and ranks recipe candidates against the user's available pantry items using a multi-factor objective function.

### Mathematical Formulation

$$\text{Composite Score} = w_c \cdot C^* + w_t \cdot T + w_e \cdot E + w_p \cdot P$$

Where:
* **$w_c = 0.45$** (Ingredient Coverage Weight)
* **$w_t = 0.25$** (Taste Profile Alignment Weight)
* **$w_e = 0.20$** (Effort Alignment Weight)
* **$w_p = 0.10$** (Cooking Practicality Weight)

$$\sum w_i = 1.0$$

---

### Signal 1: Zero-Waste Perishability-Boosted Coverage ($C^*$)

Raw ingredient coverage $C$ measures the proportion of recipe ingredients satisfied by the user's pantry:

$$C = \frac{|\text{Matched Ingredients}|}{|\text{Total Recipe Ingredients}|}$$

To prevent food waste, recipes that rescue ingredients categorized as `use_first` (e.g. fresh spinach, herbs, tomatoes, berries) receive a **1.25× multiplicative boost**:

$$C^* = \min\left(1.0, \; C \cdot (1.0 + 0.25 \cdot \mathbb{I}_{\text{rescued}})\right)$$

Where $\mathbb{I}_{\text{rescued}} = 1$ if at least one expiring `use_first` ingredient is utilized.

---

### Signal 2: Taste Profile Alignment ($T$)

Let $\mathcal{U}_t$ be the set of tastes selected by the user (*e.g., spicy, savory, fresh*) and $\mathcal{R}_t$ be the recipe's taste tags.

$$T = \begin{cases} 
0.75 & \text{if } \mathcal{U}_t = \emptyset \text{ (Neutral baseline)} \\
\min\left(1.0, \; 0.60 + 0.40 \cdot \frac{|\mathcal{U}_t \cap \mathcal{R}_t|}{|\mathcal{U}_t|}\right) & \text{if } |\mathcal{U}_t \cap \mathcal{R}_t| > 0 \\
0.25 & \text{otherwise}
\end{cases}$$

---

### Signal 3: Effort Level Alignment ($E$)

Let $L_u \in \{1, 2, 3\}$ correspond to user effort preference (*lazy: 1, easy: 2, chef: 3*) and $L_r \in \{1, 2, 3\}$ be the recipe difficulty rating.

$$E = \begin{cases}
1.00 & \text{if } |L_u - L_r| = 0 \\
0.65 & \text{if } |L_u - L_r| = 1 \\
0.30 & \text{if } |L_u - L_r| = 2
\end{cases}$$

---

### Signal 4: Practicality & Prep Burden ($P$)

Practicality penalizes excessive missing ingredients and lengthy cooking times:

$$P = 0.60 \cdot \left(1.0 - 0.70 \cdot \frac{|\text{Missing}|}{|\text{Total}|}\right) + 0.40 \cdot \text{TimeScore}$$

$$\text{TimeScore} = \begin{cases}
1.0 & \text{if } t \le 15 \text{ mins} \\
0.8 & \text{if } 15 < t \le 30 \text{ mins} \\
0.6 & \text{if } 30 < t \le 45 \text{ mins} \\
0.4 & \text{if } t > 45 \text{ mins}
\end{cases}$$

---

### Temperature-Controlled Softmax Surprise Sampling

When the user activates **"Surprise Me!"** mode, deterministic top-1 sorting is replaced with temperature-scaled Softmax probability sampling over the top $K = 8$ candidates:

$$P(R_i) = \frac{\exp\left(\frac{\text{Score}(R_i)}{\tau}\right)}{\sum_{j=1}^{K} \exp\left(\frac{\text{Score}(R_j)}{\tau}\right)}$$

With sampling temperature $\tau = 0.7$, this ensures serendipitous variety while maintaining high quality and relevance.

---

## 3. SQLite FTS5 Full-Text Index Architecture

To support instantaneous querying across 1,000+ recipes without full-table in-memory scans, FridgeMind maintains an **SQLite FTS5 virtual table**:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS recipes_fts USING fts5(
    recipe_id UNINDEXED,
    name,
    cuisine,
    tags,
    ingredients_text,
    tastes
);
```

When candidate retrieval runs, normalized pantry tokens are sanitized and compiled into an optimized boolean query:

```sql
SELECT r.* FROM recipes r
JOIN recipes_fts fts ON r.id = fts.recipe_id
WHERE recipes_fts MATCH '"egg" OR "tomato" OR "spinach"'
ORDER BY rank
LIMIT 80;
```

This yields sub-2ms query times and scales effortlessly to 50,000+ dishes.

---

## 4. Interactive Substitutions Graph Engine

The substitutions module maps common kitchen staples to culinary alternatives with explicit ratios and culinary tips:

```text
[Heavy Cream] ──(1:1)──> [Coconut Cream]   (Vegan, Dairy-Free)
[Heavy Cream] ──(1:1)──> [Cashew Cream]    (Smooth, Nutty)
[Milk]        ──(1:1)──> [Oat Milk]        (1:1 direct swap)
[Paneer]      ──(1:1)──> [Firm Tofu]       (Press water, pan-fry)
[Eggs]        ──(1:1)──> [Flax Egg]        (1 tbsp flax + 2.5 tbsp water)
[Sour Cream]  ──(1:1)──> [Greek Yogurt]    (Tangy, high protein)
```

When `/api/recipes/{id}/substitute` is invoked, the engine:
1. Rewrites matching ingredient items in the recipe.
2. Performs regex token replacement inside step instructions.
3. Appends a `"Swapped: [Substitute]"` badge.
4. Generates an adjusted culinary note.
