
## NOTA IMPORTANTE ESTE CODIGO CONTIENE YA LO VISUAL DE UNA VISTA QUE DEFINIREMOS EN US FUTURAS, PERO COMO TIENE LA DEFINICION PRINCIPAL DEL LAYOUT, POR ESO LA COMPARTO COMO REFF.
<!DOCTYPE html>

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>BetTracker 2.0 | Peaceful Control Center</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&amp;family=Geist+Mono:wght@400;500;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
        tailwind.config = {
          darkMode: "class",
          theme: {
            extend: {
              "colors": {
                      "on-tertiary": "#fff7f4",
                      "on-primary-container": "#6029c9",
                      "error": "#9e3f4e",
                      "on-secondary-fixed": "#314055",
                      "surface-dim": "#cadde9",
                      "primary-dim": "#612aca",
                      "tertiary-fixed": "#fe932c",
                      "tertiary-container": "#fe932c",
                      "secondary": "#506076",
                      "outline": "#6e7d86",
                      "surface-container-high": "#ddeaf3",
                      "surface-container-lowest": "#ffffff",
                      "on-secondary-container": "#435368",
                      "tertiary-fixed-dim": "#ed871e",
                      "on-secondary-fixed-variant": "#4d5d73",
                      "on-tertiary-fixed": "#240f00",
                      "secondary-container": "#d3e4fe",
                      "secondary-fixed-dim": "#c5d6f0",
                      "secondary-fixed": "#d3e4fe",
                      "primary-fixed-dim": "#ddcdff",
                      "on-surface": "#26343d",
                      "on-tertiary-fixed-variant": "#572c00",
                      "inverse-surface": "#0a0f12",
                      "on-primary": "#fcf5ff",
                      "primary-container": "#e9ddff",
                      "surface-container-highest": "#d5e5ef",
                      "surface-container": "#e5eff7",
                      "tertiary": "#914d00",
                      "on-error": "#fff7f7",
                      "background": "#f6fafe",
                      "error-container": "#ff8b9a",
                      "primary": "#6d3bd7",
                      "surface-variant": "#d5e5ef",
                      "on-primary-fixed-variant": "#6a37d4",
                      "inverse-on-surface": "#999da1",
                      "surface": "#f6fafe",
                      "secondary-dim": "#44546a",
                      "on-surface-variant": "#52616a",
                      "surface-container-low": "#eef4fa",
                      "on-primary-fixed": "#4d00b7",
                      "on-background": "#26343d",
                      "inverse-primary": "#a078ff",
                      "primary-fixed": "#e9ddff",
                      "on-tertiary-container": "#4a2500",
                      "surface-tint": "#6d3bd7",
                      "outline-variant": "#a4b4be",
                      "on-error-container": "#782232",
                      "on-secondary": "#f7f9ff",
                      "surface-bright": "#f6fafe",
                      "error-dim": "#4f0116",
                      "tertiary-dim": "#804300"
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
        body { font-family: 'Inter', sans-serif; background-color: #f6fafe; color: #26343d; }
        .geist-mono { font-family: 'Geist Mono', monospace; }
        .material-symbols-outlined { font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24; }
        .glass-effect { backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); }
        .chart-grid { background-image: radial-gradient(#6e7d86 0.5px, transparent 0.5px); background-size: 10px 10px; }
    </style>
</head>
<body class="bg-surface text-on-surface antialiased overflow-hidden">
<!-- Top Bar Component -->
<header class="bg-[#f6fafe]/80 dark:bg-[#0a0f12]/80 backdrop-blur-md font-['Inter'] tracking-tight font-semibold docked full-width top-0 z-50 sticky border-b border-[#26343d]/15 shadow-[0px_20px_40px_rgba(38,52,61,0.06)] flex justify-between items-center w-full px-6 py-3">
<div class="flex items-center gap-6">
<span class="text-xl font-bold text-[#26343d] dark:text-[#eef4fa]">BetTracker 2.0</span>
<div class="h-6 w-[1px] bg-outline-variant/30"></div>
<!-- Discipline Shield -->
<div class="bg-surface-container-lowest flex items-center gap-3 px-4 py-1.5 rounded-xl border border-outline-variant/10 shadow-sm">
<span class="material-symbols-outlined text-primary" data-icon="shield" style="font-variation-settings: 'FILL' 1;">shield</span>
<span class="geist-mono text-sm font-bold tracking-wider text-on-surface">1,250 DP</span>
</div>
</div>
<div class="flex items-center gap-4">
<div class="text-right hidden sm:block">
<p class="text-xs font-bold tracking-wider text-on-surface">Arquitecto Alpha</p>
<p class="text-[10px] uppercase tracking-widest text-primary font-bold">Level: Elite</p>
</div>
<img alt="Arquitecto Alpha" class="w-10 h-10 rounded-full border border-primary/20 bg-surface-container-high" data-alt="close-up portrait of a professional architect, minimalist lighting, clean aesthetics, soft focus background, corporate editorial style" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAroM565rpqT7E2gjXCA-0HnlNm3Lwa71nvOINkqs2Urbwk28jfbTjtFHnnPgWGa1WVu1f8u7SvKU0eP2JvCB8UdyaRf1Sfd4cJjtXnI2WzPYGBzmYN1OTRSkeGP2IR8r5EboKyPHzo18Brggixo7-mHZ2ooy6qrj2LU4Dto7r1PEUlT7kHyEOitwdrr6QMC8IGvCk4G7m5BWbpx-LbMlZfcxiC9whbNavoaJ2CAZGL8OJ62mW_ro1JqWJT_i_vXV5CnM9gdGJfQKM"/>
</div>
</header>
<div class="flex h-[calc(100vh-64px)] overflow-hidden">
<!-- Side Navigation Component -->
<aside class="bg-[#eef4fa] dark:bg-[#0d151a] font-['Inter'] text-sm tracking-wide uppercase font-medium h-screen w-64 border-r border-[#26343d]/15 flex flex-col h-full py-8 hidden md:flex">
<nav class="flex-1 space-y-1 px-4">
<!-- The Vault Active -->
<a class="flex items-center gap-3 px-4 py-3 text-[#8B5CF6] dark:text-[#a78bfa] font-bold border-r-2 border-[#8B5CF6] bg-surface-container-lowest/40 transition-all duration-300" href="#">
<span class="material-symbols-outlined" data-icon="account_balance">account_balance</span>
<span>The Vault</span>
</a>
<a class="flex items-center gap-3 px-4 py-3 text-[#52616a] dark:text-[#aeb9c0] hover:bg-[#ffffff]/50 transition-all duration-300" href="#">
<span class="material-symbols-outlined" data-icon="history">history</span>
<span>History</span>
</a>
<a class="flex items-center gap-3 px-4 py-3 text-[#52616a] dark:text-[#aeb9c0] hover:bg-[#ffffff]/50 transition-all duration-300" href="#">
<span class="material-symbols-outlined" data-icon="insights">insights</span>
<span>Strategy</span>
</a>
<a class="flex items-center gap-3 px-4 py-3 text-[#52616a] dark:text-[#aeb9c0] hover:bg-[#ffffff]/50 transition-all duration-300" href="#">
<span class="material-symbols-outlined" data-icon="person">person</span>
<span>Profile</span>
</a>
</nav>
<div class="px-6 mt-auto">
<button class="w-full bg-gradient-to-r from-primary to-primary-dim text-white py-3 rounded-xl font-bold tracking-tight text-xs uppercase flex items-center justify-center gap-2 shadow-lg">
<span class="material-symbols-outlined text-sm" data-icon="add">add</span>
                    New Analysis
                </button>
</div>
</aside>
<!-- Main Content Area: The Vault -->
<main class="flex-1 overflow-y-auto p-8 relative">
<div class="max-w-7xl mx-auto">
<header class="mb-10 flex justify-between items-end">
<div>
<h1 class="text-3xl font-bold tracking-tighter text-on-surface">The Vault</h1>
<p class="text-on-surface-variant mt-1 text-sm">Deep-tier market insights curated for elite capital management.</p>
</div>
<div class="flex gap-2">
<span class="text-[10px] font-bold tracking-widest uppercase text-outline-variant px-3 py-1 border border-outline-variant/20 rounded-full">Updated 12m ago</span>
</div>
</header>
<!-- Bento Grid / 3x3 Grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
<!-- Unlocked Card 1 -->
<div class="bg-surface-container-lowest rounded-xl p-6 shadow-sm border border-outline-variant/10 group hover:shadow-md transition-shadow relative">
<!-- Action Menu -->
<div class="absolute top-4 right-4 flex flex-col items-end gap-1">
<button class="text-outline-variant hover:text-on-surface transition-colors">
<span class="material-symbols-outlined text-xl">more_horiz</span>
</button>
<!-- Quick Settlement Overlay -->
<div class="bg-surface-container-lowest shadow-xl border border-outline-variant/10 rounded-lg py-1 px-1 flex gap-1 z-20">
<button class="geist-mono text-[10px] font-bold w-6 h-6 flex items-center justify-center rounded bg-primary/10 text-primary hover:bg-primary hover:text-white transition-all">P</button>
<button class="geist-mono text-[10px] font-bold w-6 h-6 flex items-center justify-center rounded bg-error/10 text-error hover:bg-error hover:text-white transition-all">L</button>
<button class="geist-mono text-[10px] font-bold w-6 h-6 flex items-center justify-center rounded bg-on-surface-variant/10 text-on-surface-variant hover:bg-on-surface-variant hover:text-white transition-all">P</button>
</div>
</div>
<div class="flex justify-between items-start mb-4 pr-12">
<span class="text-[10px] font-black uppercase tracking-widest text-[#8B5CF6]">European Handi.</span>
<span class="geist-mono text-xs font-bold text-on-surface-variant">Conf: 88%</span>
</div>
<h3 class="font-bold text-lg mb-2">London vs. Madrid</h3>
<p class="text-xs text-on-surface-variant leading-relaxed mb-6 italic">"Human Translation: Historical data suggests a pivot in mid-week liquidity. Recommended entry post-announcement."</p>
<div class="h-24 w-full relative mb-4 border border-outline-variant/5 rounded-lg overflow-hidden bg-surface-container-low/30 chart-grid">
<svg class="absolute inset-0 w-full h-full" preserveaspectratio="none" viewbox="0 0 100 100">
<path d="M0 80 Q 25 70, 40 50 T 70 30 T 100 10" fill="none" stroke="#8B5CF6" stroke-width="2"></path>
</svg>
<div class="absolute bottom-1 right-2 geist-mono text-[8px] text-outline-variant">+12.4% ROI</div>
</div>
<div class="flex justify-between items-center pt-4 border-t border-outline-variant/5">
<span class="geist-mono text-sm font-bold text-on-surface">1.92 <span class="text-[10px] text-[#8B5CF6]">ODDS</span></span>
<span class="material-symbols-outlined text-[#8B5CF6] text-lg" data-icon="arrow_outward">arrow_outward</span>
</div>
</div>
<!-- Unlocked Card 2 (Match Analysis) -->
<div class="bg-surface-container-lowest rounded-xl p-6 shadow-sm border border-outline-variant/10 group hover:shadow-md transition-shadow relative">
<div class="absolute top-4 right-4">
<button class="text-outline-variant hover:text-on-surface transition-colors">
<span class="material-symbols-outlined text-xl">more_horiz</span>
</button>
</div>
<div class="flex justify-between items-start mb-4 pr-10">
<span class="text-[10px] font-black uppercase tracking-widest text-[#8B5CF6]">Total Goals</span>
<span class="geist-mono text-xs font-bold text-on-surface-variant">Conf: 92%</span>
</div>
<h3 class="font-bold text-lg mb-2">New York vs. Paris</h3>
<p class="text-xs text-on-surface-variant leading-relaxed mb-6 italic">"Human Translation: Value found in defensive stability. Statistical outliers suggest a low-scoring encounter."</p>
<div class="h-24 w-full relative mb-4 border border-outline-variant/5 rounded-lg overflow-hidden bg-surface-container-low/30 chart-grid">
<svg class="absolute inset-0 w-full h-full" preserveaspectratio="none" viewbox="0 0 100 100">
<path d="M0 90 L 20 80 L 40 85 L 60 60 L 80 65 L 100 40" fill="none" stroke="#8B5CF6" stroke-width="2"></path>
</svg>
<div class="absolute bottom-1 right-2 geist-mono text-[8px] text-outline-variant">+6.8% ROI</div>
</div>
<div class="flex justify-between items-center pt-4 border-t border-outline-variant/5">
<span class="geist-mono text-sm font-bold text-on-surface">2.10 <span class="text-[10px] text-[#8B5CF6]">ODDS</span></span>
<span class="material-symbols-outlined text-[#8B5CF6] text-lg" data-icon="arrow_outward">arrow_outward</span>
</div>
</div>
<!-- Unlocked Card 3 (Match Analysis) -->
<div class="bg-surface-container-lowest rounded-xl p-6 shadow-sm border border-outline-variant/10 group hover:shadow-md transition-shadow relative">
<div class="absolute top-4 right-4">
<button class="text-outline-variant hover:text-on-surface transition-colors">
<span class="material-symbols-outlined text-xl">more_horiz</span>
</button>
</div>
<div class="flex justify-between items-start mb-4 pr-10">
<span class="text-[10px] font-black uppercase tracking-widest text-[#8B5CF6]">Moneyline Alpha</span>
<span class="geist-mono text-xs font-bold text-on-surface-variant">Conf: 79%</span>
</div>
<h3 class="font-bold text-lg mb-2">Tokyo vs. Berlin</h3>
<p class="text-xs text-on-surface-variant leading-relaxed mb-6 italic">"Human Translation: High variance expected due to weather. Entry only recommended with partial coverage."</p>
<div class="h-24 w-full relative mb-4 border border-outline-variant/5 rounded-lg overflow-hidden bg-surface-container-low/30 chart-grid">
<svg class="absolute inset-0 w-full h-full" preserveaspectratio="none" viewbox="0 0 100 100">
<path d="M0 50 Q 20 20, 50 60 T 100 40" fill="none" stroke="#8B5CF6" stroke-width="2"></path>
</svg>
<div class="absolute bottom-1 right-2 geist-mono text-[8px] text-outline-variant">+15.2% ROI</div>
</div>
<div class="flex justify-between items-center pt-4 border-t border-outline-variant/5">
<span class="geist-mono text-sm font-bold text-on-surface">2.45 <span class="text-[10px] text-[#8B5CF6]">ODDS</span></span>
<span class="material-symbols-outlined text-[#8B5CF6] text-lg" data-icon="arrow_outward">arrow_outward</span>
</div>
</div>
<!-- Unlocked Card 4 (Match Analysis) -->
<div class="bg-surface-container-lowest rounded-xl p-6 shadow-sm border border-outline-variant/10 group hover:shadow-md transition-shadow relative">
<div class="absolute top-4 right-4">
<button class="text-outline-variant hover:text-on-surface transition-colors">
<span class="material-symbols-outlined text-xl">more_horiz</span>
</button>
</div>
<div class="flex justify-between items-start mb-4 pr-10">
<span class="text-[10px] font-black uppercase tracking-widest text-[#8B5CF6]">Asian Spread</span>
<span class="geist-mono text-xs font-bold text-on-surface-variant">Conf: 94%</span>
</div>
<h3 class="font-bold text-lg mb-2">Milan vs. Lisbon</h3>
<p class="text-xs text-on-surface-variant leading-relaxed mb-6 italic">"Human Translation: Market mispricing detected in the away dog. Strong support at current price levels."</p>
<div class="h-24 w-full relative mb-4 border border-outline-variant/5 rounded-lg overflow-hidden bg-surface-container-low/30 chart-grid">
<svg class="absolute inset-0 w-full h-full" preserveaspectratio="none" viewbox="0 0 100 100">
<path d="M0 95 L 30 70 L 50 75 L 100 10" fill="none" stroke="#8B5CF6" stroke-width="2"></path>
</svg>
<div class="absolute bottom-1 right-2 geist-mono text-[8px] text-outline-variant">+22.1% ROI</div>
</div>
<div class="flex justify-between items-center pt-4 border-t border-outline-variant/5">
<span class="geist-mono text-sm font-bold text-on-surface">1.88 <span class="text-[10px] text-[#8B5CF6]">ODDS</span></span>
<span class="material-symbols-outlined text-[#8B5CF6] text-lg" data-icon="arrow_outward">arrow_outward</span>
</div>
</div>
<!-- Locked Card Example (Kept for variety) -->
<div class="relative bg-surface-container-lowest rounded-xl p-6 shadow-sm border border-outline-variant/10 overflow-hidden group">
<div class="absolute inset-0 z-10 glass-effect bg-white/40 flex flex-col items-center justify-center text-center px-6">
<span class="material-symbols-outlined text-primary-dim text-3xl mb-3" data-icon="lock" style="font-variation-settings: 'FILL' 1;">lock</span>
<h4 class="font-bold text-on-surface text-sm mb-4">Quarterly Trend Analysis</h4>
<button class="bg-primary hover:bg-primary-dim text-white text-[10px] font-bold uppercase tracking-widest px-6 py-3 rounded-xl shadow-lg transition-all transform active:scale-95">
                                Unlock for 500 DP
                            </button>
</div>
<div class="blur-md pointer-events-none select-none">
<div class="h-4 w-24 bg-surface-container-high mb-4"></div>
<div class="h-8 w-full bg-surface-container-high mb-4"></div>
<div class="h-20 w-full bg-surface-container-high rounded-lg mb-4"></div>
</div>
</div>
<!-- Unlocked Card 5 -->
<div class="bg-surface-container-lowest rounded-xl p-6 shadow-sm border border-outline-variant/10 group hover:shadow-md transition-shadow relative">
<div class="absolute top-4 right-4">
<button class="text-outline-variant hover:text-on-surface transition-colors">
<span class="material-symbols-outlined text-xl">more_horiz</span>
</button>
</div>
<div class="flex justify-between items-start mb-4 pr-10">
<span class="text-[10px] font-black uppercase tracking-widest text-[#8B5CF6]">Equity Curve</span>
<span class="geist-mono text-xs font-bold text-on-surface-variant">Conf: 85%</span>
</div>
<h3 class="font-bold text-lg mb-2">Steady Growth Matrix</h3>
<p class="text-xs text-on-surface-variant leading-relaxed mb-6 italic">"Human Translation: Risk parameters indicate an oversold condition. Diversification required across 3 sectors."</p>
<div class="h-24 w-full relative mb-4 border border-outline-variant/5 rounded-lg overflow-hidden bg-surface-container-low/30 chart-grid">
<svg class="absolute inset-0 w-full h-full" preserveaspectratio="none" viewbox="0 0 100 100">
<path d="M0 60 Q 30 50, 50 30 T 100 5" fill="none" stroke="#8B5CF6" stroke-width="2"></path>
</svg>
<div class="absolute bottom-1 right-2 geist-mono text-[8px] text-outline-variant">+8.2% ROI</div>
</div>
<div class="flex justify-between items-center pt-4 border-t border-outline-variant/5">
<span class="geist-mono text-sm font-bold text-on-surface">1.75 <span class="text-[10px] text-[#8B5CF6]">ODDS</span></span>
<span class="material-symbols-outlined text-[#8B5CF6] text-lg" data-icon="arrow_outward">arrow_outward</span>
</div>
</div>
</div>
</div>
</main>
</div>
</body></html>