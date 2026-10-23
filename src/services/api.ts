/**
 * FridgeMind API Service Client
 * Handles communication with the FastAPI backend with offline/fallback resilience.
 */

export interface Ingredient {
  id: number
  name: string
  qty: string
  emoji: string
  category?: string
  shelf?: 'use_first' | 'fresh_finds'
  confidence?: number
}

export interface RecipeIngredient {
  name: string
  amount: number
  unit: string
}

export interface Recipe {
  id: number
  name: string
  cuisine?: string
  time: string
  difficulty: string
  tags: string[]
  desc: string
  image: string
  cal: string
  rating: number
  match: number
  accent: string
  servings: number
  ingredients: RecipeIngredient[]
  steps: string[]
  stepTimers: number[]
  substitution: string
  ai_reason?: string
  matched_ingredients?: string[]
  missing_ingredients?: string[]
  badges?: string[]
}

export interface Preferences {
  tastes: string[]
  effort: string | null
  time: string | null
  diets: string[]
}

export interface NutritionSummary {
  calories: number
  protein_g: number
  carbs_g: number
  fat_g: number
  fiber_g?: number
  servings: number
  basis: string
  assumptions: string
  badges?: string[]
  macro_ratios?: {
    protein_pct: number
    carbs_pct: number
    fat_pct: number
  }
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/+$/, '')

/**
 * Upload a fridge photo to recognize ingredients via backend vision service.
 */
export async function recognizeFridgePhoto(file: File): Promise<{ ingredients: Ingredient[]; source: string; notes?: string }> {
  const formData = new FormData()
  formData.append('file', file)

  try {
    const res = await fetch(`${API_BASE}/ingredients/recognize`, {
      method: 'POST',
      body: formData,
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `Upload failed with status ${res.status}`)
    }

    const data = await res.json()
    return {
      ingredients: data.ingredients || [],
      source: data.source || 'gemini_vision',
      notes: data.notes,
    }
  } catch (err) {
    console.warn('[FridgeMind API] Vision endpoint unavailable, using local fallback:', err)
    return {
      ingredients: [
        { id: 1, name: 'Eggs', qty: '6', emoji: '🥚', shelf: 'use_first', category: 'dairy_eggs' },
        { id: 2, name: 'Milk', qty: '500ml', emoji: '🥛', shelf: 'use_first', category: 'dairy_eggs' },
        { id: 3, name: 'Cheese', qty: '200g', emoji: '🧀', shelf: 'use_first', category: 'dairy_eggs' },
        { id: 4, name: 'Tomatoes', qty: '3', emoji: '🍅', shelf: 'use_first', category: 'produce' },
        { id: 5, name: 'Spinach', qty: '1 bunch', emoji: '🥬', shelf: 'use_first', category: 'produce' },
        { id: 6, name: 'Garlic', qty: '4 cloves', emoji: '🧄', shelf: 'fresh_finds', category: 'aromatics' },
        { id: 7, name: 'Onion', qty: '1', emoji: '🧅', shelf: 'fresh_finds', category: 'aromatics' },
        { id: 8, name: 'Bread', qty: '½ loaf', emoji: '🍞', shelf: 'fresh_finds', category: 'bakery' },
        { id: 9, name: 'Carrots', qty: '3', emoji: '🥕', shelf: 'fresh_finds', category: 'produce' },
        { id: 10, name: 'Mushrooms', qty: '200g', emoji: '🍄', shelf: 'use_first', category: 'produce' },
        { id: 11, name: 'Lemon', qty: '1', emoji: '🍋', shelf: 'fresh_finds', category: 'produce' },
        { id: 12, name: 'Butter', qty: '100g', emoji: '🧈', shelf: 'fresh_finds', category: 'dairy_eggs' },
      ],
      source: 'offline_fallback',
      notes: 'Backend offline, loaded default fridge staples.',
    }
  }
}

/**
 * Normalize and clean manually typed ingredients.
 */
export async function normalizeManualIngredients(items: string[]): Promise<Ingredient[]> {
  try {
    const res = await fetch(`${API_BASE}/ingredients/normalize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items }),
    })

    if (res.ok) {
      const data = await res.json()
      return data.ingredients || []
    }
  } catch (err) {
    console.warn('[FridgeMind API] Normalizer unavailable, using raw entries:', err)
  }

  // Client-side fallback if backend unreachable
  return items.map((name, idx) => {
    const isPerishable = ['spinach', 'milk', 'cheese', 'tomato', 'egg', 'yogurt', 'curd', 'herb', 'cilantro', 'berries', 'mushroom'].some(k => name.toLowerCase().includes(k))
    return {
      id: Date.now() + idx,
      name,
      qty: '1',
      emoji: '🥗',
      shelf: isPerishable ? 'use_first' : 'fresh_finds',
    }
  })
}

/**
 * Fetch hybrid-ranked recipes tailored to pantry and user preferences.
 */
export async function getRecipeRecommendations(
  ingredients: Ingredient[],
  preferences: Preferences,
  theme: string = 'cozy',
  surprise: boolean = false
): Promise<{ recipes: Recipe[]; theme: string; source: string }> {
  try {
    const res = await fetch(`${API_BASE}/recipes/recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ingredients,
        preferences,
        theme,
        surprise,
      }),
    })

    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data.recipes) && data.recipes.length > 0) {
        return {
          recipes: data.recipes,
          theme: data.selected_theme || theme,
          source: data.source || 'backend',
        }
      }
    }
  } catch (err) {
    console.warn('[FridgeMind API] Recipe recommendation endpoint unreachable:', err)
  }

  return {
    recipes: [],
    theme,
    source: 'offline_fallback',
  }
}

/**
 * Fetch USDA nutrition analysis for a recipe scaled to servings.
 */
export async function getRecipeNutrition(recipeId: number, servings: number = 2): Promise<NutritionSummary | null> {
  try {
    const res = await fetch(`${API_BASE}/recipes/${recipeId}/nutrition?servings=${servings}`)
    if (res.ok) {
      return await res.json()
    }
  } catch (err) {
    console.warn('[FridgeMind API] Nutrition endpoint unreachable:', err)
  }
  return null
}

export interface SubstitutionOption {
  original: string
  substitute: string
  ratio: string
  flavor_impact: string
  notes: string
  dietary_tags?: string[]
}

export interface CatalogStats {
  total_recipes: number
  by_cuisine: Record<string, number>
  by_source?: Record<string, number>
}

/**
 * Check connectivity and status of the FastAPI backend.
 */
export async function checkApiHealth(): Promise<{ status: string; version: string } | null> {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) })
    if (res.ok) {
      return await res.json()
    }
  } catch (err) {
    // Backend offline or unreachable
  }
  return null
}

/**
 * Fetch catalog statistics from backend database.
 */
export async function fetchCatalogStats(): Promise<CatalogStats | null> {
  try {
    const res = await fetch(`${API_BASE}/recipes/catalog/stats`, { signal: AbortSignal.timeout(4000) })
    if (res.ok) {
      return await res.json()
    }
  } catch (err) {
    console.warn('[FridgeMind API] Catalog stats unreachable:', err)
  }
  return null
}

/**
 * Fetch all culinary substitutions applicable to a given recipe.
 */
export async function fetchRecipeSubstitutions(recipeId: number): Promise<SubstitutionOption[]> {
  try {
    const res = await fetch(`${API_BASE}/recipes/${recipeId}/substitutions`, { signal: AbortSignal.timeout(4000) })
    if (res.ok) {
      return await res.json()
    }
  } catch (err) {
    console.warn('[FridgeMind API] Recipe substitutions unreachable, using client heuristics:', err)
  }
  return []
}

// Built-in curated substitutions knowledge base for instant offline reactivity
const OFFLINE_SUBSTITUTIONS_MAP: Record<string, SubstitutionOption[]> = {
  milk: [
    { original: 'Milk', substitute: 'Oat milk', ratio: '1:1', flavor_impact: 'slightly sweet, silky', notes: 'Direct swap in baking, sauces, and cooking.', dietary_tags: ['vegan', 'dairy-free'] },
    { original: 'Milk', substitute: 'Almond milk', ratio: '1:1', flavor_impact: 'subtle nutty', notes: 'Best when unsweetened in savory dishes.', dietary_tags: ['vegan', 'dairy-free'] },
    { original: 'Milk', substitute: 'Water + Butter', ratio: '1 cup water + 1 tbsp butter', flavor_impact: 'rich, neutral', notes: 'Quick pantry trick when dairy carton is empty.', dietary_tags: ['vegetarian'] },
  ],
  paneer: [
    { original: 'Paneer', substitute: 'Firm Tofu', ratio: '1:1', flavor_impact: 'neutral, absorbs spices', notes: 'Press excess water, pan-fry golden for authentic texture.', dietary_tags: ['vegan', 'dairy-free', 'high-protein'] },
    { original: 'Paneer', substitute: 'Halloumi', ratio: '1:1', flavor_impact: 'salty, savory', notes: 'Grills and sears with a wonderful squeaky bite.', dietary_tags: ['vegetarian'] },
  ],
  cheese: [
    { original: 'Cheese', substitute: 'Nutritional Yeast', ratio: '2 tbsp per 1/2 cup cheese', flavor_impact: 'cheesy, savory umami', notes: 'Scatter over warm dishes for cheesy flavor.', dietary_tags: ['vegan', 'dairy-free'] },
    { original: 'Cheese', substitute: 'Firm Tofu Crumble', ratio: '1:1', flavor_impact: 'mild, protein-rich', notes: 'Season with salt and olive oil.', dietary_tags: ['vegan', 'dairy-free'] },
  ],
  spinach: [
    { original: 'Spinach', substitute: 'Kale', ratio: '1:1', flavor_impact: 'heartier, earthy', notes: 'Remove tough woody stems, sauté 2 mins longer.', dietary_tags: ['vegan', 'gluten-free'] },
    { original: 'Spinach', substitute: 'Swiss Chard', ratio: '1:1', flavor_impact: 'tender, mineral', notes: 'Chop stems finely and sauté with greens.', dietary_tags: ['vegan', 'gluten-free'] },
    { original: 'Spinach', substitute: 'Frozen Green Peas', ratio: '1:1', flavor_impact: 'sweet, tender', notes: 'Thaw and toss into pan in final 3 minutes.', dietary_tags: ['vegan', 'gluten-free'] },
  ],
  tomato: [
    { original: 'Tomato', substitute: 'Canned Diced Tomatoes', ratio: '1/2 cup per tomato', flavor_impact: 'rich, concentrated', notes: 'Simmer lightly to reduce excess canning liquid.', dietary_tags: ['vegan', 'gluten-free'] },
    { original: 'Tomato', substitute: 'Red Bell Pepper', ratio: '1:1', flavor_impact: 'sweet, smoky', notes: 'Dice finely and sauté to soften.', dietary_tags: ['vegan', 'gluten-free'] },
  ],
  butter: [
    { original: 'Butter', substitute: 'Olive Oil', ratio: '3:4 (3 tbsp oil per 4 tbsp butter)', flavor_impact: 'fruity, Mediterranean', notes: 'Excellent for pan-frying and sautéing.', dietary_tags: ['vegan', 'dairy-free'] },
    { original: 'Butter', substitute: 'Ghee', ratio: '1:1', flavor_impact: 'nutty, aromatic', notes: 'Higher smoke point, ideal for crisping.', dietary_tags: ['vegetarian'] },
  ],
  egg: [
    { original: 'Egg', substitute: 'Flax Egg', ratio: '1 tbsp ground flax + 2.5 tbsp water per egg', flavor_impact: 'nutty, good binder', notes: 'Rest for 5 mins until gelled before using.', dietary_tags: ['vegan', 'egg-free'] },
    { original: 'Egg', substitute: 'Silken Tofu', ratio: '1/4 cup blended tofu per egg', flavor_impact: 'creamy, neutral', notes: 'Moisturizes pancakes, scrambles, and bakes.', dietary_tags: ['vegan', 'egg-free'] },
  ],
}

/**
 * Look up feasible culinary substitutions for any ingredient (with offline dictionary support).
 */
export async function lookupSubstitutions(ingredient: string): Promise<SubstitutionOption[]> {
  try {
    const res = await fetch(`${API_BASE}/recipes/substitutions/lookup?ingredient=${encodeURIComponent(ingredient)}`, {
      signal: AbortSignal.timeout(3000),
    })
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data) && data.length > 0) return data
    }
  } catch (err) {
    // Fall back to client dictionary below
  }

  const lower = ingredient.toLowerCase()
  for (const [key, options] of Object.entries(OFFLINE_SUBSTITUTIONS_MAP)) {
    if (lower.includes(key) || key.includes(lower)) {
      return options
    }
  }
  return []
}

/**
 * Adapt a recipe by swapping an ingredient dynamically (with seamless client fallback).
 */
export async function substituteRecipeIngredient(
  recipe: Recipe,
  replace: string,
  substituteWith: string
): Promise<{ recipe: Recipe; message: string }> {
  try {
    const res = await fetch(`${API_BASE}/recipes/${recipe.id}/substitute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ replace, substitute_with: substituteWith }),
      signal: AbortSignal.timeout(4000),
    })
    if (res.ok) {
      const data = await res.json()
      if (data?.recipe) {
        return { recipe: data.recipe, message: data.message || `Swapped ${replace} with ${substituteWith}` }
      }
    }
  } catch (err) {
    console.warn('[FridgeMind API] Substitute endpoint offline, using local client adaptation:', err)
  }

  // Client-side recipe adaptation fallback
  const regex = new RegExp(`\\b${replace}\\b`, 'gi')
  const updatedIngredients = recipe.ingredients.map(ing => {
    if (ing.name.toLowerCase().includes(replace.toLowerCase()) || replace.toLowerCase().includes(ing.name.toLowerCase())) {
      return { ...ing, name: substituteWith }
    }
    return ing
  })

  const updatedSteps = recipe.steps.map(step => step.replace(regex, substituteWith))
  const newBadges = [...(recipe.badges || [])]
  const swapBadge = `Swapped: ${substituteWith}`
  if (!newBadges.includes(swapBadge)) {
    newBadges.unshift(swapBadge)
  }

  const adaptedRecipe: Recipe = {
    ...recipe,
    ingredients: updatedIngredients,
    steps: updatedSteps,
    badges: newBadges,
    desc: `${recipe.desc} (Adapted with ${substituteWith})`,
  }

  return {
    recipe: adaptedRecipe,
    message: `Successfully adapted recipe: swapped ${replace} with ${substituteWith}.`,
  }
}


