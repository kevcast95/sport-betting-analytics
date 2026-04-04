<!DOCTYPE html>

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>BetTracker 2.0 | Strategy &amp; Performance</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&amp;family=Geist+Mono:wght@400;500;600&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
        tailwind.config = {
            darkMode: "class",
            theme: {
                extend: {
                    "colors": {
                        "primary-container": "#e9ddff",
                        "error-container": "#ff8b9a",
                        "inverse-primary": "#a078ff",
                        "surface-container-high": "#ddeaf3",
                        "on-tertiary-container": "#4a2500",
                        "surface-bright": "#f6fafe",
                        "surface-tint": "#6d3bd7",
                        "on-primary": "#fcf5ff",
                        "error-dim": "#4f0116",
                        "error": "#9e3f4e",
                        "primary-fixed-dim": "#ddcdff",
                        "on-tertiary": "#fff7f4",
                        "on-surface": "#26343d",
                        "on-secondary-container": "#435368",
                        "tertiary-fixed": "#fe932c",
                        "on-surface-variant": "#52616a",
                        "primary-dim": "#612aca",
                        "on-tertiary-fixed-variant": "#572c00",
                        "tertiary-container": "#fe932c",
                        "on-secondary-fixed": "#314055",
                        "on-primary-fixed": "#4d00b7",
                        "primary": "#6d3bd7",
                        "tertiary-dim": "#804300",
                        "surface-container-lowest": "#ffffff",
                        "surface-variant": "#d5e5ef",
                        "secondary-container": "#d3e4fe",
                        "outline-variant": "#a4b4be",
                        "secondary": "#506076",
                        "on-error": "#fff7f7",
                        "on-secondary": "#f7f9ff",
                        "on-background": "#26343d",
                        "secondary-fixed-dim": "#c5d6f0",
                        "tertiary-fixed-dim": "#ed871e",
                        "on-primary-container": "#6029c9",
                        "surface-container": "#e5eff7",
                        "inverse-on-surface": "#999da1",
                        "tertiary": "#914d00",
                        "surface-container-highest": "#d5e5ef",
                        "inverse-surface": "#0a0f12",
                        "primary-fixed": "#e9ddff",
                        "surface-dim": "#cadde9",
                        "on-primary-fixed-variant": "#6a37d4",
                        "surface-container-low": "#eef4fa",
                        "secondary-dim": "#44546a",
                        "on-tertiary-fixed": "#240f00",
                        "outline": "#6e7d86",
                        "background": "#f6fafe",
                        "secondary-fixed": "#d3e4fe",
                        "on-error-container": "#782232",
                        "on-secondary-fixed-variant": "#4d5d73",
                        "surface": "#f6fafe"
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
        body { font-family: 'Inter', sans-serif; background-color: #f6fafe; }
        .geist-mono { font-family: 'Geist Mono', monospace; }
        .glass-nav { backdrop-filter: blur(20px); }
        .material-symbols-outlined { font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24; }
    </style>
</head>
<body class="text-on-surface">
<!-- TopNavBar -->
<header class="bg-[#f6fafe]/80 dark:bg-[#0a0f12]/80 backdrop-blur-md flex justify-between items-center w-full px-6 py-3 border-b border-[#26343d]/15 shadow-[0px_20px_40px_rgba(38,52,61,0.06)] docked full-width top-0 z-50 sticky">
<div class="flex items-center gap-4">
<span class="text-xl font-bold text-[#26343d] dark:text-[#eef4fa] font-['Inter'] tracking-tight">BetTracker 2.0</span>
</div>
<div class="flex items-center gap-6">
<!-- Discipline Wallet Component -->
<div class="bg-surface-container-lowest px-4 py-1.5 rounded-full flex items-center gap-2 shadow-sm border border-primary/10">
<span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">shield</span>
<span class="geist-mono font-bold text-on-surface">1,250 DP</span>
</div>
<div class="flex items-center gap-3">
<div class="text-right hidden md:block">
<p class="text-sm font-bold text-on-surface leading-none">Arquitecto Alpha</p>
<p class="text-[10px] uppercase tracking-widest text-on-surface-variant mt-1">Level: Elite</p>
</div>
<div class="h-10 w-10 rounded-full bg-surface-container-high border border-outline-variant/20 overflow-hidden">
<img alt="Arquitecto Alpha" class="h-full w-full object-cover" data-alt="professional portrait of a confident man with glasses in a minimalist architectural office setting with soft natural light" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCPiJLtdA-z72vZQhKchhLpy0nqPDoR2TeQAhXDmtIqibH35v0vNmeW8W9BHpJ4L-x3hrfQXG-tNdgtXFEuphZrV3H6xvNfuGoDXQG18YpffbOW__i_Kvo0KdbAME_SD6DaqHUK--Aw6EPZY5xBLjeXKNwI0K8Pyr07NCH9PaptUQESHcoxnhqYrtBxFDXMepsCzEdun-iFHz8T-776mUq3BchiAFFckcqc5J1VQcQxnqSm2CaSNP9By94qq5RrRqAkjEmmeEPCI84"/>
</div>
</div>
</div>
</header>
<div class="flex min-h-[calc(100vh-64px)]">
<!-- SideNavBar -->
<aside class="bg-[#eef4fa] dark:bg-[#0d151a] h-screen w-64 border-r border-[#26343d]/15 flex flex-col py-8 sticky top-16 hidden md:flex">
<nav class="flex-1 space-y-1 px-4">
<a class="flex items-center gap-3 px-4 py-3 text-[#8B5CF6] dark:text-[#a78bfa] font-bold border-r-2 border-[#8B5CF6] transition-all duration-300 ease-in-out font-['Inter'] text-sm tracking-wide uppercase font-medium" href="#">
<span class="material-symbols-outlined" data-icon="account_balance" style="font-variation-settings: 'FILL' 1;">account_balance</span>
<span>The Vault</span>
</a>
<a class="flex items-center gap-3 px-4 py-3 text-[#52616a] dark:text-[#aeb9c0] hover:bg-[#ffffff]/50 dark:hover:bg-[#ffffff]/5 transition-all duration-300 ease-in-out font-['Inter'] text-sm tracking-wide uppercase font-medium" href="#">
<span class="material-symbols-outlined" data-icon="history">history</span>
<span>History</span>
</a>
<a class="flex items-center gap-3 px-4 py-3 text-[#52616a] dark:text-[#aeb9c0] hover:bg-[#ffffff]/50 dark:hover:bg-[#ffffff]/5 transition-all duration-300 ease-in-out font-['Inter'] text-sm tracking-wide uppercase font-medium" href="#">
<span class="material-symbols-outlined" data-icon="insights">insights</span>
<span>Strategy</span>
</a>
<a class="flex items-center gap-3 px-4 py-3 text-[#52616a] dark:text-[#aeb9c0] hover:bg-[#ffffff]/50 dark:hover:bg-[#ffffff]/5 transition-all duration-300 ease-in-out font-['Inter'] text-sm tracking-wide uppercase font-medium" href="#">
<span class="material-symbols-outlined" data-icon="person">person</span>
<span>Profile</span>
</a>
</nav>
<div class="px-6 mt-auto">
<button class="w-full bg-gradient-to-r from-primary to-primary-dim text-white py-3 rounded-xl font-bold text-sm tracking-tight shadow-lg hover:scale-95 transition-all duration-200">
                    New Analysis
                </button>
</div>
</aside>
<!-- Main Content -->
<main class="flex-1 p-8 md:p-12 max-w-7xl mx-auto">
<header class="mb-12">
<h1 class="text-4xl font-extrabold tracking-tight text-on-surface mb-2">Strategy &amp; Performance</h1>
<p class="text-on-surface-variant font-medium tracking-wide text-sm uppercase opacity-70">The Alpha Protocol Executive Summary</p>
</header>
<!-- Summary Metrics Bento Grid -->
<div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
<div class="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/15 hover:shadow-md transition-shadow">
<p class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-4">Overall ROI</p>
<div class="flex items-baseline gap-2">
<span class="geist-mono text-3xl font-bold text-primary">+18.4%</span>
<span class="material-symbols-outlined text-primary text-sm" style="font-variation-settings: 'FILL' 1;">trending_up</span>
</div>
</div>
<div class="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/15 hover:shadow-md transition-shadow">
<p class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-4">Win Rate</p>
<div class="flex items-baseline gap-2">
<span class="geist-mono text-3xl font-bold text-on-surface">64.2%</span>
</div>
</div>
<div class="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/15 hover:shadow-md transition-shadow">
<p class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-4">Max Drawdown</p>
<div class="flex items-baseline gap-2">
<span class="geist-mono text-3xl font-bold text-tertiary">-4.2%</span>
<span class="material-symbols-outlined text-tertiary text-sm">warning</span>
</div>
</div>
<div class="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/15 hover:shadow-md transition-shadow">
<p class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-4">Discipline Gained</p>
<div class="flex items-baseline gap-2">
<span class="geist-mono text-3xl font-bold text-primary">+850</span>
<span class="material-symbols-outlined text-primary text-sm" style="font-variation-settings: 'FILL' 1;">verified</span>
</div>
</div>
</div>
<div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
<!-- Interactive Strategy Chart Section -->
<div class="lg:col-span-2 space-y-8">
<section class="bg-surface-container-lowest p-8 rounded-xl border border-outline-variant/15">
<div class="flex justify-between items-center mb-8">
<h2 class="text-lg font-bold tracking-tight">Equity Curve Performance</h2>
<div class="flex gap-2">
<span class="px-3 py-1 bg-surface-container-low text-[10px] font-bold rounded-full uppercase">12 Months</span>
<span class="px-3 py-1 text-[10px] font-bold rounded-full uppercase text-on-surface-variant">Log Scale</span>
</div>
</div>
<!-- Visual Mockup of the Chart -->
<div class="relative h-72 w-full bg-surface-container-low/30 rounded-lg overflow-hidden flex flex-col justify-end">
<!-- Background Grid Lines -->
<div class="absolute inset-0 grid grid-cols-6 grid-rows-4 pointer-events-none opacity-20">
<div class="border-r border-b border-outline-variant"></div>
<div class="border-r border-b border-outline-variant"></div>
<div class="border-r border-b border-outline-variant"></div>
<div class="border-r border-b border-outline-variant"></div>
<div class="border-r border-b border-outline-variant"></div>
<div class="border-b border-outline-variant"></div>
</div>
<!-- Confidence Interval Shadow (SVG Mock) -->
<svg class="absolute inset-0 w-full h-full" preserveaspectratio="none">
<path d="M0 250 Q 150 200, 300 180 T 600 120 T 900 80 L 900 280 L 0 280 Z" fill="rgba(164, 180, 190, 0.15)"></path>
<path d="M0 250 Q 150 220, 300 200 T 600 150 T 900 120" fill="none" stroke="#8B5CF6" stroke-width="3"></path>
</svg>
<!-- Legend/Axes Mock -->
<div class="absolute bottom-4 left-4 geist-mono text-[10px] text-on-surface-variant flex gap-8">
<span>JAN 23</span>
<span>JUN 23</span>
<span>DEC 23</span>
</div>
</div>
</section>
<!-- Strategic Notes -->
<section class="bg-surface-container-low p-8 rounded-xl">
<div class="flex items-center gap-2 mb-4">
<span class="material-symbols-outlined text-on-surface-variant">psychology</span>
<h2 class="text-lg font-bold tracking-tight">Strategic Notes (Human Translation)</h2>
</div>
<div class="bg-surface-container-lowest rounded-lg p-6 border border-outline-variant/10 min-h-[160px]">
<p class="text-on-surface leading-relaxed text-sm">
                                The current cycle is defined by high liquidity in tier-2 markets. We are observing a significant variance compression in the Alpha Protocol. Recommendation is to maintain current unit sizes but tighten the exit criteria on outlier events. Psychological readiness remains high, though consecutive streaks have historically led to over-leverage risks. Maintain the vault's cold-storage principles.
                            </p>
</div>
</section>
</div>
<!-- Sidebar Checklist & Info -->
<div class="space-y-8">
<!-- The Alpha Protocol Checklist -->
<section class="bg-surface-container-lowest p-8 rounded-xl border border-outline-variant/15 shadow-sm">
<h2 class="text-sm font-bold tracking-widest uppercase text-primary mb-8">The Alpha Protocol</h2>
<ul class="space-y-6">
<li class="flex items-center justify-between group">
<div class="flex items-center gap-4">
<div class="w-6 h-6 rounded bg-primary-container flex items-center justify-center text-primary">
<span class="material-symbols-outlined text-lg" style="font-variation-settings: 'wght' 700;">check</span>
</div>
<span class="text-sm font-semibold text-on-surface">Market Liquidity Check</span>
</div>
</li>
<li class="flex items-center justify-between group">
<div class="flex items-center gap-4">
<div class="w-6 h-6 rounded bg-primary-container flex items-center justify-center text-primary">
<span class="material-symbols-outlined text-lg" style="font-variation-settings: 'wght' 700;">check</span>
</div>
<span class="text-sm font-semibold text-on-surface">Variance Acceptance Protocol</span>
</div>
</li>
<li class="flex items-center justify-between group">
<div class="flex items-center gap-4">
<div class="w-6 h-6 rounded border-2 border-outline-variant/30 flex items-center justify-center text-transparent">
<span class="material-symbols-outlined text-lg">check</span>
</div>
<span class="text-sm font-semibold text-on-surface-variant italic">Psychological Readiness Audit</span>
</div>
<span class="text-[10px] font-bold text-tertiary uppercase">Pending</span>
</li>
<li class="flex items-center justify-between group">
<div class="flex items-center gap-4">
<div class="w-6 h-6 rounded bg-primary-container flex items-center justify-center text-primary">
<span class="material-symbols-outlined text-lg" style="font-variation-settings: 'wght' 700;">check</span>
</div>
<span class="text-sm font-semibold text-on-surface">Unit Size Recalibration</span>
</div>
</li>
</ul>
</section>
<!-- Discipline Shield Card -->
<div class="bg-gradient-to-br from-primary to-primary-dim p-8 rounded-xl text-white shadow-xl relative overflow-hidden">
<div class="absolute -right-8 -bottom-8 opacity-10">
<span class="material-symbols-outlined text-[160px]" style="font-variation-settings: 'FILL' 1;">shield</span>
</div>
<h3 class="text-[10px] font-bold uppercase tracking-[0.2em] mb-6 opacity-80">Protection Level</h3>
<div class="flex items-center gap-4 mb-4">
<span class="material-symbols-outlined text-4xl" style="font-variation-settings: 'FILL' 1;">verified_user</span>
<span class="geist-mono text-4xl font-bold tracking-tighter">MAXIMUM</span>
</div>
<p class="text-xs leading-relaxed opacity-70">
                            Your current Discipline Score of 1,250 DP provides access to the Swiss-tier reporting and liquidity-protected entry modules.
                        </p>
</div>
<!-- Market Context Image -->
<div class="rounded-xl overflow-hidden h-48 border border-outline-variant/15 relative">
<img alt="Cyber Security Visual" class="w-full h-full object-cover" data-alt="high-tech digital security vault interface with glowing circuits and data streams in deep blue and purple tones" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCX8TcvBhGYR_ype2rdQUf-pMyyOuCccPMRQP3BUVozDyxsbyYmEB-raVvU6H8u-Lw6d7ANFi2YSa-9YZaJevT0UcqTM0Yr4t4SnLVnr06B6jouis11FlPKTcVXgf5pdxA3wj88O_3AYaW4Ii2Lz9-Hk3HG5Y52kuuG3IfPIexGpAtrIkeuN1nZjHKaFLyUFqY_FJ-ZxxDFuCMinFlFS0oWZ8fzFsCGli9gSNHJsVEaaVarBYuyEk0HAsy_xsmnqX-2YR07Hpf8tpU"/>
<div class="absolute inset-0 bg-gradient-to-t from-inverse-surface/80 to-transparent flex flex-col justify-end p-6">
<span class="text-[10px] font-bold uppercase tracking-widest text-primary-fixed mb-1">Global Sentiment</span>
<span class="text-white font-bold text-sm tracking-tight">Risk-Off: Stable</span>
</div>
</div>
</div>
</div>
</main>
</div>
<!-- Mobile Navigation Shell -->
<nav class="md:hidden fixed bottom-0 left-0 right-0 bg-[#f6fafe]/95 backdrop-blur-md border-t border-[#26343d]/10 px-6 py-3 flex justify-around items-center z-50">
<a class="flex flex-col items-center gap-1 text-[#8B5CF6]" href="#">
<span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">account_balance</span>
<span class="text-[10px] font-bold uppercase tracking-tighter">Vault</span>
</a>
<a class="flex flex-col items-center gap-1 text-[#52616a]" href="#">
<span class="material-symbols-outlined">history</span>
<span class="text-[10px] font-bold uppercase tracking-tighter">History</span>
</a>
<div class="bg-primary p-3 rounded-full -mt-12 shadow-xl border-4 border-surface shadow-primary/20">
<span class="material-symbols-outlined text-white">add</span>
</div>
<a class="flex flex-col items-center gap-1 text-[#52616a]" href="#">
<span class="material-symbols-outlined">insights</span>
<span class="text-[10px] font-bold uppercase tracking-tighter">Strategy</span>
</a>
<a class="flex flex-col items-center gap-1 text-[#52616a]" href="#">
<span class="material-symbols-outlined">person</span>
<span class="text-[10px] font-bold uppercase tracking-tighter">Profile</span>
</a>
</nav>
</body></html>