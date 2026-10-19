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
