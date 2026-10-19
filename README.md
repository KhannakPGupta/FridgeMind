# 🍳 FridgeMind — Intelligent Kitchen Companion & Recipe Recommendation

FridgeMind is a full-stack, AI-driven kitchen application that transforms whatever ingredients are sitting in your fridge into delicious, personalized recipes. Designed with a hand-crafted tactile aesthetic, FridgeMind features multimodal ingredient recognition (Google Gemini Vision), a multi-cuisine hybrid recommendation engine with authentic Indian and global dishes, interactive step-by-step cooking timers, and USDA-standard nutritional breakdowns.

---

## 🌟 Key Features

- **📸 Fridge Photo Ingredient Recognition**: Upload or drag-and-drop a kitchen/fridge photo. Powered by Google Gemini 2.0 Flash Vision with safe offline fallback.
- **✍️ Manual Ingredient Entry & Normalization**: Smart alias resolution, plural cleanup, and emoji matching (e.g., paneer, palak, coriander, besan, eggs, tomatoes).
- **🍛 Multi-Cuisine Recipe Catalog**: Curated SQLite database seeded with authentic Indian staples (*Amritsari Paneer Bhurji*, *Tadka Dal*, *Aloo Jeera*, *Egg Akuri*, *Kanda Poha*, *Palak Paneer*, *Besan Chilla*) alongside Continental favorites (*Creamy Tomato Scrambled Eggs*, *Cheesy Garlic Bruschetta*, *Shakshuka*, *Garlic Butter Mushroom Toast*).
- **🎯 4-Signal Hybrid Ranking Engine**:
  $$\text{Score} = 0.45 \times \text{Coverage} + 0.25 \times \text{Taste} + 0.20 \times \text{Effort} + 0.10 \times \text{Practicality}$$
- **🎲 Surprise Mode**: High-quality reproducible sampling from top eligible recipes.
- **🥗 Hard Dietary Filters**: Strict exclusions for Vegetarian, Vegan, Dairy-free, Egg-free, and Gluten-free preferences.
- **⏱️ Cooking Mode**: Interactive ingredient checklist ("have" vs "need" badges), dynamic serving size scaler, step countdown timers with vibration/alerts, and wake-lock focus mode.
- **📊 Nutritional Transparency**: Accurate serving-scaled macro calculations (Calories, Protein, Carbs, Fat, Fiber) based on USDA FoodData Central composition averages.

---

## 🏗️ Project Architecture

```text
FridgeMind/
├── src/                               # Protected Figma React 19 Frontend
│   ├── App.tsx                        # Main application UI & state
│   ├── index.css                      # Global styles & Tailwind v4
│   ├── main.tsx                       # React DOM entry point
│   └── services/
│       └── api.ts                     # Type-safe API client layer
├── backend/                           # Modular FastAPI Backend
│   ├── app/
│   │   ├── main.py                    # App entry point, CORS, and lifecycle
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic Settings & environment config
│   │   │   └── logging.py             # Sanitized logger (masks API keys)
│   │   ├── schemas/                   # Pydantic schemas mirroring frontend types
│   │   │   ├── ingredients.py
│   │   │   ├── recipes.py
│   │   │   └── nutrition.py
│   │   ├── api/                       # HTTP API Routes
│   │   │   ├── health.py              # GET /api/health
│   │   │   ├── ingredients.py         # POST /api/ingredients/recognize, /normalize
│   │   │   └── recipes.py             # POST /api/recipes/recommend, GET /{id}/nutrition
│   │   ├── services/                  # Business & AI Services
│   │   │   ├── vision_service.py      # Gemini 2.0 Flash Vision handler
│   │   │   ├── recipe_service.py      # Candidate retrieval & recommendation
│   │   │   ├── llm_recipe_adapter.py  # Structured generative recipe adaptation
│   │   │   └── nutrition_service.py   # USDA composition nutrient aggregator
│   │   ├── ml/                        # ML & Algorithmic Modules
│   │   │   ├── normalizer.py          # Canonical vocabulary & emoji mapper
│   │   │   ├── ranking.py             # 4-signal hybrid ranking formula
│   │   │   └── hard_filters.py        # Strict allergy and dietary constraint filters
│   │   └── data/
│   │       ├── database.py            # SQLite connection helper
│   │       ├── seed_data.py           # Multi-cuisine recipe catalog seeder
│   │       └── recipes.db             # Bundled SQLite database
│   ├── tests/                         # Pytest automated test suite (25 tests)
│   ├── requirements.txt               # Backend Python dependencies
│   └── .env.example                   # Environment configuration template
├── package.json                       # Frontend dependencies & build scripts
├── vite.config.ts                     # Vite + React + Tailwind v4 config
└── pytest.ini                         # Pytest configuration
```

---

## 🚀 Quick Start Guide (Windows / Mac / Linux)

### 1. Prerequisites
- **Node.js** (v18+ or v24+)
- **Python** (v3.10+ or v3.13+)

---

### 2. Backend Setup

1. Open a terminal in the project root:
   ```powershell
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   ```powershell
   copy .env.example .env
   ```
   *(Optional)* Add your free Google Gemini API key in `backend/.env`:
   ```env
   GEMINI_API_KEY=your_actual_key_here
   ```
   > **Note**: Even without an API key, FridgeMind operates seamlessly offline using its bundled 16+ curated recipes and rule-based vision fallback!

5. Start the backend development server:
   ```powershell
   uvicorn backend.app.main:app --reload --port 8000
   ```
   - API Health Check: `http://localhost:8000/api/health`
   - Interactive Swagger API Docs: `http://localhost:8000/docs`

---

### 3. Frontend Setup

1. In a second terminal in the project root:
   ```powershell
   npm install
   ```
2. Start the Vite development server:
   ```powershell
   npm run dev
   ```
3. Open your browser at `http://localhost:8443` (or the port displayed in your terminal).

---

## 🧪 Automated Testing

Run the comprehensive 25-test backend test suite:
```powershell
backend\.venv\Scripts\pytest backend/tests -v
```
Verified test coverage includes:
- System health and metadata readiness
- Image validation (valid JPEG/PNG, unsupported formats, corrupt files, max size limits)
- Ingredient normalizer & Indian pantry vocabulary
- Dietary hard filters (Vegetarian, Vegan, Dairy-Free, Gluten-Free)
- 4-signal hybrid ranking formula verification
- Nutrition aggregation & serving size scaling
- Recipe recommendation and Surprise mode endpoints

---

## 🔒 Security & Privacy

- **No User Accounts / Tracking**: Pure session-based architecture with zero persistent user databases.
- **Sanitized Logging**: All server logs mask sensitive credentials and API keys.
- **Safe Image Processing**: Uploaded images are processed in memory and never stored on disk.
- **Environment Isolation**: `.env` and local secrets are excluded from Git via `.gitignore`.
