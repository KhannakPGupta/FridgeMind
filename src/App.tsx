import { useEffect, useState, useRef, useMemo } from 'react'
import {
  recognizeFridgePhoto,
  getRecipeRecommendations,
  normalizeManualIngredients,
  getRecipeNutrition,
  checkApiHealth,
  fetchRecipeSubstitutions,
  lookupSubstitutions,
  substituteRecipeIngredient,
  fetchCatalogStats,
  type Ingredient,
  type RecipeIngredient,
  type Recipe,
  type Preferences,
  type NutritionSummary,
  type SubstitutionOption,
  type CatalogStats,
} from './services/api'

type Screen = 'home' | 'input' | 'ingredients' | 'vibe' | 'results' | 'recipe'
type VibeTheme = 'cozy' | 'spicy' | 'fresh' | 'chef'

const DEFAULT_PREFERENCES: Preferences = { tastes: [], effort: null, time: null, diets: [] }

// ─── Sound Feedback ──────────────────────────────────────────────────────────

function playKitchenChime(type: 'timer' | 'complete' = 'timer') {
  try {
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    if (!AudioContextClass) return
    const ctx = new AudioContextClass()
    const now = ctx.currentTime

    if (type === 'timer') {
      const osc1 = ctx.createOscillator()
      const gain1 = ctx.createGain()
      osc1.type = 'sine'
      osc1.frequency.setValueAtTime(659.25, now) // E5
      gain1.gain.setValueAtTime(0.12, now)
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.35)
      osc1.connect(gain1)
      gain1.connect(ctx.destination)
      osc1.start(now)
      osc1.stop(now + 0.35)

      const osc2 = ctx.createOscillator()
      const gain2 = ctx.createGain()
      osc2.type = 'sine'
      osc2.frequency.setValueAtTime(830.61, now + 0.15) // G#5
      gain2.gain.setValueAtTime(0.15, now + 0.15)
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.6)
      osc2.connect(gain2)
      gain2.connect(ctx.destination)
      osc2.start(now + 0.15)
      osc2.stop(now + 0.6)
    } else if (type === 'complete') {
      const notes = [523.25, 659.25, 783.99, 1046.50]
      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        osc.type = 'triangle'
        osc.frequency.setValueAtTime(freq, now + idx * 0.1)
        gain.gain.setValueAtTime(0.14, now + idx * 0.1)
        gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.1 + 0.45)
        osc.connect(gain)
        gain.connect(ctx.destination)
        osc.start(now + idx * 0.1)
        osc.stop(now + idx * 0.1 + 0.5)
      })
    }
  } catch {
    // Graceful silent fallback if AudioContext cannot start
  }
}

// ─── Data ────────────────────────────────────────────────────────────────────

const PERISHABLE_KEYWORDS = [
  'spinach', 'kale', 'lettuce', 'herb', 'basil', 'cilantro', 'coriander', 'parsley',
  'mint', 'milk', 'cheese', 'paneer', 'yogurt', 'curd', 'cream', 'tomato', 'egg',
  'mushroom', 'berries', 'strawberry', 'avocado', 'fish', 'salmon', 'prawn', 'chicken',
  'beef', 'pork', 'meat', 'tofu'
]

function isPerishable(name: string): boolean {
  const lower = name.toLowerCase()
  return PERISHABLE_KEYWORDS.some(k => lower.includes(k))
}

const EMOJI_MAP: [string, string][] = [
  ['egg', '🥚'], ['milk', '🥛'], ['cheese', '🧀'], ['tomato', '🍅'],
  ['spinach', '🥬'], ['garlic', '🧄'], ['onion', '🧅'], ['bread', '🍞'],
  ['butter', '🧈'], ['carrot', '🥕'], ['broccoli', '🥦'], ['mushroom', '🍄'],
  ['lemon', '🍋'], ['apple', '🍎'], ['banana', '🍌'], ['avocado', '🥑'],
  ['pepper', '🫑'], ['cucumber', '🥒'], ['chicken', '🍗'], ['beef', '🥩'],
  ['pasta', '🍝'], ['rice', '🍚'], ['potato', '🥔'], ['salmon', '🐟'],
  ['shrimp', '🍤'], ['corn', '🌽'], ['pea', '🫛'], ['bean', '🫘'],
  ['olive', '🫒'], ['herb', '🌿'], ['basil', '🌿'], ['parsley', '🌿'],
  ['flour', '🌾'], ['sugar', '🍬'], ['chocolate', '🍫'], ['yogurt', '🥣'],
]

function getEmoji(name: string): string {
  const lower = name.toLowerCase()
  for (const [key, emoji] of EMOJI_MAP) {
    if (lower.includes(key)) return emoji
  }
  return '🥗'
}

const INITIAL_INGREDIENTS: Ingredient[] = [
  { id: 1, name: 'Eggs', qty: '6', emoji: '🥚', shelf: 'use_first', category: 'dairy_eggs' },
  { id: 2, name: 'Milk', qty: '500ml', emoji: '🥛', shelf: 'use_first', category: 'dairy_eggs' },
  { id: 3, name: 'Cheese', qty: '200g', emoji: '🧀', shelf: 'use_first', category: 'dairy_eggs' },
  { id: 4, name: 'Tomatoes', qty: '3', emoji: '🍅', shelf: 'use_first', category: 'produce' },
  { id: 5, name: 'Spinach', qty: '1 bunch', emoji: '🥬', shelf: 'use_first', category: 'produce' },
  { id: 6, name: 'Garlic', qty: '4 cloves', emoji: '🧄', shelf: 'fresh_finds', category: 'aromatics' },
  { id: 7, name: 'Onion', qty: '1', emoji: '🧅', shelf: 'fresh_finds', category: 'aromatics' },
  { id: 8, name: 'Bread', qty: '½ loaf', emoji: '🍞', shelf: 'fresh_finds', category: 'bakery' },
]

const TASTE_OPTIONS = [
  { id: 'spicy',   label: 'Spicy',        emoji: '🌶️', bg: '#FFD5C2' },
  { id: 'savory',  label: 'Savory',       emoji: '🧄', bg: '#C9DCC5' },
  { id: 'sweet',   label: 'Sweet',        emoji: '🍯', bg: '#F5D66F' },
  { id: 'tangy',   label: 'Tangy',        emoji: '🍋', bg: '#F6C8D0' },
  { id: 'creamy',  label: 'Creamy',       emoji: '🥛', bg: '#F6C8D0' },
  { id: 'fresh',   label: 'Fresh & Light',emoji: '🌿', bg: '#C9DCC5' },
  { id: 'comfort', label: 'Comfort Food', emoji: '🫕', bg: '#FFD5C2' },
]

const EFFORT_OPTIONS = [
  { id: 'lazy', label: 'Couch Potato Mode', emoji: '🛋️', desc: 'Zero effort. Maximum chill.' },
  { id: 'easy', label: 'Easy Does It',      emoji: '😊', desc: 'Simple steps, quick wins!' },
  { id: 'chef', label: 'Chef Era!',          emoji: '👨‍🍳', desc: "Let's impress everyone." },
]

const TIME_OPTIONS = ['10 min', '20 min', '30 min', '45 min', 'Any time ⏰']

const DIET_OPTIONS = [
  { id: 'veg',   label: 'Vegetarian',  emoji: '🥦' },
  { id: 'vegan', label: 'Vegan',       emoji: '🌱' },
  { id: 'df',    label: 'Dairy-free',  emoji: '🚫🥛' },
  { id: 'ef',    label: 'Egg-free',    emoji: '🚫🥚' },
  { id: 'gf',    label: 'Gluten-free', emoji: '🌾' },
  { id: 'hp',    label: 'High-protein',emoji: '💪' },
]

const RECIPES: Recipe[] = [
  {
    id: 1,
    name: 'Creamy Tomato Scrambled Eggs',
    time: '12 min', difficulty: 'Easy',
    tags: ['Vegetarian', 'High-protein'],
    desc: 'Silky eggs with burst cherry tomatoes, fresh spinach & gooey melted cheese.',
    image: 'https://images.unsplash.com/photo-1525351484163-7529414344d8?w=600&h=380&fit=crop&auto=format',
    cal: '320 cal', rating: 4.8, match: 98, accent: '#FFD5C2',
    servings: 2,
    badges: ['High Waste Reducer', 'Protein Rich', 'Quick & Easy'],
    matched_ingredients: ['Eggs', 'Tomatoes', 'Spinach', 'Cheese', 'Garlic', 'Milk'],
    missing_ingredients: [],
    ingredients: [
      { name: 'Eggs', amount: 3, unit: '' }, { name: 'Tomatoes', amount: 150, unit: 'g' },
      { name: 'Spinach', amount: 60, unit: 'g' }, { name: 'Cheese', amount: 50, unit: 'g' },
      { name: 'Garlic', amount: 1, unit: 'clove' }, { name: 'Milk', amount: 30, unit: 'ml' },
    ],
    steps: [
      'Whisk the eggs with the milk, a pinch of salt, and plenty of black pepper.',
      'Warm a skillet over medium-low heat. Add the garlic and tomatoes; cook until juicy.',
      'Wilt in the spinach, then pour in the eggs and fold slowly until soft and glossy.',
      'Scatter over the cheese, fold once more, and serve immediately.',
    ],
    stepTimers: [0, 180, 240, 60],
    substitution: 'No spinach? Kale or frozen peas work beautifully here.',
  },
  {
    id: 2,
    name: 'Cheesy Garlic Bruschetta',
    time: '15 min', difficulty: 'Easy',
    tags: ['Vegetarian'],
    desc: 'Crispy toast with golden garlic butter, melted cheese & vine-ripened tomatoes.',
    image: 'https://images.unsplash.com/photo-1572695157366-5e585ab2b69f?w=600&h=380&fit=crop&auto=format',
    cal: '280 cal', rating: 4.6, match: 94, accent: '#F5D66F',
    servings: 2,
    badges: ['Crispy Classic', 'Kid Friendly', 'Snack Alert'],
    matched_ingredients: ['Bread', 'Tomatoes', 'Cheese', 'Garlic', 'Butter'],
    missing_ingredients: ['Basil'],
    ingredients: [
      { name: 'Bread', amount: 4, unit: 'slices' }, { name: 'Tomatoes', amount: 180, unit: 'g' },
      { name: 'Cheese', amount: 80, unit: 'g' }, { name: 'Garlic', amount: 2, unit: 'cloves' },
      { name: 'Butter', amount: 25, unit: 'g' }, { name: 'Basil', amount: 8, unit: 'leaves' },
    ],
    steps: [
      'Heat the oven grill and line a tray. Mix softened butter with the crushed garlic.',
      'Spread the garlic butter over the bread and toast until the edges turn golden.',
      'Top with chopped tomatoes and cheese, then grill until bubbling.',
      'Finish with torn basil, black pepper, and a tiny pinch of salt.',
    ],
    stepTimers: [0, 240, 300, 0],
    substitution: 'No fresh basil? Parsley, oregano, or a spoonful of pesto all work.',
  },
  {
    id: 3,
    name: 'Spinach & Cheese Omelette',
    time: '10 min', difficulty: 'Easy',
    tags: ['Vegetarian', 'Gluten-free', 'High-protein'],
    desc: 'Fluffy omelette filled with wilted spinach, caramelised onions & gooey cheese.',
    image: 'https://images.unsplash.com/photo-1510693206972-df098062cb71?w=600&h=380&fit=crop&auto=format',
    cal: '290 cal', rating: 4.7, match: 91, accent: '#C9DCC5',
    servings: 2,
    badges: ['High Waste Reducer', 'Low Carb', 'Protein Rich'],
    matched_ingredients: ['Eggs', 'Spinach', 'Cheese', 'Onion', 'Milk'],
    missing_ingredients: ['Butter'],
    ingredients: [
      { name: 'Eggs', amount: 4, unit: '' }, { name: 'Spinach', amount: 80, unit: 'g' },
      { name: 'Cheese', amount: 70, unit: 'g' }, { name: 'Onion', amount: 0.5, unit: '' },
      { name: 'Butter', amount: 15, unit: 'g' }, { name: 'Milk', amount: 30, unit: 'ml' },
    ],
    steps: [
      'Whisk the eggs and milk until smooth. Season with salt and pepper.',
      'Soften the onion in butter, then add the spinach and cook until just wilted.',
      'Pour in the eggs. Pull the cooked edges inward until the top is almost set.',
      'Add the cheese, fold the omelette, and rest for one minute before serving.',
    ],
    stepTimers: [0, 240, 240, 60],
    substitution: 'Swap spinach for mushrooms, peas, or any tender greens you have.',
  },
  {
    id: 4,
    name: 'Golden Tomato Milk Soup',
    time: '25 min', difficulty: 'Medium',
    tags: ['Vegetarian', 'Gluten-free'],
    desc: 'Velvety tomato soup made creamy with warm milk, roasted garlic & fresh herbs.',
    image: 'https://images.unsplash.com/photo-1547592166-23ac45744acd?w=600&h=380&fit=crop&auto=format',
    cal: '190 cal', rating: 4.5, match: 87, accent: '#F6C8D0',
    servings: 2,
    badges: ['Comfort Food', 'Zero Waste Hero', 'Warm Bowl'],
    matched_ingredients: ['Tomatoes', 'Milk', 'Garlic', 'Onion'],
    missing_ingredients: ['Butter', 'Basil'],
    ingredients: [
      { name: 'Tomatoes', amount: 500, unit: 'g' }, { name: 'Milk', amount: 250, unit: 'ml' },
      { name: 'Garlic', amount: 2, unit: 'cloves' }, { name: 'Onion', amount: 1, unit: '' },
      { name: 'Butter', amount: 20, unit: 'g' }, { name: 'Basil', amount: 10, unit: 'leaves' },
    ],
    steps: [
      'Chop the tomatoes and onion. Gently crush the garlic.',
      'Melt the butter in a pot and soften the onion and garlic without browning.',
      'Add the tomatoes and simmer until collapsed, then blend until velvety.',
      'Stir in the warm milk over low heat. Season and finish with basil.',
    ],
    stepTimers: [0, 300, 900, 180],
    substitution: 'Use unsweetened oat milk for a dairy-free bowl with the same silky finish.',
  },
]


// ─── SVG Illustrations ────────────────────────────────────────────────────────

function FridgeHeroSVG({ className = '', eyeX = 0, eyeY = 0 }: { className?: string; eyeX?: number; eyeY?: number }) {
  return (
    <svg viewBox="0 0 380 500" fill="none" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden="true">
      {/* Ground shadow */}
      <ellipse cx="190" cy="462" rx="118" ry="16" fill="#E8C050" opacity="0.3" />

      {/* Floating tomato — top left */}
      <g transform="translate(10 48)">
        <circle cx="34" cy="36" r="30" fill="#E97861" />
        <path d="M 25 11 Q 34 2 43 11" fill="#6B9E5E" />
        <path d="M 17 17 Q 22 4 30 11" stroke="#6B9E5E" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <path d="M 43 17 Q 46 4 38 11" stroke="#6B9E5E" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <ellipse cx="22" cy="34" rx="6" ry="7" fill="#C43F2B" opacity="0.35" />
      </g>

      {/* Floating carrot — top right */}
      <g transform="translate(304 18)">
        <path d="M 12 72 Q 24 16 36 16 Q 48 16 60 72 Z" fill="#E97861" />
        <path d="M 16 32 Q 24 10 36 18" stroke="#6B9E5E" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <path d="M 34 18 Q 36 6 38 18" stroke="#6B9E5E" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <path d="M 46 32 Q 44 10 36 18" stroke="#6B9E5E" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <line x1="14" y1="40" x2="30" y2="35" stroke="#C43F2B" strokeWidth="1.5" opacity="0.45" />
        <line x1="13" y1="52" x2="29" y2="47" stroke="#C43F2B" strokeWidth="1.5" opacity="0.45" />
        <line x1="14" y1="64" x2="30" y2="59" stroke="#C43F2B" strokeWidth="1.5" opacity="0.45" />
      </g>

      {/* Strawberry — bottom left */}
      <g transform="translate(8 308)">
        <path d="M 10 24 Q 32 8 54 24 Q 54 56 32 68 Q 10 56 10 24Z" fill="#E97861" />
        <path d="M 20 24 Q 32 10 44 24" fill="#6B9E5E" />
        <circle cx="26" cy="36" r="2.5" fill="#FFFCF4" opacity="0.7" />
        <circle cx="38" cy="28" r="2.5" fill="#FFFCF4" opacity="0.7" />
        <circle cx="34" cy="46" r="2" fill="#FFFCF4" opacity="0.7" />
        <circle cx="44" cy="38" r="2" fill="#FFFCF4" opacity="0.7" />
      </g>

      {/* Mushroom — bottom right */}
      <g transform="translate(308 318)">
        <rect x="14" y="34" width="22" height="30" rx="5" fill="#FFFCF4" stroke="#F6C8D0" strokeWidth="1.5" />
        <ellipse cx="25" cy="34" rx="30" ry="18" fill="#F6C8D0" />
        <ellipse cx="25" cy="34" rx="22" ry="13" fill="#EDA8BC" />
        <circle cx="16" cy="28" r="3.5" fill="#FFFCF4" opacity="0.65" />
        <circle cx="29" cy="25" r="3" fill="#FFFCF4" opacity="0.65" />
      </g>

      {/* Pasta swirls — right */}
      <g transform="translate(338 208)">
        <path d="M 6 0 Q 18 12 6 24 Q 18 36 6 48" stroke="#F5D66F" strokeWidth="3.5" fill="none" strokeLinecap="round" />
        <path d="M 18 4 Q 30 16 18 28 Q 30 40 18 52" stroke="#E8C050" strokeWidth="3.5" fill="none" strokeLinecap="round" />
        <path d="M 30 0 Q 42 12 30 24 Q 42 36 30 48" stroke="#F5D66F" strokeWidth="3.5" fill="none" strokeLinecap="round" />
      </g>

      {/* Sparkle star — right upper */}
      <path d="M 302 166 L 308 154 L 314 166 L 326 172 L 314 178 L 308 190 L 302 178 L 290 172 Z" fill="#F5D66F" opacity="0.85" />
      {/* Dot clusters */}
      <circle cx="34" cy="178" r="8" fill="#F5D66F" opacity="0.55" />
      <circle cx="356" cy="268" r="5" fill="#F5D66F" opacity="0.65" />
      {/* Hearts & doodles */}
      <text x="344" y="134" fontSize="24" fill="#F6C8D0" fontFamily="sans-serif" opacity="0.9">♥</text>
      <text x="18" y="262" fontSize="20" fill="#C9DCC5" fontFamily="sans-serif" opacity="0.9">✦</text>
      <text x="318" y="300" fontSize="15" fill="#F5D66F" fontFamily="sans-serif">⭐</text>
      <text x="52" y="396" fontSize="14" fill="#E97861" fontFamily="sans-serif" opacity="0.6">♥</text>

      {/* ── Main fridge body ── */}
      <rect x="72" y="56" width="236" height="370" rx="34" fill="#FFD5C2" />
      <rect x="74" y="58" width="232" height="366" rx="32" fill="#FFD5C2" stroke="#F5AAAE" strokeWidth="1.5" />

      {/* Freezer section */}
      <rect x="74" y="58" width="232" height="140" rx="32" fill="#F6C8D0" />
      {/* Divider bar */}
      <rect x="74" y="180" width="232" height="22" fill="#EEACC0" />

      {/* Lower fridge */}
      <rect x="74" y="202" width="232" height="222" fill="#FFD5C2" />
      <rect x="74" y="394" width="232" height="32" rx="32" fill="#FFD5C2" />

      {/* Door centre crease */}
      <line x1="190" y1="58" x2="190" y2="426" stroke="#EDA8B8" strokeWidth="2" strokeDasharray="6 5" opacity="0.55" />

      {/* Handles */}
      <rect x="274" y="94" width="16" height="60" rx="8" fill="#E97861" />
      <rect x="274" y="248" width="16" height="74" rx="8" fill="#E97861" />

      {/* ── Face ── */}
      {/* Eye whites */}
      <circle cx="146" cy="118" r="23" fill="white" />
      <circle cx="214" cy="118" r="23" fill="white" />
      {/* Pupils */}
      <circle cx={150 + eyeX} cy={122 + eyeY} r="13" fill="#394331" className="transition-all duration-150" />
      <circle cx={218 + eyeX} cy={122 + eyeY} r="13" fill="#394331" className="transition-all duration-150" />
      {/* Shine */}
      <circle cx={156 + eyeX} cy={115 + eyeY} r="5" fill="white" className="transition-all duration-150" />
      <circle cx={224 + eyeX} cy={115 + eyeY} r="5" fill="white" className="transition-all duration-150" />
      <circle cx={147 + eyeX} cy={127 + eyeY} r="2.5" fill="white" className="transition-all duration-150" />
      <circle cx={215 + eyeX} cy={127 + eyeY} r="2.5" fill="white" className="transition-all duration-150" />
      {/* Smile */}
      <path d="M 157 148 Q 180 167 203 148" stroke="#394331" strokeWidth="5" strokeLinecap="round" fill="none" />
      {/* Blush */}
      <circle cx="124" cy="148" r="18" fill="#E97861" opacity="0.2" />
      <circle cx="236" cy="148" r="18" fill="#E97861" opacity="0.2" />

      {/* ── Food inside lower fridge ── */}
      {/* Milk carton */}
      <rect x="90" y="228" width="42" height="66" rx="9" fill="white" stroke="#C9DCC5" strokeWidth="1.5" />
      <rect x="90" y="228" width="42" height="24" rx="9" fill="#C9DCC5" />
      <text x="111" y="290" textAnchor="middle" fontSize="14" fill="#394331">🥛</text>
      {/* Egg */}
      <ellipse cx="170" cy="265" rx="22" ry="27" fill="#FFF9E9" stroke="#F5D66F" strokeWidth="1.5" />
      <ellipse cx="170" cy="263" rx="12" ry="15" fill="#F5D66F" opacity="0.55" />
      {/* Broccoli */}
      <ellipse cx="222" cy="238" rx="18" ry="17" fill="#C9DCC5" />
      <ellipse cx="235" cy="231" rx="15" ry="14" fill="#A8C9A4" />
      <ellipse cx="209" cy="231" rx="14" ry="13" fill="#A8C9A4" />
      <rect x="215" y="253" width="14" height="18" rx="5" fill="#8BB885" />
      {/* Cheese wedge */}
      <path d="M 92 325 L 162 305 L 175 352 L 92 352 Z" fill="#F5D66F" />
      <circle cx="114" cy="336" r="6" fill="#E8C050" />
      <circle cx="140" cy="325" r="5" fill="#E8C050" />
      <circle cx="154" cy="342" r="4" fill="#E8C050" />

      {/* Stars on divider */}
      <circle cx="96" cy="191" r="5" fill="#F5D66F" />
      <circle cx="152" cy="189" r="3.5" fill="#F5D66F" />
      <circle cx="228" cy="191" r="5" fill="#F5D66F" />
      <circle cx="276" cy="189" r="3.5" fill="#F5D66F" />

      {/* Feet */}
      <rect x="106" y="421" width="40" height="18" rx="9" fill="#EDA8B0" />
      <rect x="234" y="421" width="40" height="18" rx="9" fill="#EDA8B0" />
    </svg>
  )
}

function SmallFridgeSVG() {
  return (
    <svg viewBox="0 0 130 170" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-28 h-36" aria-hidden="true">
      <rect x="10" y="8" width="110" height="152" rx="22" fill="#FFD5C2" />
      <rect x="10" y="8" width="110" height="70" rx="22" fill="#F6C8D0" />
      <rect x="10" y="72" width="110" height="14" fill="#EEACC0" />
      <rect x="94" y="28" width="12" height="36" rx="6" fill="#E97861" />
      <rect x="94" y="100" width="12" height="42" rx="6" fill="#E97861" />
      <circle cx="52" cy="46" r="11" fill="white" />
      <circle cx="78" cy="46" r="11" fill="white" />
      <circle cx="54" cy="48" r="6" fill="#394331" />
      <circle cx="80" cy="48" r="6" fill="#394331" />
      <circle cx="57" cy="45" r="2.5" fill="white" />
      <circle cx="83" cy="45" r="2.5" fill="white" />
      <path d="M 54 60 Q 65 70 76 60" stroke="#394331" strokeWidth="2.5" strokeLinecap="round" fill="none" />
      <circle cx="36" cy="60" r="9" fill="#E97861" opacity="0.2" />
      <circle cx="94" cy="60" r="9" fill="#E97861" opacity="0.2" />
      {/* Camera badge */}
      <circle cx="100" cy="145" r="22" fill="#E97861" />
      <rect x="90" y="137" width="20" height="16" rx="4" fill="white" />
      <circle cx="100" cy="145" r="6" fill="#E97861" />
      <circle cx="100" cy="145" r="3" fill="white" />
      <rect x="97" y="135" width="6" height="4" rx="1.5" fill="white" />
    </svg>
  )
}

function BowlSVG() {
  return (
    <svg viewBox="0 0 130 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-28 h-24" aria-hidden="true">
      <ellipse cx="65" cy="62" rx="56" ry="34" fill="#F6C8D0" />
      <path d="M 9 62 Q 9 96 65 96 Q 121 96 121 62 Z" fill="#E9A8B8" />
      <ellipse cx="65" cy="62" rx="56" ry="16" fill="#F6C8D0" stroke="#E9A8B8" strokeWidth="2" />
      <ellipse cx="65" cy="62" rx="48" ry="10" fill="#FFF9E9" />
      {/* Coloured dots in bowl */}
      <circle cx="48" cy="60" r="4.5" fill="#F5D66F" />
      <circle cx="64" cy="58" r="4" fill="#FFD5C2" />
      <circle cx="78" cy="60" r="4.5" fill="#C9DCC5" />
      <circle cx="65" cy="65" r="3" fill="#F5D66F" />
      {/* Spoon */}
      <ellipse cx="108" cy="42" rx="10" ry="8" fill="#F5D66F" />
      <rect x="106" y="37" width="6" height="38" rx="3" fill="#F5D66F" transform="rotate(14 109 56)" />
      {/* Steam lines */}
      <path d="M 40 42 Q 37 34 40 26 Q 43 18 40 11" stroke="#C9DCC5" strokeWidth="2.5" strokeLinecap="round" fill="none" opacity="0.7" />
      <path d="M 57 38 Q 54 30 57 22 Q 60 14 57 7" stroke="#C9DCC5" strokeWidth="2.5" strokeLinecap="round" fill="none" opacity="0.7" />
    </svg>
  )
}

// ─── Shared components ────────────────────────────────────────────────────────

function IngredientIcon({ name, className = '' }: { name: string; className?: string }) {
  const lower = name.toLowerCase()
  if (lower.includes('egg')) {
    return <svg viewBox="0 0 48 48" className={className} aria-hidden="true"><path d="M24 5C15 5 9 20 9 29c0 9 6 14 15 14s15-5 15-14C39 20 33 5 24 5Z" fill="#FFF9E9" stroke="#394331" strokeWidth="2"/><circle cx="24" cy="29" r="8" fill="#F5D66F"/></svg>
  }
  if (lower.includes('tomato')) {
    return <svg viewBox="0 0 48 48" className={className} aria-hidden="true"><circle cx="24" cy="27" r="16" fill="#E97861" stroke="#394331" strokeWidth="2"/><path d="m24 12 4-6 1 7 7-1-5 6-7-3-7 3-5-6 7 1 1-7 4 6Z" fill="#7FA875" stroke="#394331" strokeWidth="1.5"/></svg>
  }
  if (lower.includes('spinach') || lower.includes('herb') || lower.includes('basil')) {
    return <svg viewBox="0 0 48 48" className={className} aria-hidden="true"><path d="M39 8C18 9 8 20 10 34c9 4 24 0 29-26Z" fill="#9FC69A" stroke="#394331" strokeWidth="2"/><path d="M12 38c5-10 12-16 22-23" stroke="#394331" strokeWidth="2" strokeLinecap="round"/></svg>
  }
  if (lower.includes('cheese')) {
    return <svg viewBox="0 0 48 48" className={className} aria-hidden="true"><path d="M7 22 36 8l6 29H7V22Z" fill="#F5D66F" stroke="#394331" strokeWidth="2" strokeLinejoin="round"/><circle cx="27" cy="23" r="4" fill="#E3B93D"/><circle cx="16" cy="31" r="3" fill="#E3B93D"/></svg>
  }
  if (lower.includes('milk') || lower.includes('yogurt')) {
    return <svg viewBox="0 0 48 48" className={className} aria-hidden="true"><path d="M14 14h20l4 7v21H10V21l4-7Z" fill="#FFFCF4" stroke="#394331" strokeWidth="2"/><path d="M14 14l5-8h10l5 8H14Z" fill="#C9DCC5" stroke="#394331" strokeWidth="2"/><path d="M10 25h28v9H10z" fill="#F6C8D0"/></svg>
  }
  return <svg viewBox="0 0 48 48" className={className} aria-hidden="true"><path d="M24 42C14 36 8 29 9 19c9-2 14 1 17 8 0-9 5-15 14-18 3 16-3 28-16 33Z" fill="#C9DCC5" stroke="#394331" strokeWidth="2" strokeLinejoin="round"/><path d="M24 39c1-10 5-18 12-25M23 35c-2-7-6-11-11-13" stroke="#394331" strokeWidth="1.8" strokeLinecap="round"/></svg>
}

function PersistentFridge({ screen, ingredientCount }: { screen: Screen; ingredientCount: number }) {
  if (screen === 'home') return null
  const isThinking = screen === 'vibe'
  const isProud = screen === 'results' || screen === 'recipe'
  return (
    <div className={`persistent-fridge fridge-${screen}`} aria-hidden="true">
      <svg viewBox="0 0 120 150">
        {screen === 'recipe' && <path d="M27 24c8-18 26-20 33-8 9-13 27-8 30 8H27Z" fill="#FFFCF4" stroke="#394331" strokeWidth="2.5"/>}
        <rect x="20" y="24" width="80" height="112" rx="18" fill="#FFD5C2" stroke="#394331" strokeWidth="3"/>
        <path d="M20 75h80" stroke="#394331" strokeWidth="3"/>
        <path d="M86 42v21M86 89v26" stroke="#E97861" strokeWidth="7" strokeLinecap="round"/>
        {isProud ? (
          <><path d="M38 49h13M67 49q7-8 14 0" stroke="#394331" strokeWidth="3" strokeLinecap="round"/><path d="M45 61q15 13 30 0" stroke="#394331" strokeWidth="3" fill="none" strokeLinecap="round"/></>
        ) : isThinking ? (
          <><circle cx="46" cy="50" r="4" fill="#394331"/><circle cx="74" cy="46" r="4" fill="#394331"/><path d="M49 64q11-5 22 0" stroke="#394331" strokeWidth="3" fill="none" strokeLinecap="round"/></>
        ) : (
          <><circle cx="46" cy="50" r="4" fill="#394331"/><circle cx="74" cy="50" r="4" fill="#394331"/><path d="M48 61q12 11 24 0" stroke="#394331" strokeWidth="3" fill="none" strokeLinecap="round"/></>
        )}
        {Array.from({ length: Math.min(ingredientCount, 8) }).map((_, index) => (
          <circle key={index} cx={36 + (index % 4) * 15} cy={92 + Math.floor(index / 4) * 18} r="5" fill={CHIP_COLORS[index % CHIP_COLORS.length]} stroke="#394331" strokeWidth="1"/>
        ))}
      </svg>
    </div>
  )
}

function SceneWipe({ screen }: { screen: Screen }) {
  return (
    <div key={screen} className={`scene-wipe wipe-${screen}`} aria-hidden="true">
      <div className="wipe-door wipe-left" />
      <div className="wipe-door wipe-right" />
      <span>{screen === 'results' ? '✦' : screen === 'recipe' ? '♨' : '•'}</span>
    </div>
  )
}

function PageHeader({ onBack, label }: { onBack: () => void; label: string }) {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)

  useEffect(() => {
    let isMounted = true
    checkApiHealth().then(res => {
      if (isMounted) setApiOnline(!!res)
    }).catch(() => {
      if (isMounted) setApiOnline(false)
    })
    return () => { isMounted = false }
  }, [])

  const stepMatch = label.match(/\d/)
  const step = stepMatch ? Number(stepMatch[0]) : null
  return (
    <header className="app-header sticky top-0 z-50 flex items-center gap-4 px-5 md:px-12 py-4">
      <button
        onClick={onBack}
        className="header-back flex items-center gap-1.5 bg-cream text-olive font-body font-bold px-4 py-2 rounded-full text-sm border-2 border-olive/10 hover:bg-peach transition-all"
      >
        ← Back
      </button>
      <div className="flex items-center gap-2">
        <span className="brand-mark" aria-hidden="true">F</span>
        <span className="font-heading text-xl font-semibold text-olive">FridgeMind</span>
      </div>

      {apiOnline !== null && (
        <span
          title={apiOnline ? 'FastAPI backend active: Live SQLite FTS5 search & ML enabled' : 'Operating in resilient offline mode with built-in culinary catalog'}
          className={`hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-body font-bold border shadow-2xs transition-all ${
            apiOnline
              ? 'bg-[#C9DCC5]/70 text-olive border-[#A3C29E]'
              : 'bg-[#F5D66F]/45 text-olive border-[#F5D66F]'
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${apiOnline ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
          {apiOnline ? 'AI Connected' : 'Offline Mode'}
        </span>
      )}

      {step ? (
        <div className="ml-auto hidden sm:flex items-center gap-2" aria-label={label}>
          {[1, 2, 3, 4].map(item => (
            <span key={item} className={`step-dot ${item <= step ? 'is-active' : ''}`}>{item}</span>
          ))}
        </div>
      ) : (
        <span className="ml-auto font-body text-xs text-olive/50 font-extrabold uppercase tracking-widest">{label}</span>
      )}
      {step && <span className="sm:hidden ml-auto font-body text-xs text-olive/50 font-extrabold uppercase tracking-widest">{label}</span>}
    </header>
  )
}

function AmbientKitchen() {
  return (
    <div className="ambient-kitchen" aria-hidden="true">
      <span className="ambient-shape shape-one">🍅</span>
      <span className="ambient-shape shape-two">✦</span>
      <span className="ambient-shape shape-three">🥕</span>
      <span className="ambient-shape shape-four">〜</span>
      <span className="ambient-shape shape-five">🍋</span>
      <span className="ambient-shape shape-six">✿</span>
    </div>
  )
}

function DoodleSprinkles() {
  return (
    <div className="doodle-sprinkles" aria-hidden="true">
      <span>✦</span><span>♡</span><span>〜</span><span>✿</span><span>✦</span>
    </div>
  )
}

// ─── Screen 1: Home ───────────────────────────────────────────────────────────

function HomeScreen({ onNavigate }: { onNavigate: (s: Screen) => void }) {
  const [eyes, setEyes] = useState({ x: 0, y: 0 })

  return (
    <div className="experience-shell screen-enter min-h-screen bg-butter flex flex-col paper-texture">
      {/* NAV */}
      <nav className="app-header sticky top-0 z-50 px-6 md:px-12 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="brand-mark" aria-hidden="true">F</span>
          <span className="font-heading text-[1.6rem] font-semibold text-olive tracking-wide">FridgeMind</span>
        </div>
        <div className="flex items-center gap-6">
          <a href="#how" className="hidden md:block font-body text-olive/55 hover:text-olive transition-colors font-semibold text-sm">
            How it works ↓
          </a>
          <button
            onClick={() => onNavigate('input')}
            className="bg-tomato text-white font-body font-bold px-5 py-2.5 rounded-full hover:bg-[#D4614F] transition-all hover:scale-105 shadow-md text-sm"
          >
            Let's Cook! 🍳
          </button>
        </div>
      </nav>

      {/* HERO */}
      <section className="hero-section flex-1 px-6 md:px-12 lg:px-20 pt-12 md:pt-16 pb-12">
        <div className="max-w-7xl mx-auto grid md:grid-cols-2 gap-8 lg:gap-16 items-center min-h-[540px]">
          {/* Left text */}
          <div className="hero-copy space-y-6 order-2 md:order-1 relative">
            <div className="inline-flex items-center gap-2 bg-sage/50 border border-sage text-olive px-4 py-1.5 rounded-full font-body font-bold text-[0.7rem] tracking-[0.12em] uppercase">
              ✨ Your AI Cooking Buddy
            </div>
            <h1 className="font-heading text-5xl md:text-[3.8rem] lg:text-[4.4rem] font-semibold text-olive leading-[1.08] tracking-tight">
              Your fridge has<br />
              <span className="text-tomato italic">secrets.</span><br />
              Let's make dinner.
            </h1>
            <p className="font-body text-olive/65 text-lg leading-relaxed max-w-md">
              Show us what's hiding in your kitchen, pick your vibe, and let's turn those random ingredients into something{' '}
              <strong className="text-olive font-extrabold">absolutely delicious!</strong> 🍳
            </p>
            <div className="flex flex-wrap gap-3 pt-1">
              <button
                onClick={() => onNavigate('input')}
                className="bg-olive text-butter font-body font-bold px-8 py-4 rounded-2xl text-lg hover:scale-[1.03] active:scale-[0.97] transition-transform shadow-lg"
              >
                Let's Cook! →
              </button>
              <button
                onClick={() => onNavigate('results')}
                className="bg-yellow text-olive font-body font-bold px-8 py-4 rounded-2xl text-lg hover:scale-[1.03] active:scale-[0.97] transition-transform border-2 border-olive/10 shadow-sm"
              >
                Surprise Me! ✨
              </button>
            </div>
            <div className="flex items-center gap-3 pt-1">
              <div className="flex -space-x-2">
                {['🧑‍🍳', '👩‍🍳', '🧑', '👩'].map((e, i) => (
                  <div key={i} className="w-9 h-9 rounded-full bg-peach border-2 border-butter flex items-center justify-center text-sm shadow-sm">{e}</div>
                ))}
              </div>
              <span className="font-body text-sm text-olive/50 font-semibold">2,847 meals cooked today!</span>
            </div>
          </div>

          {/* Right illustration */}
          <div
            className="hero-illustration flex justify-center items-center relative order-1 md:order-2"
            onMouseMove={event => {
              const rect = event.currentTarget.getBoundingClientRect()
              setEyes({
                x: Math.max(-5, Math.min(5, (event.clientX - rect.left - rect.width / 2) / 35)),
                y: Math.max(-4, Math.min(4, (event.clientY - rect.top - rect.height / 2) / 45)),
              })
            }}
            onMouseLeave={() => setEyes({ x: 0, y: 0 })}
          >
            <div
              className="absolute inset-0 rounded-[50%_42%_58%_46%/46%_54%_42%_58%] opacity-55"
              style={{ background: 'radial-gradient(ellipse at 50% 50%, #FFD5C2 0%, #FFF1B8 65%, transparent 100%)' }}
            />
            <FridgeHeroSVG eyeX={eyes.x} eyeY={eyes.y} className="w-full max-w-[320px] md:max-w-[390px] relative z-10 fridge-float" />
            <DoodleSprinkles />
          </div>
        </div>
      </section>

      <div className="ingredient-marquee" aria-hidden="true">
        <div className="marquee-track">
          <span>FRESH IDEAS</span><i>✦</i><span>ZERO WASTE</span><i>🍅</i><span>COOK YOUR MOOD</span><i>✿</i>
          <span>FRESH IDEAS</span><i>✦</i><span>ZERO WASTE</span><i>🍅</i><span>COOK YOUR MOOD</span><i>✿</i>
        </div>
      </div>

      {/* HOW IT WORKS */}
      <section id="how" className="px-6 md:px-12 lg:px-20 py-16 bg-vanilla">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <span className="inline-block font-body font-bold text-[0.7rem] uppercase tracking-[0.12em] text-tomato bg-pink/40 px-4 py-1.5 rounded-full mb-4 border border-pink">
              The Magic
            </span>
            <h2 className="font-heading text-4xl md:text-5xl font-semibold text-olive">
              Three easy steps ✨
            </h2>
            <p className="font-body text-olive/50 mt-2 text-lg">From empty fridge to dinner table in minutes</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { n: '01', emoji: '📸', title: 'Scan or type', desc: 'Upload a fridge photo or just tell us which ingredients you have on hand.' },
              { n: '02', emoji: '🎨', title: 'Pick your vibe', desc: 'Spicy or sweet? Lazy mode or chef era? Vegetarian or high-protein? You decide.' },
              { n: '03', emoji: '🍽️', title: 'Get inspired!', desc: "FridgeMind whips up personalised recipes tailored exactly to you and your pantry." },
            ].map(({ n, emoji, title, desc }) => (
              <div key={n} className="scrap-card relative bg-cream rounded-3xl p-8 border border-yellow/30 shadow-sm hover:shadow-md transition-shadow overflow-hidden group">
                <span className="absolute top-5 right-6 font-heading text-[5rem] text-yellow/35 font-semibold leading-none select-none group-hover:text-yellow/50 transition-colors">{n}</span>
                <div className="text-5xl mb-4">{emoji}</div>
                <h3 className="font-heading text-2xl font-semibold text-olive mb-2">{title}</h3>
                <p className="font-body text-olive/55 leading-relaxed text-sm">{desc}</p>
              </div>
            ))}
          </div>
          <div className="text-center mt-12">
            <button
              onClick={() => onNavigate('input')}
              className="bg-tomato text-white font-body font-bold px-10 py-4 rounded-2xl text-lg hover:bg-[#D4614F] hover:scale-[1.03] transition-all shadow-lg"
            >
              Start cooking now →
            </button>
          </div>
        </div>
      </section>

      {/* TESTIMONIAL STRIP */}
      <section className="px-6 md:px-12 lg:px-20 py-12 bg-peach/30">
        <div className="max-w-5xl mx-auto">
          <div className="grid md:grid-cols-3 gap-5">
            {[
              { quote: "Made the best omelette of my life from random leftovers!", name: 'Priya K.', emoji: '🥚' },
              { quote: "The Surprise Me! button is dangerously fun. I'm obsessed.", name: 'Marcus T.', emoji: '🍝' },
              { quote: "Finally stopped wasting food. FridgeMind is a game changer.", name: 'Yuna L.', emoji: '🥦' },
            ].map(({ quote, name, emoji }) => (
              <div key={name} className="bg-cream rounded-2xl p-6 border border-yellow/30 shadow-sm">
                <div className="text-3xl mb-3">{emoji}</div>
                <p className="font-body text-olive/70 text-sm leading-relaxed mb-4 italic">"{quote}"</p>
                <p className="font-body font-bold text-olive text-sm">— {name}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="px-6 md:px-12 py-6 bg-vanilla border-t border-yellow/30 text-center">
        <p className="font-body text-olive/40 text-sm">Made with 🧡 by FridgeMind &nbsp;·&nbsp; Your kitchen, your mood, your next meal.</p>
      </footer>
    </div>
  )
}

// ─── Screen 2: Input method ───────────────────────────────────────────────────

function InputScreen({ onNavigate, onContinue }: { onNavigate: (s: Screen) => void; onContinue: (items: Ingredient[]) => void }) {
  const [method, setMethod] = useState<'scan' | 'type' | null>(null)
  const [newItem, setNewItem] = useState('')
  const [typed, setTyped] = useState<string[]>([])
  const [dragging, setDragging] = useState(false)
  const [uploaded, setUploaded] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [normalizing, setNormalizing] = useState(false)
  const [scannedItems, setScannedItems] = useState<Ingredient[] | null>(null)

  function addItem() {
    const v = newItem.trim()
    if (v && !typed.some(item => item.toLowerCase() === v.toLowerCase())) {
      setTyped(p => [...p, v])
      setNewItem('')
      setMethod('type')
    }
  }

  async function handleFileScan(file: File) {
    setMethod('scan')
    setScanning(true)
    try {
      const res = await recognizeFridgePhoto(file)
      setScannedItems(res.ingredients)
    } finally {
      setScanning(false)
      setUploaded(true)
    }
  }

  async function continueToIngredients() {
    if (method === 'type' && typed.length) {
      setNormalizing(true)
      try {
        const normalized = await normalizeManualIngredients(typed)
        onContinue(normalized)
      } finally {
        setNormalizing(false)
      }
      return
    }
    if (method === 'scan' && uploaded) {
      onContinue(scannedItems || [
        ...INITIAL_INGREDIENTS,
        { id: 9, name: 'Carrots', qty: '3', emoji: '🥕', shelf: 'fresh_finds' },
        { id: 10, name: 'Mushrooms', qty: '200g', emoji: '🍄', shelf: 'use_first' },
        { id: 11, name: 'Lemon', qty: '1', emoji: '🍋', shelf: 'fresh_finds' },
        { id: 12, name: 'Butter', qty: '100g', emoji: '🧈', shelf: 'fresh_finds' },
      ])
    }
  }

  const canContinue = method === 'type' ? typed.length > 0 : method === 'scan' && uploaded

  return (
    <div className="experience-shell screen-enter min-h-screen bg-butter flex flex-col paper-texture">
      <PageHeader onBack={() => onNavigate('home')} label="Step 1 of 4" />

      <div className="flex-1 px-6 md:px-12 lg:px-20 py-10">
        <div className="max-w-5xl mx-auto">
          <div className="screen-title text-center mb-10">
            <h1 className="font-heading text-4xl md:text-5xl font-semibold text-olive mb-3">
              What's hiding in your kitchen? 🔍
            </h1>
            <p className="font-body text-olive/60 text-lg">Choose how you'd like to share your ingredients with us!</p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Card A — Scan */}
            <div
              onClick={() => setMethod('scan')}
              className={`polaroid-card bg-cream rounded-3xl p-7 border-2 cursor-pointer transition-all hover:shadow-lg ${method === 'scan' ? 'border-tomato shadow-lg shadow-tomato/10 ring-2 ring-tomato/20' : 'border-yellow/40 hover:border-peach'}`}
            >
              <div className="flex justify-center mb-4">
                <SmallFridgeSVG />
              </div>
              <h2 className="font-heading text-2xl font-semibold text-olive mb-1.5">Scan my kitchen</h2>
              <p className="font-body text-olive/55 text-sm mb-5">Got a fridge pic? Let's take a peek!</p>

              <div
                className={`fridge-drop border-2 border-dashed rounded-2xl p-8 text-center transition-all ${dragging ? 'border-tomato bg-peach/30 is-open' : 'border-yellow/55 bg-vanilla/70 hover:border-yellow hover:bg-vanilla'}`}
                onDragEnter={() => { setDragging(true); setMethod('scan') }}
                onDragLeave={() => setDragging(false)}
                onDrop={e => {
                  e.preventDefault()
                  setDragging(false)
                  const file = e.dataTransfer.files?.[0]
                  if (file) handleFileScan(file)
                  else { setUploaded(true); setMethod('scan') }
                }}
                onDragOver={e => e.preventDefault()}
              >
                {uploaded ? (
                  <div className="space-y-2">
                    <div className="text-4xl success-pop">✨</div>
                    <p className="font-body font-bold text-olive text-sm">
                      Your fridge is looking fabulous. We spotted {scannedItems ? scannedItems.length : 12} ingredients!
                    </p>
                  </div>
                ) : scanning ? (
                  <div className="space-y-2">
                    <div className="text-4xl animate-bounce">🔍</div>
                    <p className="font-body font-bold text-olive text-sm">
                      Consulting the tiny chefs… Scanning your kitchen!
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="text-4xl mb-2.5">📸</div>
                    <p className="font-body text-olive/50 text-sm mb-3">Drag & drop your fridge photo here</p>
                    <label className="inline-block bg-tomato text-white font-body font-bold px-5 py-2.5 rounded-xl text-sm hover:bg-[#D4614F] transition-colors cursor-pointer">
                      Upload a photo 📸
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={e => {
                          const file = e.target.files?.[0]
                          if (file) handleFileScan(file)
                          else { setUploaded(true); setMethod('scan') }
                        }}
                      />
                    </label>
                    <p className="font-body text-olive/30 text-xs mt-2.5">PNG, JPG, WEBP up to 10 MB</p>
                  </>
                )}
              </div>
            </div>


            {/* Card B — Type */}
            <div
              onClick={() => setMethod('type')}
              className={`scrap-card bg-cream rounded-3xl p-7 border-2 cursor-pointer transition-all hover:shadow-lg ${method === 'type' ? 'border-tomato shadow-lg shadow-tomato/10 ring-2 ring-tomato/20' : 'border-yellow/40 hover:border-peach'}`}
            >
              <div className="flex justify-center mb-4">
                <BowlSVG />
              </div>
              <h2 className="font-heading text-2xl font-semibold text-olive mb-1.5">I'll type it!</h2>
              <p className="font-body text-olive/55 text-sm mb-5">Know what you've got? Pop it in!</p>

              <div className="space-y-3" onClick={e => e.stopPropagation()}>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newItem}
                    onChange={e => {
                      setNewItem(e.target.value)
                      setMethod('type')
                    }}
                    onKeyDown={e => e.key === 'Enter' && addItem()}
                    placeholder="e.g. eggs, cheese, broccoli…"
                    className="flex-1 bg-vanilla border border-yellow/50 rounded-xl px-4 py-3 font-body text-olive placeholder-olive/30 text-sm outline-none focus:border-tomato focus:ring-2 focus:ring-tomato/20 transition-all"
                  />
                  <button
                    onClick={addItem}
                    className="bg-olive text-butter font-body font-bold px-4 py-3 rounded-xl text-sm hover:bg-[#4A5740] transition-colors whitespace-nowrap"
                  >
                    Add +
                  </button>
                </div>
                {typed.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {typed.map((item, i) => (
                      <span key={i} className="ingredient-pop inline-flex items-center gap-1.5 bg-yellow/55 text-olive font-body font-semibold text-xs px-3 py-1.5 rounded-full border border-yellow/60">
                        {getEmoji(item)} {item}
                        <button onClick={e => { e.stopPropagation(); setTyped(p => p.filter((_, j) => j !== i)) }} className="text-olive/40 hover:text-tomato transition-colors">×</button>
                      </span>
                    ))}
                  </div>
                )}
                <p className="font-body text-olive/30 text-xs">Press Enter or click Add to add each ingredient</p>
              </div>
            </div>
          </div>

          <div className="mt-8 text-center">
            <button
              onClick={continueToIngredients}
              disabled={!canContinue || normalizing}
              className="bg-olive text-butter font-body font-bold px-10 py-4 rounded-2xl text-lg hover:scale-[1.03] active:scale-[0.97] transition-transform shadow-lg disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:transform-none"
            >
              {normalizing ? 'Normalizing ingredients… 🥬' : 'Looks good, continue →'}
            </button>
            <p className="font-body text-olive/50 text-xs mt-3" aria-live="polite">
              {normalizing ? 'Matching ingredients to catalog & perishability shelves…' : canContinue ? 'You can edit your ingredient list in the next step' : 'Add an ingredient or upload a photo to continue'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Screen 3: Ingredients ───────────────────────────────────────────────────

const CHIP_COLORS = ['#FFD5C2', '#F6C8D0', '#C9DCC5', '#F5D66F']
const QUICK_ADDS = [
  { name: 'Butter', emoji: '🧈' }, { name: 'Carrots', emoji: '🥕' },
  { name: 'Mushrooms', emoji: '🍄' }, { name: 'Red Pepper', emoji: '🫑' },
  { name: 'Avocado', emoji: '🥑' }, { name: 'Lemon', emoji: '🍋' },
  { name: 'Olive Oil', emoji: '🫒' }, { name: 'Pasta', emoji: '🍝' },
]

function IngredientsScreen({ onNavigate, ingredients, setIngredients }: { onNavigate: (s: Screen) => void; ingredients: Ingredient[]; setIngredients: React.Dispatch<React.SetStateAction<Ingredient[]>> }) {
  const [newName, setNewName] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [departingId, setDepartingId] = useState<number | null>(null)
  const [draggingId, setDraggingId] = useState<number | null>(null)
  const nextId = useRef(Math.max(0, ...ingredients.map(item => item.id)) + 1)

  function add(name?: string, emoji?: string) {
    const n = (name ?? newName).trim()
    if (!n || ingredients.some(item => item.name.toLowerCase() === n.toLowerCase())) return
    const shelf: 'use_first' | 'fresh_finds' = isPerishable(n) ? 'use_first' : 'fresh_finds'
    setIngredients(p => [...p, { id: nextId.current++, name: n, qty: '1', emoji: emoji ?? getEmoji(n), shelf }])
    if (!name) setNewName('')
  }

  function toggleShelf(id: number, e?: React.MouseEvent) {
    if (e) e.stopPropagation()
    setIngredients(p => p.map(i => {
      if (i.id !== id) return i
      const currentShelf = i.shelf ?? (isPerishable(i.name) ? 'use_first' : 'fresh_finds')
      const nextShelf: 'use_first' | 'fresh_finds' = currentShelf === 'use_first' ? 'fresh_finds' : 'use_first'
      return { ...i, shelf: nextShelf }
    }))
  }

  function moveToShelf(id: number, targetShelf: 'use_first' | 'fresh_finds') {
    setIngredients(p => p.map(i => i.id === id ? { ...i, shelf: targetShelf } : i))
  }

  function remove(id: number) {
    setDepartingId(id)
    window.setTimeout(() => {
      setIngredients(p => p.filter(i => i.id !== id))
      setDepartingId(null)
    }, 260)
  }
  function setQty(id: number, qty: string) { setIngredients(p => p.map(i => i.id === id ? { ...i, qty } : i)) }

  return (
    <div className="experience-shell screen-enter min-h-screen bg-butter flex flex-col paper-texture">
      <PageHeader onBack={() => onNavigate('input')} label="Step 2 of 4" />

      <div className="flex-1 px-6 md:px-12 lg:px-20 py-10">
        <div className="max-w-4xl mx-auto">
          <div className="screen-title text-center mb-8">
            <h1 className="font-heading text-4xl md:text-5xl font-semibold text-olive mb-3">
              Look at all this yummy potential! 😍
            </h1>
            <p className="font-body text-olive/60 text-lg">
              We found <strong className="text-tomato">{ingredients.length} ingredients</strong> — sorted into <strong className="text-tomato">use first</strong> and <strong className="text-olive">fresh finds</strong>!
            </p>
          </div>

          {/* Ingredient chips */}
          <div className="fridge-board bg-cream rounded-3xl p-6 md:p-8 border border-yellow/30 shadow-sm mb-5">
            <div className="fridge-interior mb-6">
              {ingredients.length === 0 && (
                <div className="w-full text-center py-5">
                  <div className="text-5xl mb-2">🍽️</div>
                  <p className="font-body text-olive/45 text-sm font-bold">My shelves are feeling a little empty.</p>
                  <p className="font-body text-olive/35 text-xs">Add a snack-sized idea below!</p>
                </div>
              )}
              {[0, 1].map(shelf => {
                const shelfType: 'use_first' | 'fresh_finds' = shelf === 0 ? 'use_first' : 'fresh_finds'
                const shelfItems = ingredients.filter(item => {
                  const itemShelf = item.shelf ?? (isPerishable(item.name) ? 'use_first' : 'fresh_finds')
                  return itemShelf === shelfType
                })

                return (
                  <div
                    className="fridge-shelf"
                    key={shelf}
                    onDragOver={e => e.preventDefault()}
                    onDrop={() => {
                      if (draggingId !== null) {
                        moveToShelf(draggingId, shelfType)
                        setDraggingId(null)
                      }
                    }}
                  >
                    <span className="shelf-label">
                      {shelf === 0 ? '⚡ use first (perishable)' : '🌱 fresh finds (pantry)'}
                    </span>
                    <div className="flex flex-wrap gap-3">
                      {shelfItems.length === 0 ? (
                        <p className="font-body text-olive/35 text-xs py-2 italic">
                          {shelf === 0 ? 'No urgent items! Drag or tap items to move here.' : 'No pantry staples here. Drag or tap items to move here.'}
                        </p>
                      ) : (
                        shelfItems.map((ing, i) => (
                          <div
                            key={ing.id}
                            draggable
                            onDragStart={() => setDraggingId(ing.id)}
                            onDragEnd={() => setDraggingId(null)}
                            className={`ingredient-magnet flex items-center gap-2 rounded-2xl px-3 py-2 border-2 border-white/50 shadow-sm group transition-all hover:shadow-md hover:scale-[1.04] ${departingId === ing.id ? 'to-compost' : ''} ${draggingId === ing.id ? 'is-dragging' : ''}`}
                            style={{ backgroundColor: CHIP_COLORS[(i + shelf) % CHIP_COLORS.length], '--tilt': `${[-1.5, 1, -0.5, 1.5][i % 4]}deg` } as React.CSSProperties}
                          >
                            <IngredientIcon name={ing.name} className="w-8 h-8 shrink-0" />
                            <div>
                              <div className="flex items-center gap-1.5">
                                <span className="block font-body font-extrabold text-olive text-xs">{ing.name}</span>
                                <button
                                  type="button"
                                  onClick={e => toggleShelf(ing.id, e)}
                                  title={shelf === 0 ? 'Move to Fresh Finds shelf' : 'Move to Use First shelf'}
                                  className="shelf-pill-btn bg-white/70 hover:bg-white text-olive/80"
                                >
                                  {shelf === 0 ? '⏳ urgent' : '🌱 staple'}
                                </button>
                              </div>
                              {editingId === ing.id ? (
                                <input autoFocus value={ing.qty} onChange={e => setQty(ing.id, e.target.value)} onBlur={() => setEditingId(null)} onKeyDown={e => e.key === 'Enter' && setEditingId(null)} className="w-16 bg-white/60 rounded-lg px-2 py-0.5 font-body text-olive text-xs outline-none border border-yellow text-center" />
                              ) : (
                                <button onClick={() => setEditingId(ing.id)} title="Click to edit quantity" className="font-body text-olive/55 text-[10px] bg-white/40 hover:bg-white/70 px-2 py-0.5 rounded-lg transition-colors">{ing.qty}</button>
                              )}
                            </div>
                            <button onClick={() => remove(ing.id)} aria-label={`Remove ${ing.name}`} className="text-olive/25 hover:text-tomato transition-colors opacity-0 group-hover:opacity-100 text-xl leading-none font-light">×</button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            <div
              className={`compost-drop ${draggingId ? 'is-ready' : ''}`}
              onDragOver={event => event.preventDefault()}
              onDrop={() => {
                if (draggingId) remove(draggingId)
                setDraggingId(null)
              }}
            >
              <span aria-hidden="true">♻</span>
              <strong>Drop to compost</strong>
            </div>

            {/* Add new */}
            <div className="flex gap-2 border-t border-yellow/25 pt-5 relative">
              <span className="absolute -top-4 right-1 font-body text-[10px] text-olive/35 font-bold">tiny compost bin ↘</span>
              <input
                type="text"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && add()}
                placeholder="Add more ingredients…"
                className="flex-1 bg-vanilla border border-yellow/50 rounded-xl px-4 py-3 font-body text-olive placeholder-olive/30 text-sm outline-none focus:border-tomato focus:ring-2 focus:ring-tomato/20 transition-all"
              />
              <button
                onClick={() => add()}
                className="bg-tomato text-white font-body font-bold px-5 py-3 rounded-xl text-sm hover:bg-[#D4614F] transition-colors"
              >
                + Add
              </button>
            </div>
          </div>

          {/* Quick-add suggestions */}
          <div className="mb-8">
            <p className="font-body text-olive/40 text-xs font-bold uppercase tracking-wider mb-3">Quick add:</p>
            <div className="flex flex-wrap gap-2">
              {QUICK_ADDS.filter(q => !ingredients.find(i => i.name.toLowerCase() === q.name.toLowerCase())).map(({ name, emoji }) => (
                <button
                  key={name}
                  onClick={() => add(name, emoji)}
                  className="font-body text-sm text-olive/70 bg-vanilla hover:bg-peach border border-yellow/40 hover:border-peach px-3 py-1.5 rounded-full transition-colors font-semibold"
                >
                  + {emoji} {name}
                </button>
              ))}
            </div>
          </div>

          <div className="text-center">
            <button
              onClick={() => onNavigate('vibe')}
              disabled={ingredients.length === 0}
              className="bg-olive text-butter font-body font-bold px-10 py-4 rounded-2xl text-lg hover:scale-[1.03] active:scale-[0.97] transition-transform shadow-lg disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Looks good! Let's pick a vibe →
            </button>
            {ingredients.length === 0 && <p className="font-body text-olive/60 text-xs mt-3" role="status">Add at least one ingredient to continue.</p>}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Screen 4: Vibe ──────────────────────────────────────────────────────────

function VibeScreen({ onNavigate, onFind, initialPreferences, ingredients }: { onNavigate: (s: Screen) => void; onFind: (theme: VibeTheme, preferences: Preferences, recipes?: Recipe[]) => void; initialPreferences: Preferences; ingredients: Ingredient[] }) {
  const [tastes, setTastes] = useState(new Set(initialPreferences.tastes))
  const [effort, setEffort] = useState<string | null>(initialPreferences.effort)
  const [time, setTime] = useState<string | null>(initialPreferences.time)
  const [diets, setDiets] = useState(new Set(initialPreferences.diets))
  const [generating, setGenerating] = useState(false)

  function toggle<T>(set: Set<T>, val: T): Set<T> {
    const n = new Set(set)
    n.has(val) ? n.delete(val) : n.add(val)
    return n
  }

  async function findMeal(surprise = false) {
    setGenerating(true)
    const selectedTheme: VibeTheme = surprise
      ? (['cozy', 'spicy', 'fresh', 'chef'] as VibeTheme[])[Math.floor(Math.random() * 4)]
      : tastes.has('spicy') ? 'spicy' : tastes.has('fresh') ? 'fresh' : effort === 'chef' ? 'chef' : 'cozy'
    const nextPreferences = { tastes: [...tastes], effort, time, diets: [...diets] }
    try {
      const res = await getRecipeRecommendations(ingredients, nextPreferences, selectedTheme, surprise)
      const finalTheme = (['cozy', 'spicy', 'fresh', 'chef'].includes(res.theme) ? res.theme : selectedTheme) as VibeTheme
      window.setTimeout(() => onFind(finalTheme, nextPreferences, res.recipes.length ? res.recipes : undefined), 1200)
    } catch {
      window.setTimeout(() => onFind(selectedTheme, nextPreferences), 1200)
    }
  }


  return (
    <div className="experience-shell screen-enter min-h-screen bg-butter flex flex-col paper-texture">
      <PageHeader onBack={() => onNavigate('ingredients')} label="Step 3 of 4" />

      <div className="flex-1 px-6 md:px-12 lg:px-20 py-10">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="screen-title text-center">
            <h1 className="font-heading text-4xl md:text-5xl font-semibold text-olive mb-3">
              Okay, chef. What's the vibe? 🎨
            </h1>
            <p className="font-body text-olive/60 text-lg">Tell us your preferences and we'll find the perfect match!</p>
          </div>

          {/* Taste */}
          <section className="bg-cream rounded-3xl p-6 md:p-8 border border-yellow/30 shadow-sm">
            <h2 className="font-heading text-2xl font-semibold text-olive mb-5 flex items-center gap-2">
              👅 Taste preferences
              <span className="font-body text-sm text-olive/40 font-normal">(pick all that apply)</span>
            </h2>
            <div className="flex flex-wrap gap-3">
              {TASTE_OPTIONS.map(({ id, label, emoji, bg }) => {
                const active = tastes.has(id)
                return (
                  <button
                    key={id}
                    onClick={() => setTastes(toggle(tastes, id))}
                    aria-pressed={active}
                    className={`vibe-sticker flex items-center gap-2 px-5 py-3 rounded-2xl font-body font-bold text-sm transition-all border-2 hover:scale-[1.04] ${active ? 'is-selected border-olive text-olive scale-[1.04] shadow-md' : 'border-transparent text-olive/70 hover:border-yellow/50'}`}
                    style={{ backgroundColor: bg }}
                  >
                    <span>{emoji}</span> {label}
                    {active && <span className="text-tomato text-xs">✓</span>}
                  </button>
                )
              })}
            </div>
          </section>

          {/* Cooking effort */}
          <section className="bg-cream rounded-3xl p-6 md:p-8 border border-yellow/30 shadow-sm">
            <h2 className="font-heading text-2xl font-semibold text-olive mb-5 flex items-center gap-2">
              ⚡ Cooking effort
            </h2>
            <div className="grid sm:grid-cols-3 gap-4">
              {EFFORT_OPTIONS.map(({ id, label, emoji, desc }) => (
                <button
                  key={id}
                  onClick={() => setEffort(id)}
                  aria-pressed={effort === id}
                  className={`effort-card p-5 rounded-2xl text-left border-2 transition-all hover:scale-[1.02] ${effort === id ? 'is-selected border-olive bg-yellow/45 shadow-md' : 'border-yellow/30 bg-vanilla hover:border-yellow hover:bg-yellow/20'}`}
                >
                  <div className="text-4xl mb-2 effort-mascot">{emoji}</div>
                  <div className="font-body font-bold text-olive text-sm mb-1">{label}</div>
                  <div className="font-body text-olive/50 text-xs leading-snug">{desc}</div>
                  {effort === id && <div className="mt-2 font-body text-tomato text-xs font-bold">Selected ✓</div>}
                </button>
              ))}
            </div>
          </section>

          {/* Time */}
          <section className="bg-cream rounded-3xl p-6 md:p-8 border border-yellow/30 shadow-sm">
            <h2 className="font-heading text-2xl font-semibold text-olive mb-5 flex items-center gap-2">
              ⏱️ How much time do you have?
            </h2>
            <div className="flex flex-wrap gap-3">
              {TIME_OPTIONS.map(t => (
                <button
                  key={t}
                  onClick={() => setTime(t)}
                  aria-pressed={time === t}
                  className={`px-6 py-3 rounded-full font-body font-bold text-sm transition-all border-2 ${time === t ? 'bg-olive text-butter border-olive shadow-md' : 'bg-vanilla text-olive border-yellow/40 hover:border-yellow hover:bg-yellow/20'}`}
                >
                  {t}
                </button>
              ))}
            </div>
          </section>

          {/* Dietary */}
          <section className="bg-cream rounded-3xl p-6 md:p-8 border border-yellow/30 shadow-sm">
            <h2 className="font-heading text-2xl font-semibold text-olive mb-5 flex items-center gap-2">
              🥗 Dietary preferences
              <span className="font-body text-sm text-olive/40 font-normal">(optional)</span>
            </h2>
            <div className="flex flex-wrap gap-3">
              {DIET_OPTIONS.map(({ id, label, emoji }) => (
                <button
                  key={id}
                  onClick={() => setDiets(toggle(diets, id))}
                  aria-pressed={diets.has(id)}
                  className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-body font-bold text-sm transition-all border-2 ${diets.has(id) ? 'bg-sage text-olive border-sage/80 shadow-sm' : 'bg-vanilla text-olive/70 border-yellow/40 hover:border-sage hover:bg-sage/20'}`}
                >
                  <span>{emoji}</span> {label}
                </button>
              ))}
            </div>
          </section>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center pb-8">
            <button
              onClick={() => findMeal(false)}
              disabled={generating}
              className="bg-olive text-butter font-body font-bold px-10 py-4 rounded-2xl text-lg hover:scale-[1.03] active:scale-[0.97] transition-transform shadow-lg"
            >
              Find my meal 🍽️
            </button>
            <button
              onClick={() => findMeal(true)}
              disabled={generating}
              className="bg-yellow text-olive font-body font-bold px-10 py-4 rounded-2xl text-lg hover:scale-[1.03] active:scale-[0.97] transition-transform border-2 border-olive/10 shadow-sm"
            >
              Surprise me! 🎲
            </button>
          </div>
        </div>
      </div>
      {generating && (
        <div className="loading-kitchen" role="status" aria-live="polite">
          <div className="loading-card">
            <div className="cooking-pot" aria-hidden="true">
              <span className="pot-lid">⌒</span>
              <span className="pot-body">◡</span>
              <span className="steam steam-one">♡</span>
              <span className="steam steam-two">〜</span>
            </div>
            <h2 className="font-heading text-3xl font-semibold text-olive">Tiny chefs at work!</h2>
            <div className="loading-phrases font-body font-bold text-tomato">
              <span>Peeking in the fridge…</span>
              <span>Consulting the tiny chefs…</span>
              <span>Adding one last sprinkle…</span>
            </div>
            <div className="loading-dots"><i /><i /><i /></div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Screen 5: Results ───────────────────────────────────────────────────────

function ResultsScreen({ onNavigate, onViewRecipe, onStartOver, theme, ingredients, recipes = RECIPES }: { onNavigate: (s: Screen) => void; onViewRecipe: (recipe: Recipe) => void; onStartOver: () => void; theme: VibeTheme; ingredients: Ingredient[]; recipes?: Recipe[] }) {
  // Deduplicate incoming recipes by clean name
  const uniqueRecipes = useMemo(() => {
    const seen = new Set<string>()
    return (recipes || []).filter(recipe => {
      const key = (recipe.name || '').trim().toLowerCase()
      if (!key || seen.has(key)) return false
      seen.add(key)
      return true
    })
  }, [recipes])

  const [saved, setSaved] = useState(() => {
    try { return new Set<number>(JSON.parse(localStorage.getItem('fridgemind-saved') ?? '[]')) }
    catch { return new Set<number>() }
  })
  const [filter, setFilter] = useState<string | null>(null)
  const [recipeOrder, setRecipeOrder] = useState(uniqueRecipes.map(recipe => recipe.id))

  useEffect(() => {
    setRecipeOrder(uniqueRecipes.map(recipe => recipe.id))
  }, [uniqueRecipes])

  function toggleSave(id: number) {
    setSaved(prev => {
      const n = new Set(prev)
      n.has(id) ? n.delete(id) : n.add(id)
      localStorage.setItem('fridgemind-saved', JSON.stringify([...n]))
      return n
    })
  }

  const allTags = [...new Set(uniqueRecipes.flatMap(r => r.tags))]
  const pantryNames = new Set(ingredients.map(item => item.name.toLowerCase()))
  const pantryMatch = (recipe: Recipe) => recipe.ingredients.filter(item => pantryNames.has(item.name.toLowerCase())).length
  const orderedRecipes = recipeOrder
    .map(id => uniqueRecipes.find(recipe => recipe.id === id)!)
    .filter(Boolean)
    .sort((a, b) => (b.match ?? pantryMatch(b)) - (a.match ?? pantryMatch(a)))
  const displayed = filter ? orderedRecipes.filter(r => r.tags.includes(filter)) : orderedRecipes

  function shuffleRecipes() {
    setRecipeOrder(previous => [...previous].sort(() => Math.random() - 0.5))
  }

  return (
    <div className={`experience-shell screen-enter min-h-screen bg-butter flex flex-col paper-texture results-theme theme-${theme}`}>
      <PageHeader onBack={() => onNavigate('vibe')} label="Step 4 of 4" />

      <div className="flex-1 px-6 md:px-12 lg:px-20 py-10">
        <div className="max-w-5xl mx-auto">

          {/* Header */}
          <div className="screen-title text-center mb-10">
            <div className="inline-flex items-center gap-2 bg-sage/50 border border-sage text-olive px-4 py-1.5 rounded-full font-body font-bold text-[0.7rem] tracking-[0.12em] uppercase mb-4">
              🎉 Your personalised recipes
            </div>
            <h1 className="font-heading text-4xl md:text-5xl font-semibold text-olive mb-3">
              We cooked up some magic! ✨
            </h1>
            <p className="font-body text-olive/60 text-lg">
              Based on your <strong>{ingredients.length} ingredients</strong> + your {theme} vibe — here's what we found!
            </p>
          </div>

          {/* Filter bar */}
          <div className="flex items-center gap-3 flex-wrap justify-between mb-7">
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => setFilter(null)}
                aria-pressed={!filter}
                className={`px-4 py-2 rounded-full font-body font-bold text-xs border transition-all ${!filter ? 'bg-olive text-butter border-olive' : 'bg-cream text-olive border-yellow/40 hover:border-yellow'}`}
              >
                All recipes
              </button>
              {allTags.map(tag => (
                <button
                  key={tag}
                  onClick={() => setFilter(filter === tag ? null : tag)}
                  aria-pressed={filter === tag}
                  className={`px-4 py-2 rounded-full font-body font-bold text-xs border transition-all ${filter === tag ? 'bg-tomato text-white border-tomato' : 'bg-cream text-olive border-yellow/40 hover:border-yellow'}`}
                >
                  {tag}
                </button>
              ))}
            </div>
            <button onClick={shuffleRecipes} className="flex items-center gap-2 bg-yellow text-olive font-body font-bold px-5 py-2.5 rounded-full text-xs hover:scale-105 transition-transform border border-yellow/60 shadow-sm">
              🎲 Shuffle recipes
            </button>
          </div>

          {/* Recipe grid */}
          <div className="grid md:grid-cols-2 gap-6 mb-10">
            {displayed.map((recipe, i) => (
              <article
                key={recipe.id}
                className="recipe-note bg-cream rounded-3xl overflow-hidden border border-yellow/30 shadow-sm hover:shadow-xl transition-all hover:-translate-y-1 group"
              >
                {/* Image area */}
                <div className="relative h-52 overflow-hidden" style={{ backgroundColor: recipe.accent }}>
                  <img
                    src={recipe.image}
                    alt={recipe.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    loading={i < 2 ? 'eager' : 'lazy'}
                  />
                  {/* Match badge */}
                  <div className="absolute top-3 left-3 bg-olive/90 text-butter font-body font-bold text-xs px-3 py-1.5 rounded-full shadow-md backdrop-blur-sm">
                    {recipe.match ?? Math.min(99, 70 + pantryMatch(recipe) * 5)}% match 🎯
                  </div>
                  {/* Save button */}
                  <button
                    onClick={() => toggleSave(recipe.id)}
                    aria-label={saved.has(recipe.id) ? 'Unsave recipe' : 'Save recipe'}
                    aria-pressed={saved.has(recipe.id)}
                    className={`save-heart absolute top-3 right-3 w-9 h-9 rounded-full flex items-center justify-center text-lg transition-all shadow-md ${saved.has(recipe.id) ? 'is-saved bg-tomato text-white' : 'bg-white/85 text-olive hover:bg-white'}`}
                  >
                    {saved.has(recipe.id) ? '♥' : '♡'}
                  </button>
                  {/* Time + difficulty */}
                  <div className="absolute bottom-3 left-3 flex gap-2">
                    <span className="bg-white/90 text-olive font-body font-bold text-xs px-2.5 py-1 rounded-full backdrop-blur-sm">
                      ⏱ {recipe.time}
                    </span>
                    <span className="bg-white/90 text-olive font-body font-bold text-xs px-2.5 py-1 rounded-full backdrop-blur-sm">
                      {recipe.difficulty === 'Easy' ? '🥄' : '🍳'} {recipe.difficulty}
                    </span>
                  </div>
                </div>

                {/* Content */}
                <div className="p-5">
                  {/* Dynamic Badges from ML */}
                  {recipe.badges && recipe.badges.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-2.5">
                      {recipe.badges.map(b => (
                        <span key={b} className="bg-yellow/60 text-olive border border-yellow/70 font-body font-extrabold text-[10px] px-2.5 py-0.5 rounded-full uppercase tracking-wider shadow-2xs">
                          ⭐ {b}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {recipe.tags.map(tag => (
                      <span key={tag} className="pantry-label bg-sage/35 text-olive font-body font-bold text-xs px-2.5 py-1 rounded-full border border-sage/30">
                        {tag}
                      </span>
                    ))}
                    <span className="bg-vanilla text-olive/45 font-body text-xs px-2.5 py-1 rounded-full">
                      {recipe.cal}
                    </span>
                  </div>
                  <h3 className="font-heading text-[1.3rem] font-semibold text-olive mb-2 leading-tight">{recipe.name}</h3>
                  <p className="font-body text-olive/55 text-sm leading-relaxed mb-3">{recipe.desc}</p>

                  {/* Missing vs Matched Ingredients */}
                  {recipe.missing_ingredients && recipe.missing_ingredients.length > 0 ? (
                    <div className="mb-3 px-3 py-1.5 rounded-xl bg-peach/25 border border-peach/50 text-xs font-body flex items-center justify-between gap-1.5 text-olive/75">
                      <div className="flex items-center gap-1.5 truncate">
                        <span className="text-tomato font-extrabold">Missing:</span>
                        <span className="font-semibold truncate">{recipe.missing_ingredients.join(', ')}</span>
                      </div>
                      {recipe.substitution && (
                        <span className="shrink-0 text-[10px] font-extrabold text-olive/80 bg-yellow/50 px-2 py-0.5 rounded-md border border-yellow/60">
                          💡 Swap available
                        </span>
                      )}
                    </div>
                  ) : (
                    <div className="mb-3 px-3 py-1.5 rounded-xl bg-sage/30 border border-sage/50 text-xs font-body font-bold text-olive flex items-center gap-1.5">
                      <span>✨ 100% pantry match! Zero waste hero.</span>
                    </div>
                  )}

                  <div className="ai-reason mb-4">
                    <span>✦</span>
                    <p>{recipe.ai_reason || `You have ${pantryMatch(recipe)} of ${recipe.ingredients.length} ingredients already, so this is a low-waste ${theme} match.`}</p>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-0.5">
                      {[1, 2, 3, 4, 5].map(star => (
                        <span key={star} className={`text-base ${star <= Math.round(recipe.rating) ? 'text-yellow' : 'text-olive/15'}`}>★</span>
                      ))}
                      <span className="font-body text-olive/40 text-xs ml-1.5">{recipe.rating}</span>
                    </div>
                    <button onClick={() => onViewRecipe(recipe)} className="bg-tomato text-white font-body font-bold text-sm px-5 py-2.5 rounded-xl hover:bg-[#D4614F] hover:scale-105 transition-all shadow-sm">
                      View Recipe →
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>

          {/* Bottom CTA */}
          <div className="bg-cream rounded-3xl p-8 border border-yellow/30 shadow-sm text-center mb-8">
            <div className="text-4xl mb-3">🍳</div>
            <h3 className="font-heading text-2xl font-semibold text-olive mb-2">Not quite hitting the spot?</h3>
            <p className="font-body text-olive/55 text-sm mb-6">Tweak your preferences or start fresh — we've got endless ideas for you!</p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={() => onNavigate('vibe')}
                className="bg-vanilla text-olive font-body font-bold px-8 py-3.5 rounded-2xl border-2 border-yellow/40 hover:border-yellow transition-all hover:scale-[1.02] shadow-sm"
              >
                ← Tweak preferences
              </button>
              <button
                onClick={() => onNavigate('ingredients')}
                className="bg-vanilla text-olive font-body font-bold px-8 py-3.5 rounded-2xl border-2 border-yellow/40 hover:border-yellow transition-all hover:scale-[1.02] shadow-sm"
              >
                Change ingredients
              </button>
              <button
                onClick={onStartOver}
                className="bg-olive text-butter font-body font-bold px-8 py-3.5 rounded-2xl hover:bg-[#4A5740] transition-all hover:scale-[1.02] shadow-sm"
              >
                Start over 🔄
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function RecipeDetailScreen({
  recipe,
  onNavigate,
  pantry,
  onUpdateRecipe,
}: {
  recipe: Recipe
  onNavigate: (screen: Screen) => void
  pantry: Ingredient[]
  onUpdateRecipe?: (recipe: Recipe) => void
}) {
  const [currentRecipe, setCurrentRecipe] = useState<Recipe>(recipe)
  const [swapModalOpen, setSwapModalOpen] = useState(false)
  const [swapTarget, setSwapTarget] = useState<string>('')
  const [swapOptions, setSwapOptions] = useState<SubstitutionOption[]>([])
  const [loadingSwaps, setLoadingSwaps] = useState(false)
  const [swapToast, setSwapToast] = useState<string | null>(null)
  const [isApplyingSwap, setIsApplyingSwap] = useState(false)

  // Sync internal recipe when prop changes
  useEffect(() => {
    setCurrentRecipe(recipe)
  }, [recipe])

  const storageKey = `fridgemind-cooking-${currentRecipe.id}`
  const savedCooking = (() => {
    try { return JSON.parse(localStorage.getItem(storageKey) ?? '{}') as { servings?: number; checked?: number[]; activeStep?: number; seconds?: number } }
    catch { return {} }
  })()
  const [servings, setServings] = useState(savedCooking.servings ?? currentRecipe.servings)
  const [checked, setChecked] = useState(new Set(savedCooking.checked ?? []))
  const [activeStep, setActiveStep] = useState(savedCooking.activeStep ?? 0)
  const [seconds, setSeconds] = useState(savedCooking.seconds ?? currentRecipe.stepTimers[0])
  const [timerRunning, setTimerRunning] = useState(false)
  const [timerFinished, setTimerFinished] = useState(false)
  const [focusMode, setFocusMode] = useState(false)
  const [completed, setCompleted] = useState(false)
  const [nutrition, setNutrition] = useState<NutritionSummary | null>(null)
  const [loadingNutrition, setLoadingNutrition] = useState(false)

  useEffect(() => {
    let isMounted = true
    setLoadingNutrition(true)
    getRecipeNutrition(currentRecipe.id, servings)
      .then(data => {
        if (!isMounted) return
        if (data) {
          setNutrition(data)
        } else {
          // Responsive client-side fallback calculation based on recipe baseline
          const baseCal = parseInt(currentRecipe.cal) || 300
          const scaledCal = Math.round((baseCal * servings) / (currentRecipe.servings || 2))
          const protein = Math.round(18 * (servings / (currentRecipe.servings || 2)))
          const carbs = Math.round(25 * (servings / (currentRecipe.servings || 2)))
          const fat = Math.round(14 * (servings / (currentRecipe.servings || 2)))
          const totalMacroCal = (protein * 4) + (carbs * 4) + (fat * 9)
          setNutrition({
            calories: scaledCal,
            protein_g: protein,
            carbs_g: carbs,
            fat_g: fat,
            servings,
            basis: 'USDA FoodData Central estimate',
            assumptions: 'Standard portion weights',
            macro_ratios: {
              protein_pct: Math.round(((protein * 4) / totalMacroCal) * 100),
              carbs_pct: Math.round(((carbs * 4) / totalMacroCal) * 100),
              fat_pct: Math.round(((fat * 9) / totalMacroCal) * 100),
            }
          })
        }
      })
      .catch(() => {
        // Silently preserve state
      })
      .finally(() => {
        if (isMounted) setLoadingNutrition(false)
      })
    return () => { isMounted = false }
  }, [currentRecipe.id, currentRecipe.ingredients, servings, currentRecipe.cal, currentRecipe.servings])

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify({ servings, checked: [...checked], activeStep, seconds }))
  }, [activeStep, checked, seconds, servings, storageKey])

  useEffect(() => {
    if (!timerRunning) return
    const timer = window.setInterval(() => {
      setSeconds(value => {
        if (value <= 1) {
          setTimerRunning(false)
          setTimerFinished(true)
          playKitchenChime('timer')
          if ('vibrate' in navigator) navigator.vibrate([180, 80, 180])
          return 0
        }
        return value - 1
      })
    }, 1000)
    return () => window.clearInterval(timer)
  }, [timerRunning])

  useEffect(() => {
    if (!timerRunning) return
    const warnBeforeLeaving = (event: BeforeUnloadEvent) => event.preventDefault()
    window.addEventListener('beforeunload', warnBeforeLeaving)
    return () => window.removeEventListener('beforeunload', warnBeforeLeaving)
  }, [timerRunning])

  useEffect(() => {
    const wakeLockNavigator = navigator as Navigator & { wakeLock?: { request: (type: 'screen') => Promise<{ release: () => Promise<void> }> } }
    let lock: { release: () => Promise<void> } | undefined
    if (focusMode && wakeLockNavigator.wakeLock) wakeLockNavigator.wakeLock.request('screen').then(value => { lock = value }).catch(() => undefined)
    return () => { lock?.release().catch(() => undefined) }
  }, [focusMode])

  function selectStep(index: number) {
    setActiveStep(index)
    setSeconds(currentRecipe.stepTimers[index] || 0)
    setTimerRunning(false)
    setTimerFinished(false)
  }

  function formatAmount(ingredient: RecipeIngredient) {
    const scaled = ingredient.amount * (servings / currentRecipe.servings)
    const amount = Number.isInteger(scaled) ? String(scaled) : String(Math.round(scaled * 10) / 10)
    return `${amount}${ingredient.unit ? ` ${ingredient.unit}` : ''}`
  }

  async function openSwapModal(targetName?: string) {
    const ingredientName = targetName || currentRecipe.ingredients[0]?.name || ''
    setSwapTarget(ingredientName)
    setSwapModalOpen(true)
    setLoadingSwaps(true)
    try {
      const options = await lookupSubstitutions(ingredientName)
      setSwapOptions(options)
    } catch {
      setSwapOptions([])
    } finally {
      setLoadingSwaps(false)
    }
  }

  async function handleSelectSwapTarget(name: string) {
    setSwapTarget(name)
    setLoadingSwaps(true)
    try {
      const options = await lookupSubstitutions(name)
      setSwapOptions(options)
    } catch {
      setSwapOptions([])
    } finally {
      setLoadingSwaps(false)
    }
  }

  async function handleApplySwap(original: string, substituteWith: string) {
    setIsApplyingSwap(true)
    try {
      const res = await substituteRecipeIngredient(currentRecipe, original, substituteWith)
      setCurrentRecipe(res.recipe)
      if (onUpdateRecipe) onUpdateRecipe(res.recipe)
      playKitchenChime('complete')
      setSwapToast(res.message)
      setSwapModalOpen(false)
      window.setTimeout(() => setSwapToast(null), 5000)
    } catch (err) {
      console.warn('Failed to apply swap:', err)
    } finally {
      setIsApplyingSwap(false)
    }
  }

  const pantryNames = new Set(pantry.map(item => item.name.toLowerCase()))
  const availableCount = currentRecipe.ingredients.filter(item => pantryNames.has(item.name.toLowerCase())).length
  const minutes = String(Math.floor(seconds / 60)).padStart(2, '0')
  const remainingSeconds = String(seconds % 60).padStart(2, '0')

  return (
    <div className="experience-shell screen-enter min-h-screen bg-butter flex flex-col paper-texture cooking-world">
      <PageHeader onBack={() => {
        if (!timerRunning || window.confirm('Your timer is still running. Leave cooking mode?')) onNavigate('results')
      }} label="Cooking mode" />
      <main className="flex-1 px-5 md:px-12 lg:px-20 py-8">
        <div className="max-w-6xl mx-auto">
          {swapToast && (
            <div className="mb-6 p-4 rounded-2xl bg-sage/40 border border-sage/80 flex items-center justify-between font-body text-sm text-olive shadow-sm animate-fade-in" role="status">
              <span className="flex items-center gap-2">
                <span className="text-xl">🎉</span>
                <strong>{swapToast}</strong>
              </span>
              <button onClick={() => setSwapToast(null)} className="text-olive/60 hover:text-olive text-sm font-bold ml-2">✕</button>
            </div>
          )}

          <section className="recipe-hero-card">
            <img src={currentRecipe.image} alt={currentRecipe.name} />
            <div className="recipe-hero-copy">
              <span className="font-body font-extrabold text-xs uppercase tracking-[.14em] text-tomato">FridgeMind kitchen notebook</span>
              <h1 className="font-heading text-4xl md:text-6xl font-semibold text-olive leading-tight">{currentRecipe.name}</h1>
              <p className="font-body text-olive/60 text-lg">{currentRecipe.desc}</p>
              {currentRecipe.badges && currentRecipe.badges.length > 0 && (
                <div className="flex flex-wrap gap-1.5 my-1">
                  {currentRecipe.badges.map(b => (
                    <span
                      key={b}
                      className={`font-body font-extrabold text-[10px] px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                        b.startsWith('Swapped')
                          ? 'bg-tomato text-white shadow-2xs'
                          : 'bg-sage/45 text-olive border border-sage/60'
                      }`}
                    >
                      {b.startsWith('Swapped') ? `🔄 ${b}` : b}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex flex-wrap gap-3">
                <span>⏱ {currentRecipe.time}</span>
                <span>🍳 {currentRecipe.difficulty}</span>
                <span>🔥 {nutrition ? `${nutrition.calories} cal` : currentRecipe.cal}</span>
                <span className="text-tomato font-extrabold">Serving {servings}</span>
              </div>
              <p className="font-body font-extrabold text-sm text-olive/70">You already have {availableCount} of {currentRecipe.ingredients.length} ingredients.</p>
            </div>
          </section>

          <div className={`recipe-workspace ${focusMode ? 'is-focus-mode' : ''}`}>
            <aside className="ingredient-checklist">
              <div className="flex items-center justify-between mb-5">
                <h2 className="font-heading text-2xl font-semibold">Ingredients</h2>
                <div className="serving-control" aria-label={`${servings} servings`}>
                  <button aria-label="Decrease servings" onClick={() => setServings(value => Math.max(1, value - 1))}>−</button>
                  <strong>{servings}</strong>
                  <button aria-label="Increase servings" onClick={() => setServings(value => Math.min(12, value + 1))}>+</button>
                </div>
              </div>
              {currentRecipe.ingredients.map((item, index) => {
                const inPantry = pantryNames.has(item.name.toLowerCase())
                return (
                <button key={item.name} aria-pressed={checked.has(index)} onClick={() => setChecked(current => {
                  const next = new Set(current)
                  next.has(index) ? next.delete(index) : next.add(index)
                  return next
                })} className={`check-ingredient ${checked.has(index) ? 'is-checked' : ''}`}>
                  <span className="custom-check">{checked.has(index) ? '✓' : ''}</span>
                  <IngredientIcon name={item.name} className="w-8 h-8" />
                  <span>{item.name}<em className={inPantry ? 'pantry-have' : 'pantry-need'}>{inPantry ? 'have' : 'need'}</em></span>
                  <div className="flex items-center gap-2 ml-auto">
                    <small>{formatAmount(item)}</small>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        openSwapModal(item.name)
                      }}
                      title={`Explore culinary swaps for ${item.name}`}
                      className="px-2 py-0.5 rounded-lg text-[10px] font-body font-bold text-olive/80 hover:text-white bg-peach/40 hover:bg-tomato border border-peach/70 transition-all flex items-center gap-1 shadow-2xs"
                    >
                      <span>🔄</span>
                      <span className="hidden sm:inline">Swap</span>
                    </button>
                  </div>
                </button>
              )})}
              <div className="substitution-note group">
                <div className="flex items-center justify-between mb-1.5">
                  <strong className="text-olive flex items-center gap-1">
                    <span>💡</span> Culinary Substitutions
                  </strong>
                  <button
                    type="button"
                    onClick={() => openSwapModal(currentRecipe.ingredients[0]?.name)}
                    className="text-xs font-body font-extrabold text-tomato hover:text-[#b53a29] underline decoration-dotted flex items-center gap-1 hover:scale-105 transition-transform"
                  >
                    <span>✨ 1-Click Swap Mode</span>
                  </button>
                </div>
                <p className="text-olive/75 text-sm">{currentRecipe.substitution}</p>
              </div>

              {/* Dynamic USDA Nutrition Card */}
              <div className="nutrition-card">
                <div className="flex items-center justify-between mb-2">
                  <strong className="font-heading text-sm text-olive flex items-center gap-1.5">
                    <span>🥗</span> Nutrition Analysis
                  </strong>
                  <span className="font-body text-[10px] text-olive/50 font-extrabold uppercase tracking-wider">
                    {loadingNutrition ? 'Calculating…' : 'USDA Standard'}
                  </span>
                </div>
                <div className="flex items-baseline justify-between mb-1">
                  <span className="font-body text-xs text-olive/60">Scaled Total:</span>
                  <strong className="font-heading text-xl text-tomato">{nutrition?.calories ?? recipe.cal} cal</strong>
                </div>
                {nutrition?.macro_ratios && (
                  <div>
                    <div className="macro-bar-container" title={`Protein: ${nutrition.macro_ratios.protein_pct}%, Carbs: ${nutrition.macro_ratios.carbs_pct}%, Fat: ${nutrition.macro_ratios.fat_pct}%`}>
                      <div className="macro-bar-protein" style={{ width: `${nutrition.macro_ratios.protein_pct}%` }} />
                      <div className="macro-bar-carbs" style={{ width: `${nutrition.macro_ratios.carbs_pct}%` }} />
                      <div className="macro-bar-fat" style={{ width: `${nutrition.macro_ratios.fat_pct}%` }} />
                    </div>
                    <div className="grid grid-cols-3 gap-1.5 text-center font-body text-[11px] mt-2">
                      <div className="bg-[#C9DCC5]/45 rounded-xl py-1.5 px-1 border border-[#C9DCC5]/80">
                        <span className="block font-black text-olive">{nutrition.protein_g}g</span>
                        <span className="text-olive/60 font-bold text-[9px] uppercase">Protein</span>
                      </div>
                      <div className="bg-[#F5D66F]/45 rounded-xl py-1.5 px-1 border border-[#F5D66F]/80">
                        <span className="block font-black text-olive">{nutrition.carbs_g}g</span>
                        <span className="text-olive/60 font-bold text-[9px] uppercase">Carbs</span>
                      </div>
                      <div className="bg-[#FFD5C2]/45 rounded-xl py-1.5 px-1 border border-[#FFD5C2]/80">
                        <span className="block font-black text-olive">{nutrition.fat_g}g</span>
                        <span className="text-olive/60 font-bold text-[9px] uppercase">Fat</span>
                      </div>
                    </div>
                  </div>
                )}
                <p className="font-body text-[10px] text-olive/45 mt-2 italic text-center">
                  {nutrition?.assumptions || 'USDA FoodData Central standard portion weights'}
                </p>
              </div>
            </aside>

            <section className="cooking-steps">
              <div className="cooking-toolbar">
                <div>
                  <span>Step {activeStep + 1} of {currentRecipe.steps.length}</span>
                  <div className="step-progress"><i style={{ width: `${((activeStep + 1) / currentRecipe.steps.length) * 100}%` }} /></div>
                </div>
                <button aria-pressed={focusMode} onClick={() => setFocusMode(value => !value)}>{focusMode ? 'Show full recipe' : 'Focus mode'}</button>
              </div>
              <div className="timer-card">
                <div><small>{currentRecipe.stepTimers[activeStep] ? `Step ${activeStep + 1} countdown` : 'No timer needed for this step'}</small><strong aria-live="off" aria-label={`${minutes} minutes and ${remainingSeconds} seconds remaining`}>{minutes}:{remainingSeconds}</strong></div>
                <button disabled={!seconds && !timerRunning} onClick={() => { setTimerFinished(false); setTimerRunning(value => !value) }}>{timerRunning ? 'Pause' : 'Start timer'}</button>
                <button onClick={() => { setSeconds(currentRecipe.stepTimers[activeStep] || 0); setTimerRunning(false); setTimerFinished(false) }}>Reset</button>
              </div>
              {timerFinished && <div className="timer-alert" role="alert">Time’s up! Your next delicious move is ready.</div>}
              <h2 className="font-heading text-3xl font-semibold mt-7 mb-4">Let’s cook</h2>
              {currentRecipe.steps.map((step, index) => (
                <button key={step} aria-pressed={activeStep === index} onClick={() => selectStep(index)} className={`cooking-step ${activeStep === index ? 'is-active' : ''}`}>
                  <span>{index + 1}</span>
                  <p>{step}</p>
                  {activeStep === index && <i>Now cooking</i>}
                </button>
              ))}
              <div className="step-navigation">
                <button disabled={activeStep === 0} onClick={() => selectStep(activeStep - 1)}>← Previous</button>
                {activeStep < currentRecipe.steps.length - 1
                  ? <button onClick={() => selectStep(activeStep + 1)}>Next step →</button>
                  : <button onClick={() => {
                      setCompleted(true)
                      setTimerRunning(false)
                      playKitchenChime('complete')
                      localStorage.removeItem(storageKey)
                    }}>Finish cooking</button>}
              </div>
              {completed && (
                <div className="completion-card" role="status">
                  <span aria-hidden="true">✦</span>
                  <h2 className="font-heading text-3xl font-semibold">You made something wonderful!</h2>
                  <p>Take a breath, plate it proudly, and enjoy your {currentRecipe.name.toLowerCase()}.</p>
                  <button className="bg-olive text-butter font-body font-extrabold px-8 py-4 rounded-2xl mt-4" onClick={() => onNavigate('results')}>Back to my recipes</button>
                </div>
              )}
            </section>
          </div>
        </div>
      </main>

      {/* Interactive 1-Click Substitution Modal */}
      {swapModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-olive/50 backdrop-blur-sm animate-fade-in" role="dialog" aria-modal="true">
          <div className="bg-cream rounded-3xl p-6 md:p-8 max-w-xl w-full border-2 border-yellow/40 shadow-2xl space-y-5 max-h-[90vh] flex flex-col paper-texture">
            <div className="flex items-center justify-between border-b border-yellow/30 pb-3">
              <div>
                <h3 className="font-heading text-2xl font-semibold text-olive flex items-center gap-2">
                  <span>🔄</span> 1-Click Culinary Swaps
                </h3>
                <p className="font-body text-xs text-olive/60 mt-0.5">Adapt this recipe on-the-fly with authentic pantry substitutes</p>
              </div>
              <button
                onClick={() => setSwapModalOpen(false)}
                className="w-8 h-8 rounded-full bg-peach/40 hover:bg-peach text-olive flex items-center justify-center font-bold text-sm transition-colors"
                aria-label="Close substitutions dialog"
              >
                ✕
              </button>
            </div>

            <div>
              <label className="block font-body font-extrabold text-xs text-olive/70 uppercase tracking-wider mb-2">
                Select ingredient to replace:
              </label>
              <div className="flex flex-wrap gap-2">
                {currentRecipe.ingredients.map(ing => (
                  <button
                    key={ing.name}
                    type="button"
                    onClick={() => handleSelectSwapTarget(ing.name)}
                    className={`px-3 py-1.5 rounded-xl font-body text-xs font-bold transition-all border ${
                      swapTarget.toLowerCase() === ing.name.toLowerCase()
                        ? 'bg-olive text-butter border-olive shadow-xs scale-105'
                        : 'bg-white/80 text-olive border-yellow/40 hover:border-yellow'
                    }`}
                  >
                    {ing.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {loadingSwaps ? (
                <div className="text-center py-8">
                  <span className="text-3xl animate-spin inline-block mb-2">🍳</span>
                  <p className="font-body text-xs text-olive/60 font-bold">Scanning culinary substitution matrix…</p>
                </div>
              ) : swapOptions.length === 0 ? (
                <div className="text-center py-8 bg-white/50 rounded-2xl p-4 border border-yellow/30">
                  <span className="text-3xl block mb-2">🌿</span>
                  <p className="font-body text-sm font-bold text-olive">No direct swaps found for {swapTarget}</p>
                  <p className="font-body text-xs text-olive/50 mt-1">Try selecting another ingredient above, or use any tender greens or staple grains you have on hand.</p>
                </div>
              ) : (
                swapOptions.map((opt, idx) => {
                  const inPantry = pantry.some(p => p.name.toLowerCase().includes(opt.substitute.toLowerCase()) || opt.substitute.toLowerCase().includes(p.name.toLowerCase()))
                  return (
                    <div
                      key={idx}
                      className={`p-4 rounded-2xl border transition-all ${
                        inPantry ? 'bg-[#C9DCC5]/30 border-[#A3C29E]' : 'bg-white/70 border-yellow/30'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3 mb-1.5">
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <strong className="font-heading text-lg text-olive">{opt.substitute}</strong>
                            <span className="bg-yellow/40 text-olive text-[11px] font-body font-bold px-2 py-0.5 rounded-full border border-yellow/50">
                              Ratio: {opt.ratio}
                            </span>
                            {inPantry && (
                              <span className="bg-emerald-600 text-white text-[10px] font-body font-extrabold px-2 py-0.5 rounded-full shadow-2xs">
                                ⭐ In your pantry!
                              </span>
                            )}
                          </div>
                          <p className="font-body text-xs text-olive/70 italic mt-0.5">Flavor impact: {opt.flavor_impact}</p>
                        </div>
                        <button
                          disabled={isApplyingSwap}
                          onClick={() => handleApplySwap(swapTarget, opt.substitute)}
                          className="shrink-0 bg-tomato hover:bg-[#d04332] text-white font-body font-bold text-xs px-3.5 py-2 rounded-xl transition-all shadow-xs hover:scale-105 active:scale-95 disabled:opacity-50"
                        >
                          {isApplyingSwap ? 'Adapting…' : 'Apply Swap →'}
                        </button>
                      </div>
                      <p className="font-body text-xs text-olive/60 mt-1">{opt.notes}</p>
                      {opt.dietary_tags && opt.dietary_tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {opt.dietary_tags.map(tag => (
                            <span key={tag} className="text-[10px] font-body font-semibold px-2 py-0.5 rounded-md bg-olive/10 text-olive/70">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>

            <div className="pt-2 border-t border-yellow/30 text-right">
              <button
                onClick={() => setSwapModalOpen(false)}
                className="bg-vanilla hover:bg-cream text-olive font-body font-bold text-xs px-5 py-2.5 rounded-xl border border-yellow/50 transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Root ────────────────────────────────────────────────────────────────────

export default function App() {
  const validScreens: Screen[] = ['home', 'input', 'ingredients', 'vibe', 'results', 'recipe']
  const readSaved = <T,>(key: string, fallback: T): T => {
    try { return JSON.parse(localStorage.getItem(key) ?? '') as T }
    catch { return fallback }
  }
  const initialHash = window.location.hash.replace('#/', '') as Screen
  const [screen, setScreen] = useState<Screen>(validScreens.includes(initialHash) ? initialHash : 'home')
  const [ingredients, setIngredients] = useState<Ingredient[]>(() => readSaved('fridgemind-ingredients', INITIAL_INGREDIENTS))
  const [theme, setTheme] = useState<VibeTheme>(() => readSaved('fridgemind-theme', 'cozy'))
  const [preferences, setPreferences] = useState<Preferences>(() => readSaved('fridgemind-preferences', DEFAULT_PREFERENCES))
  const [recipesList, setRecipesList] = useState<Recipe[]>(RECIPES)
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe>(() => {
    const id = readSaved('fridgemind-recipe', RECIPES[0].id)
    return RECIPES.find(recipe => recipe.id === id) ?? RECIPES[0]
  })

  useEffect(() => {
    const handleHash = () => {
      const next = window.location.hash.replace('#/', '') as Screen
      setScreen(validScreens.includes(next) ? next : 'home')
    }
    window.addEventListener('hashchange', handleHash)
    return () => window.removeEventListener('hashchange', handleHash)
  }, [])

  useEffect(() => {
    localStorage.setItem('fridgemind-ingredients', JSON.stringify(ingredients))
    localStorage.setItem('fridgemind-theme', JSON.stringify(theme))
    localStorage.setItem('fridgemind-preferences', JSON.stringify(preferences))
    localStorage.setItem('fridgemind-recipe', JSON.stringify(selectedRecipe.id))
  }, [ingredients, preferences, selectedRecipe.id, theme])

  useEffect(() => {
    document.title = screen === 'home' ? 'FridgeMind — Your next meal' : `${screen === 'recipe' ? selectedRecipe.name : screen[0].toUpperCase() + screen.slice(1)} | FridgeMind`
    window.setTimeout(() => {
      const heading = document.querySelector('h1')
      if (heading instanceof HTMLElement) {
        heading.tabIndex = -1
        heading.focus({ preventScroll: true })
      }
    }, 50)
  }, [screen, selectedRecipe.name])

  function navigate(to: Screen) {
    window.scrollTo({ top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    if (window.location.hash === `#/${to}`) setScreen(to)
    else window.location.hash = `/${to}`
  }

  return (
    <div className="min-h-screen overflow-x-hidden">
      <AmbientKitchen />
      <SceneWipe screen={screen} />
      <PersistentFridge screen={screen} ingredientCount={ingredients.length} />
      {screen === 'home'        && <HomeScreen        onNavigate={navigate} />}
      {screen === 'input'       && <InputScreen       onNavigate={navigate} onContinue={items => { setIngredients(items); navigate('ingredients') }} />}
      {screen === 'ingredients' && <IngredientsScreen onNavigate={navigate} ingredients={ingredients} setIngredients={setIngredients} />}
      {screen === 'vibe'        && <VibeScreen onNavigate={navigate} ingredients={ingredients} initialPreferences={preferences} onFind={(nextTheme, nextPreferences, nextRecipes) => { setTheme(nextTheme); setPreferences(nextPreferences); if (nextRecipes?.length) setRecipesList(nextRecipes); navigate('results') }} />}
      {screen === 'results'     && <ResultsScreen onNavigate={navigate} recipes={recipesList} onStartOver={() => {
        if (window.confirm('Start fresh and clear your ingredients and preferences?')) {
          setIngredients(INITIAL_INGREDIENTS)
          setPreferences(DEFAULT_PREFERENCES)
          setTheme('cozy')
          setRecipesList(RECIPES)
          localStorage.removeItem('fridgemind-saved')
          navigate('home')
        }
      }} theme={theme} ingredients={ingredients} onViewRecipe={recipe => { setSelectedRecipe(recipe); navigate('recipe') }} />}
      {screen === 'recipe'      && <RecipeDetailScreen recipe={selectedRecipe} pantry={ingredients} onNavigate={navigate} onUpdateRecipe={setSelectedRecipe} />}
    </div>
  )
}

