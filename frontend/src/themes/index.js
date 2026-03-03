/**
 * Theme definitions for the Habit Reward app.
 *
 * Each theme provides:
 *  - name        Display label shown in the picker
 *  - icon        Emoji for the picker card
 *  - cssVars     CSS custom-property overrides applied to <html>
 *  - classes     Structural class tokens used by components
 *    - card        { rounded, shadow, border, bg, hoverBg, extra }
 *    - button      { rounded, padding, primary, secondary }
 *    - input       { base }
 *    - badge       { base }
 *    - select      { base }
 *  - layout      'sidebar' | 'topbar'
 *  - navStyle    'default' | 'frosted' | 'underline' | 'glow'
 */

export const themes = {
  dark_emerald: {
    name: 'Dark Emerald',
    icon: '🌑',
    description: 'Classic dark theme with emerald accents',
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
  },

  light_clean: {
    name: 'Light Clean',
    icon: '☀️',
    description: 'Airy light theme with indigo accents',
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
  },

  neon_cyberpunk: {
    name: 'Neon Cyberpunk',
    icon: '🌐',
    description: 'Futuristic neon glow on deep navy',
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
    navStyle: 'frosted',
  },

  warm_earth: {
    name: 'Warm Earth',
    icon: '🌿',
    description: 'Cozy dark stone with warm amber tones',
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
  },

  ocean_gradient: {
    name: 'Ocean Gradient',
    icon: '🌊',
    description: 'Deep slate with sky-to-teal gradients',
    cssVars: {
      '--color-bg-primary': '#0f172a',
      '--color-bg-card': 'rgba(15,23,42,0.7)',
      '--color-bg-card-hover': 'rgba(30,41,59,0.8)',
      '--color-text-primary': '#e2e8f0',
      '--color-text-secondary': '#94a3b8',
      '--color-accent': '#0ea5e9',
      '--color-accent-hover': '#38bdf8',
      '--color-danger': '#f43f5e',
      '--color-streak-fire': '#f97316',
    },
    classes: {
      card: {
        rounded: 'rounded-2xl',
        shadow: 'shadow-xl shadow-sky-900/20',
        border: 'border border-sky-900/30',
        bg: 'bg-bg-card backdrop-blur-sm',
        hoverBg: 'hover:bg-bg-card-hover',
        extra: '',
      },
      button: {
        rounded: 'rounded-xl',
        padding: 'px-4 py-2',
        primary: 'bg-gradient-to-r from-sky-500 to-teal-500 hover:from-sky-400 hover:to-teal-400 text-white shadow-md',
        secondary: 'bg-slate-700/50 hover:bg-slate-600/50 text-text-secondary border border-slate-600/30',
      },
      input: {
        base: 'bg-slate-800/60 border border-sky-900/30 rounded-xl text-text-primary backdrop-blur-sm',
      },
      badge: {
        base: 'rounded-lg bg-sky-900/30 text-sky-300',
      },
      select: {
        base: 'bg-slate-800/60 border border-sky-900/30 rounded-xl text-text-primary',
      },
    },
    layout: 'topbar',
    navStyle: 'default',
  },

  ios_glass: {
    name: 'iOS Glass',
    icon: '🍎',
    description: 'Full glassmorphism with translucent layers',
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
  },

  minimal_ink: {
    name: 'Minimal Ink',
    icon: '🖊️',
    description: 'Ultra-clean monochrome with sharp edges',
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
  },
};

export const defaultTheme = 'dark_emerald';

export function getTheme(id) {
  return themes[id] || themes[defaultTheme];
}
