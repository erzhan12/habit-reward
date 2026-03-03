/**
 * Theme definitions for the Habit Reward app.
 *
 * Each theme provides:
 *  - name          Display label shown in the picker
 *  - icon          Emoji for the picker card
 *  - description   Short description
 *  - cssVars       CSS custom-property overrides applied to <html>
 *  - classes       Structural class tokens used by components
 *    - card        { rounded, shadow, border, bg, hoverBg, extra }
 *    - button      { rounded, padding, primary, secondary }
 *    - input       { base }
 *    - badge       { base }
 *    - select      { base }
 *  - layout        'sidebar' | 'topbar'
 *  - navStyle      'default' | 'frosted' | 'underline' | 'glow'
 *  - font          { family, import, weight, size }
 *  - interactions  { habitComplete }
 *  - animations    { cardEntrance, completionCelebration, hoverMicro, streakFire }
 *  - reward        { displayMode, celebrationComponent }
 *  - pageLayout    { habitList, density, rewardList }
 */

// ── Validation constant sets ────────────────────────────────────────
export const VALID_INTERACTIONS = new Set([
  'button-right', 'checkbox', 'swipe-reveal',
]);

export const VALID_CARD_ENTRANCES = new Set([
  'none', 'fade-in', 'slide-up', 'stagger-fade',
]);

export const VALID_COMPLETION_CELEBRATIONS = new Set([
  'none', 'scale-up', 'burst-particles', 'fade-quiet',
]);

export const VALID_HOVER_MICROS = new Set([
  'none', 'scale', 'shadow-lift', 'glow-border',
]);

export const VALID_STREAK_FIRES = new Set([
  'none', 'pulse-glow', 'flicker-flame', 'bounce',
]);

export const VALID_DISPLAY_MODES = new Set([
  'expand-from-card', 'toast',
]);

export const VALID_HABIT_LAYOUTS = new Set([
  'list', 'grid-2',
]);

export const VALID_DENSITIES = new Set([
  'spacious', 'normal', 'compact',
]);

// ── Default values for all extended config keys ─────────────────────
export const DEFAULTS = {
  font: {
    family: 'system-ui, -apple-system, sans-serif',
    import: null,
    weight: '400',
    size: '16px',
  },
  interactions: {
    habitComplete: 'button-right',
  },
  animations: {
    cardEntrance: 'none',
    completionCelebration: 'none',
    hoverMicro: 'none',
    streakFire: 'none',
  },
  reward: {
    displayMode: 'expand-from-card',
    celebrationComponent: null,
  },
  pageLayout: {
    habitList: 'list',
    density: 'normal',
    rewardList: 'list',
  },
};

// ── Deep merge helper ───────────────────────────────────────────────
function deepMerge(defaults, overrides) {
  const result = { ...defaults };
  for (const key of Object.keys(overrides)) {
    if (
      overrides[key] &&
      typeof overrides[key] === 'object' &&
      !Array.isArray(overrides[key]) &&
      defaults[key] &&
      typeof defaults[key] === 'object' &&
      !Array.isArray(defaults[key])
    ) {
      result[key] = deepMerge(defaults[key], overrides[key]);
    } else {
      result[key] = overrides[key];
    }
  }
  return result;
}

// ── Resolve theme config with defaults ──────────────────────────────
export function resolveTheme(config) {
  return deepMerge(DEFAULTS, config);
}

// ── Theme definitions ───────────────────────────────────────────────
export const themes = {
  clean_modern: {
    name: 'Clean Modern',
    icon: '✨',
    description: 'Polished light theme with subtle shadows and rounded cards',
    cssVars: {
      '--color-bg-primary': '#f8fafc',
      '--color-bg-card': '#ffffff',
      '--color-bg-card-hover': '#f1f5f9',
      '--color-text-primary': '#0f172a',
      '--color-text-secondary': '#64748b',
      '--color-accent': '#6366f1',
      '--color-accent-hover': '#4f46e5',
      '--color-danger': '#ef4444',
      '--color-streak-fire': '#f97316',
    },
    classes: {
      card: {
        rounded: 'rounded-2xl',
        shadow: 'shadow-sm',
        border: 'border border-slate-200',
        bg: 'bg-bg-card',
        hoverBg: 'hover:bg-bg-card-hover',
        extra: '',
      },
      button: {
        rounded: 'rounded-full',
        padding: 'px-5 py-2',
        primary: 'bg-accent hover:bg-accent-hover text-white',
        secondary: 'bg-slate-100 hover:bg-slate-200 text-text-secondary',
      },
      input: {
        base: 'bg-white border border-slate-200 rounded-xl text-text-primary',
      },
      badge: {
        base: 'rounded-full bg-slate-100 text-text-secondary',
      },
      select: {
        base: 'bg-white border border-slate-200 rounded-xl text-text-primary',
      },
    },
    layout: 'sidebar',
    navStyle: 'default',
    font: {
      family: "'Inter', system-ui, -apple-system, sans-serif",
      import: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap',
      weight: '400',
      size: '16px',
    },
    interactions: {
      habitComplete: 'button-right',
    },
    animations: {
      cardEntrance: 'fade-in',
      completionCelebration: 'scale-up',
      hoverMicro: 'shadow-lift',
      streakFire: 'pulse-glow',
    },
    reward: {
      displayMode: 'expand-from-card',
      celebrationComponent: null,
    },
    pageLayout: {
      habitList: 'list',
      density: 'spacious',
      rewardList: 'list',
    },
  },

  gamified_arcade: {
    name: 'Gamified Arcade',
    icon: '🕹️',
    description: 'Bold neon glow on deep navy with pixel-perfect energy',
    cssVars: {
      '--color-bg-primary': '#0a0e27',
      '--color-bg-card': '#0d1240',
      '--color-bg-card-hover': '#111650',
      '--color-text-primary': '#e2e8f0',
      '--color-text-secondary': '#94a3b8',
      '--color-accent': '#06b6d4',
      '--color-accent-hover': '#22d3ee',
      '--color-danger': '#f43f5e',
      '--color-streak-fire': '#ec4899',
    },
    classes: {
      card: {
        rounded: 'rounded-lg',
        shadow: 'shadow-lg shadow-cyan-900/20',
        border: 'border border-cyan-900/40',
        bg: 'bg-bg-card',
        hoverBg: 'hover:bg-bg-card-hover hover:border-cyan-500/40 hover:shadow-cyan-500/20',
        extra: '',
      },
      button: {
        rounded: 'rounded-md',
        padding: 'px-4 py-2',
        primary: 'bg-transparent border border-accent text-accent hover:bg-accent hover:text-black',
        secondary: 'bg-transparent border border-gray-600 text-text-secondary hover:border-gray-400',
      },
      input: {
        base: 'bg-bg-card border border-cyan-900/40 rounded-lg text-text-primary focus:border-accent',
      },
      badge: {
        base: 'rounded border border-accent/30 text-accent',
      },
      select: {
        base: 'bg-bg-card border border-cyan-900/40 rounded-lg text-text-primary',
      },
    },
    layout: 'sidebar',
    navStyle: 'glow',
    font: {
      family: "'Press Start 2P', 'Courier New', monospace",
      import: 'https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap',
      weight: '400',
      size: '14px',
    },
    interactions: {
      habitComplete: 'button-right',
    },
    animations: {
      cardEntrance: 'stagger-fade',
      completionCelebration: 'burst-particles',
      hoverMicro: 'glow-border',
      streakFire: 'flicker-flame',
    },
    reward: {
      displayMode: 'toast',
      celebrationComponent: null,
    },
    pageLayout: {
      habitList: 'list',
      density: 'normal',
      rewardList: 'list',
    },
  },
  cozy_warm: {
    name: 'Cozy Warm',
    icon: '🌿',
    description: 'Earth tones with warm amber accents and soft shapes',
    cssVars: {
      '--color-bg-primary': '#1c1917',
      '--color-bg-card': '#292524',
      '--color-bg-card-hover': '#3a3532',
      '--color-text-primary': '#d6d3d1',
      '--color-text-secondary': '#a8a29e',
      '--color-accent': '#f59e0b',
      '--color-accent-hover': '#fbbf24',
      '--color-danger': '#ef4444',
      '--color-streak-fire': '#fb923c',
    },
    classes: {
      card: {
        rounded: 'rounded-xl',
        shadow: '',
        border: 'border-l-4 border-l-amber-500 border-t-0 border-r-0 border-b-0',
        bg: 'bg-bg-card',
        hoverBg: 'hover:bg-bg-card-hover',
        extra: 'pl-4',
      },
      button: {
        rounded: 'rounded-lg',
        padding: 'px-5 py-2.5',
        primary: 'bg-accent hover:bg-accent-hover text-black font-semibold',
        secondary: 'bg-stone-700 hover:bg-stone-600 text-text-secondary',
      },
      input: {
        base: 'bg-bg-card border border-stone-700 rounded-lg text-text-primary',
      },
      badge: {
        base: 'rounded bg-stone-700 text-text-secondary',
      },
      select: {
        base: 'bg-bg-card border border-stone-700 rounded-lg text-text-primary',
      },
    },
    layout: 'sidebar',
    navStyle: 'underline',
    font: {
      family: "'Quicksand', system-ui, sans-serif",
      import: 'https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600&display=swap',
      weight: '500',
      size: '16px',
    },
    interactions: {
      habitComplete: 'button-right',
    },
    animations: {
      cardEntrance: 'slide-up',
      completionCelebration: 'scale-up',
      hoverMicro: 'scale',
      streakFire: 'bounce',
    },
    reward: {
      displayMode: 'expand-from-card',
      celebrationComponent: null,
    },
    pageLayout: {
      habitList: 'list',
      density: 'spacious',
      rewardList: 'list',
    },
  },

  ios_native: {
    name: 'iOS Native',
    icon: '🍎',
    description: 'Full glassmorphism with frosted translucent layers',
    cssVars: {
      '--color-bg-primary': '#1c1c2e',
      '--color-bg-card': 'rgba(255,255,255,0.07)',
      '--color-bg-card-hover': 'rgba(255,255,255,0.12)',
      '--color-text-primary': '#f2f2f7',
      '--color-text-secondary': '#aeaeb2',
      '--color-accent': '#007aff',
      '--color-accent-hover': '#3395ff',
      '--color-danger': '#ff3b30',
      '--color-streak-fire': '#ff9500',
    },
    classes: {
      card: {
        rounded: 'rounded-2xl',
        shadow: 'shadow-lg shadow-black/20',
        border: 'border border-white/10',
        bg: 'bg-bg-card backdrop-blur-xl',
        hoverBg: 'hover:bg-bg-card-hover',
        extra: '',
      },
      button: {
        rounded: 'rounded-xl',
        padding: 'px-4 py-2',
        primary: 'bg-[#007aff]/90 hover:bg-[#007aff] text-white backdrop-blur-sm',
        secondary: 'bg-white/10 hover:bg-white/15 text-text-secondary backdrop-blur-sm border border-white/10',
      },
      input: {
        base: 'bg-white/8 border border-white/10 rounded-xl text-text-primary backdrop-blur-xl',
      },
      badge: {
        base: 'rounded-full bg-white/10 text-text-secondary backdrop-blur-sm',
      },
      select: {
        base: 'bg-white/8 border border-white/10 rounded-xl text-text-primary backdrop-blur-xl',
      },
    },
    layout: 'sidebar',
    navStyle: 'frosted',
    font: {
      family: "-apple-system, 'SF Pro Display', system-ui, sans-serif",
      import: null,
      weight: '400',
      size: '16px',
    },
    interactions: {
      habitComplete: 'button-right',
    },
    animations: {
      cardEntrance: 'fade-in',
      completionCelebration: 'scale-up',
      hoverMicro: 'scale',
      streakFire: 'pulse-glow',
    },
    reward: {
      displayMode: 'expand-from-card',
      celebrationComponent: null,
    },
    pageLayout: {
      habitList: 'list',
      density: 'normal',
      rewardList: 'list',
    },
  },

  dark_focus: {
    name: 'Dark Focus',
    icon: '🌑',
    description: 'Deep dark with emerald accents for distraction-free focus',
    cssVars: {
      '--color-bg-primary': '#030712',
      '--color-bg-card': '#111827',
      '--color-bg-card-hover': '#1f2937',
      '--color-text-primary': '#f3f4f6',
      '--color-text-secondary': '#9ca3af',
      '--color-accent': '#10b981',
      '--color-accent-hover': '#34d399',
      '--color-danger': '#ef4444',
      '--color-streak-fire': '#f97316',
    },
    classes: {
      card: {
        rounded: 'rounded-xl',
        shadow: '',
        border: '',
        bg: 'bg-bg-card',
        hoverBg: 'hover:bg-bg-card-hover',
        extra: '',
      },
      button: {
        rounded: 'rounded-lg',
        padding: 'px-4 py-2',
        primary: 'bg-accent hover:bg-accent-hover text-white',
        secondary: 'bg-gray-800 hover:bg-gray-700 text-text-secondary',
      },
      input: {
        base: 'bg-bg-card border border-gray-800 rounded-lg text-text-primary',
      },
      badge: {
        base: 'rounded bg-gray-800 text-text-secondary',
      },
      select: {
        base: 'bg-bg-card border border-gray-800 rounded-lg text-text-primary',
      },
    },
    layout: 'sidebar',
    navStyle: 'default',
    font: {
      family: 'system-ui, -apple-system, sans-serif',
      import: null,
      weight: '400',
      size: '15px',
    },
    interactions: {
      habitComplete: 'button-right',
    },
    animations: {
      cardEntrance: 'fade-in',
      completionCelebration: 'fade-quiet',
      hoverMicro: 'none',
      streakFire: 'pulse-glow',
    },
    reward: {
      displayMode: 'expand-from-card',
      celebrationComponent: null,
    },
    pageLayout: {
      habitList: 'list',
      density: 'compact',
      rewardList: 'list',
    },
  },

  retro_terminal: {
    name: 'Retro Terminal',
    icon: '💻',
    description: 'Green-on-black terminal with monospace font and hacker vibes',
    cssVars: {
      '--color-bg-primary': '#0a0a0a',
      '--color-bg-card': '#121212',
      '--color-bg-card-hover': '#1a1a1a',
      '--color-text-primary': '#00ff41',
      '--color-text-secondary': '#00cc33',
      '--color-accent': '#00ff41',
      '--color-accent-hover': '#33ff66',
      '--color-danger': '#ff1744',
      '--color-streak-fire': '#ffab00',
    },
    classes: {
      card: {
        rounded: 'rounded-none',
        shadow: '',
        border: 'border border-green-900/50',
        bg: 'bg-bg-card',
        hoverBg: 'hover:bg-bg-card-hover',
        extra: '',
      },
      button: {
        rounded: 'rounded-none',
        padding: 'px-4 py-1.5',
        primary: 'bg-transparent border border-accent text-accent hover:bg-accent hover:text-black',
        secondary: 'bg-transparent border border-green-900/50 text-text-secondary hover:border-accent/50',
      },
      input: {
        base: 'bg-black border border-green-900/50 rounded-none text-text-primary focus:border-accent',
      },
      badge: {
        base: 'rounded-none border border-green-900/50 text-accent',
      },
      select: {
        base: 'bg-black border border-green-900/50 rounded-none text-text-primary',
      },
    },
    layout: 'sidebar',
    navStyle: 'glow',
    font: {
      family: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
      import: 'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap',
      weight: '400',
      size: '14px',
    },
    interactions: {
      habitComplete: 'button-right',
    },
    animations: {
      cardEntrance: 'stagger-fade',
      completionCelebration: 'fade-quiet',
      hoverMicro: 'glow-border',
      streakFire: 'flicker-flame',
    },
    reward: {
      displayMode: 'toast',
      celebrationComponent: null,
    },
    pageLayout: {
      habitList: 'list',
      density: 'compact',
      rewardList: 'list',
    },
  },

  nature_forest: {
    name: 'Nature Forest',
    icon: '🌲',
    description: 'Deep greens and earthy browns with an organic, natural feel',
    cssVars: {
      '--color-bg-primary': '#0f1a0f',
      '--color-bg-card': '#1a2e1a',
      '--color-bg-card-hover': '#243824',
      '--color-text-primary': '#d4e7d4',
      '--color-text-secondary': '#8faa8f',
      '--color-accent': '#4ade80',
      '--color-accent-hover': '#22c55e',
      '--color-danger': '#f87171',
      '--color-streak-fire': '#fb923c',
    },
    classes: {
      card: {
        rounded: 'rounded-2xl',
        shadow: 'shadow-md shadow-green-950/30',
        border: 'border border-green-900/30',
        bg: 'bg-bg-card',
        hoverBg: 'hover:bg-bg-card-hover',
        extra: '',
      },
      button: {
        rounded: 'rounded-xl',
        padding: 'px-5 py-2',
        primary: 'bg-accent hover:bg-accent-hover text-black font-semibold',
        secondary: 'bg-green-900/30 hover:bg-green-900/50 text-text-secondary border border-green-900/30',
      },
      input: {
        base: 'bg-green-950/50 border border-green-900/30 rounded-xl text-text-primary',
      },
      badge: {
        base: 'rounded-lg bg-green-900/30 text-accent',
      },
      select: {
        base: 'bg-green-950/50 border border-green-900/30 rounded-xl text-text-primary',
      },
    },
    layout: 'sidebar',
    navStyle: 'default',
    font: {
      family: "'Nunito', system-ui, sans-serif",
      import: 'https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap',
      weight: '400',
      size: '16px',
    },
    interactions: {
      habitComplete: 'button-right',
    },
    animations: {
      cardEntrance: 'slide-up',
      completionCelebration: 'scale-up',
      hoverMicro: 'shadow-lift',
      streakFire: 'bounce',
    },
    reward: {
      displayMode: 'expand-from-card',
      celebrationComponent: null,
    },
    pageLayout: {
      habitList: 'list',
      density: 'spacious',
      rewardList: 'grid-2',
    },
  },

  minimalist_zen: {
    name: 'Minimalist Zen',
    icon: '🖊️',
    description: 'Ultra-clean monochrome with sharp edges and calm whitespace',
    cssVars: {
      '--color-bg-primary': '#ffffff',
      '--color-bg-card': '#ffffff',
      '--color-bg-card-hover': '#f9fafb',
      '--color-text-primary': '#111111',
      '--color-text-secondary': '#6b7280',
      '--color-accent': '#111111',
      '--color-accent-hover': '#374151',
      '--color-danger': '#dc2626',
      '--color-streak-fire': '#d97706',
    },
    classes: {
      card: {
        rounded: 'rounded-none',
        shadow: '',
        border: 'border-b border-gray-200',
        bg: 'bg-bg-card',
        hoverBg: 'hover:bg-bg-card-hover',
        extra: '',
      },
      button: {
        rounded: 'rounded-none',
        padding: 'px-4 py-2',
        primary: 'bg-accent hover:bg-accent-hover text-white',
        secondary: 'bg-transparent border border-gray-300 hover:border-gray-500 text-text-secondary',
      },
      input: {
        base: 'bg-white border-b border-gray-300 rounded-none text-text-primary',
      },
      badge: {
        base: 'rounded-none border border-gray-300 text-text-secondary',
      },
      select: {
        base: 'bg-white border-b border-gray-300 rounded-none text-text-primary',
      },
    },
    layout: 'sidebar',
    navStyle: 'underline',
    font: {
      family: 'system-ui, -apple-system, sans-serif',
      import: null,
      weight: '300',
      size: '16px',
    },
    interactions: {
      habitComplete: 'button-right',
    },
    animations: {
      cardEntrance: 'none',
      completionCelebration: 'fade-quiet',
      hoverMicro: 'none',
      streakFire: 'none',
    },
    reward: {
      displayMode: 'expand-from-card',
      celebrationComponent: null,
    },
    pageLayout: {
      habitList: 'list',
      density: 'spacious',
      rewardList: 'list',
    },
  },
};

// ── Backward-compatibility aliases ──────────────────────────────────
// Old theme IDs map to the closest new theme
const THEME_ALIASES = {
  dark_emerald: 'clean_modern',
  light_clean: 'clean_modern',
  neon_cyberpunk: 'gamified_arcade',
  warm_earth: 'clean_modern',
  ocean_gradient: 'gamified_arcade',
  ios_glass: 'clean_modern',
  minimal_ink: 'clean_modern',
};

export const defaultTheme = 'clean_modern';

export function getTheme(id) {
  const resolvedId = THEME_ALIASES[id] || id;
  const config = themes[resolvedId] || themes[defaultTheme];
  return resolveTheme(config);
}
