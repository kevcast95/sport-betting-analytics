<!DOCTYPE html>

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,600;0,700;1,400&amp;family=Geist+Mono:wght@400;700&amp;family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<script id="tailwind-config">
      tailwind.config = {
        darkMode: "class",
        theme: {
          extend: {
            "colors": {
                    "on-tertiary": "#fff7f4",
                    "on-surface-variant": "#52616a",
                    "error": "#9e3f4e",
                    "inverse-surface": "#0a0f12",
                    "surface-tint": "#6d3bd7",
                    "primary-fixed-dim": "#ddcdff",
                    "secondary-container": "#d3e4fe",
                    "on-primary-fixed-variant": "#6a37d4",
                    "secondary-fixed-dim": "#c5d6f0",
                    "on-error-container": "#782232",
                    "error-dim": "#4f0116",
                    "on-tertiary-container": "#4a2500",
                    "on-secondary-fixed-variant": "#4d5d73",
                    "inverse-on-surface": "#999da1",
                    "surface-dim": "#cadde9",
                    "on-background": "#26343d",
                    "on-error": "#fff7f7",
                    "tertiary-fixed": "#fe932c",
                    "on-primary-fixed": "#4d00b7",
                    "secondary-fixed": "#d3e4fe",
                    "on-secondary-container": "#435368",
                    "inverse-primary": "#a078ff",
                    "on-primary-container": "#6029c9",
                    "surface-bright": "#f6fafe",
                    "primary-dim": "#612aca",
                    "on-tertiary-fixed-variant": "#572c00",
                    "secondary": "#506076",
                    "surface-container": "#e5eff7",
                    "surface": "#f6fafe",
                    "surface-container-highest": "#d5e5ef",
                    "tertiary-fixed-dim": "#ed871e",
                    "tertiary-container": "#fe932c",
                    "surface-container-high": "#ddeaf3",
                    "outline": "#6e7d86",
                    "tertiary-dim": "#804300",
                    "primary-fixed": "#e9ddff",
                    "on-tertiary-fixed": "#240f00",
                    "background": "#f6fafe",
                    "on-primary": "#fcf5ff",
                    "tertiary": "#914d00",
                    "on-secondary-fixed": "#314055",
                    "surface-container-low": "#eef4fa",
                    "outline-variant": "#a4b4be",
                    "on-surface": "#26343d",
                    "primary-container": "#e9ddff",
                    "surface-variant": "#d5e5ef",
                    "primary": "#6d3bd7",
                    "error-container": "#ff8b9a",
                    "surface-container-lowest": "#ffffff",
                    "secondary-dim": "#44546a",
                    "on-secondary": "#f7f9ff"
            },
            "borderRadius": {
                    "DEFAULT": "0.125rem",
                    "lg": "0.25rem",
                    "xl": "0.5rem",
                    "full": "0.75rem"
            },
            "fontFamily": {
                    "headline": ["Inter"],
                    "body": ["Inter"],
                    "label": ["Inter"],
                    "mono": ["Geist Mono"]
            }
          },
        },
      }
    </script>
<style>
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        }
        body { font-family: 'Inter', sans-serif; }
        .mono { font-family: 'Geist Mono', monospace; }
        .progress-bar-glow { box-shadow: 0 0 12px rgba(139, 92, 246, 0.3); }
        .glass-panel { background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(12px); }
    </style>
</head>
<body class="bg-surface text-on-surface min-h-screen">
<!-- Top Progress Indicator (Focus Mode) -->
<div class="fixed top-0 left-0 w-full h-1 bg-surface-container z-[60]">
<div class="h-full bg-primary progress-bar-glow" style="width: 45%;"></div>
</div>
<!-- Header Shell (Identity Diagnostic) -->
<header class="fixed top-0 w-full border-b-[0.5px] border-[#8B5CF6]/15 bg-surface/80 backdrop-blur-md z-50 flex justify-between items-center px-8 py-4">
<div class="font-['Geist_Mono'] text-xs tracking-[0.05em] uppercase text-on-surface-variant">Identity Diagnostic</div>
<div class="font-headline tracking-tight text-on-surface font-semibold">Step 04 / 09</div>
<button class="text-on-surface-variant hover:bg-surface-container-low transition-colors px-4 py-1.5 rounded-xl text-sm font-medium">Exit Focus</button>
</header>
<main class="pt-24 pb-32 max-w-4xl mx-auto px-6">
<!-- Question Section -->
<section class="mt-12 space-y-8">
<!-- Header/Quote -->
<div class="text-center space-y-6 px-12">
<blockquote class="italic text-on-surface-variant text-lg leading-relaxed font-light">
                    "The market is a device for transferring money from the impatient to the patient."
                </blockquote>
<h1 class="text-3xl font-bold tracking-tight text-on-surface">
                    In the event of a 5% bankroll drawdown, what is your first protocol adjustment?
                </h1>
</div>
<!-- Selectable Options -->
<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-12">
<button class="group relative flex flex-col items-center justify-center p-8 bg-surface-container-lowest border border-outline-variant/20 rounded-xl hover:border-primary/40 hover:bg-primary-container/10 transition-all duration-300">
<span class="material-symbols-outlined text-primary mb-4 opacity-60 group-hover:opacity-100" data-icon="rebase_edit">rebase_edit</span>
<span class="text-sm font-semibold tracking-wide uppercase text-on-surface">Recalibrate Stake Unit</span>
<div class="absolute inset-0 rounded-xl border-primary opacity-0 group-focus:opacity-100 group-focus:border-2 transition-opacity pointer-events-none"></div>
</button>
<button class="group relative flex flex-col items-center justify-center p-8 bg-surface-container-lowest border border-outline-variant/20 rounded-xl hover:border-primary/40 hover:bg-primary-container/10 transition-all duration-300">
<span class="material-symbols-outlined text-primary mb-4 opacity-60 group-hover:opacity-100" data-icon="shield">shield</span>
<span class="text-sm font-semibold tracking-wide uppercase text-on-surface">Execute Hedge Protocol</span>
<div class="absolute inset-0 rounded-xl border-primary opacity-0 group-focus:opacity-100 group-focus:border-2 transition-opacity pointer-events-none"></div>
</button>
<button class="group relative flex flex-col items-center justify-center p-8 bg-surface-container-lowest border border-outline-variant/20 rounded-xl hover:border-primary/40 hover:bg-primary-container/10 transition-all duration-300">
<span class="material-symbols-outlined text-primary mb-4 opacity-60 group-hover:opacity-100" data-icon="logout">logout</span>
<span class="text-sm font-semibold tracking-wide uppercase text-on-surface">Immediate Market Exit</span>
<div class="absolute inset-0 rounded-xl border-primary opacity-0 group-focus:opacity-100 group-focus:border-2 transition-opacity pointer-events-none"></div>
</button>
</div>
</section>
<!-- Preview Mockup Section (Operator Profile) -->
<section class="mt-24 border-t border-outline-variant/10 pt-16">
<div class="flex flex-col items-center">
<span class="mono text-[10px] uppercase tracking-widest text-on-surface-variant mb-8">Evolving Operator Profile</span>
<div class="grid grid-cols-1 md:grid-cols-2 gap-8 w-full">
<!-- Identity Badge -->
<div class="bg-surface-container-low rounded-xl p-8 flex items-center gap-6">
<div class="w-20 h-20 rounded-full bg-primary flex items-center justify-center relative overflow-hidden">
<img class="absolute inset-0 w-full h-full object-cover opacity-80 mix-blend-overlay grayscale" data-alt="portrait of a focused professional analyst in a high-tech environment with cinematic lighting and soft bokeh" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBRQJo6vabtAHvSvPR2pYG8YS5girjz0JSoIDWQ9aV9V4hf4vTlxImm2m8urHK7-FRPhbphZ_C1d63soT6KNc_4GJTYD0TL4EGFy49ScwvVgrIuhh-ch5oV3f6iWIMxO15Q18AcCeTUmje0uaj_vEA1JQAPzObhpQlNRXhVn1-GeqksAX85zeIvsZ6azTbIXLbc29EGCiQpOGb071KZpt65-_acjcSOHKgWEvkJujVjFkHyseVOoPHOiyNkgkzkZuazgR-vCIfxStk"/>
<span class="material-symbols-outlined text-on-primary text-3xl relative z-10" data-icon="verified_user">verified_user</span>
</div>
<div>
<div class="flex items-center gap-2 mb-1">
<h3 class="font-bold text-xl tracking-tight">The Guardian</h3>
<span class="bg-primary/10 text-primary text-[10px] px-2 py-0.5 rounded-full mono font-bold tracking-tighter">TIER II</span>
</div>
<p class="text-on-surface-variant text-sm leading-relaxed max-w-[240px]">
                                Risk mitigation is prioritized over aggressive expansion. Current profile signals 98% system integrity.
                            </p>
</div>
</div>
<!-- Technical Stats -->
<div class="bg-surface-container-low rounded-xl p-8 space-y-4">
<div class="flex justify-between items-end border-b border-outline-variant/10 pb-2">
<span class="mono text-[10px] uppercase tracking-wider text-on-surface-variant">System Integrity</span>
<span class="mono text-lg font-bold text-primary">0.942</span>
</div>
<div class="flex justify-between items-end border-b border-outline-variant/10 pb-2">
<span class="mono text-[10px] uppercase tracking-wider text-on-surface-variant">Discipline Points</span>
<div class="flex items-center gap-2">
<span class="material-symbols-outlined text-primary text-sm" data-icon="security">security</span>
<span class="mono text-lg font-bold text-on-surface">1,240 XP</span>
</div>
</div>
<div class="flex justify-between items-end border-b border-outline-variant/10 pb-2">
<span class="mono text-[10px] uppercase tracking-wider text-on-surface-variant">Operator Status</span>
<span class="mono text-xs font-bold text-tertiary">STABLE_V4</span>
</div>
</div>
</div>
</div>
</section>
</main>
<!-- Bottom Status (Navigation-less but informative) -->
<footer class="fixed bottom-0 left-0 w-full z-50 flex justify-center gap-12 px-12 pb-8 bg-gradient-to-t from-surface to-transparent pointer-events-none">
<div class="pointer-events-auto flex gap-12 bg-surface-container-lowest/80 backdrop-blur px-8 py-3 rounded-full border border-outline-variant/15">
<div class="flex items-center gap-2">
<span class="material-symbols-outlined text-[18px] text-primary" data-icon="monitoring">monitoring</span>
<span class="mono text-[10px] uppercase tracking-widest text-on-surface">Technical Status: Nominal</span>
</div>
<div class="flex items-center gap-2 opacity-30">
<span class="material-symbols-outlined text-[18px]" data-icon="security">security</span>
<span class="mono text-[10px] uppercase tracking-widest text-on-surface">System Integrity</span>
</div>
<div class="flex items-center gap-2 opacity-30">
<span class="material-symbols-outlined text-[18px]" data-icon="fingerprint">fingerprint</span>
<span class="mono text-[10px] uppercase tracking-widest text-on-surface">Operator ID</span>
</div>
</div>
</footer>
</body></html>