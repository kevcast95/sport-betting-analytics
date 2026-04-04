<!DOCTYPE html>

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Elite Progression Path - BetTracker 2.0</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&amp;family=Geist+Mono:wght@400;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
        tailwind.config = {
            darkMode: "class",
            theme: {
                extend: {
                    "colors": {
                        "on-primary-container": "#6029c9",
                        "on-primary-fixed": "#4d00b7",
                        "secondary-container": "#d3e4fe",
                        "outline-variant": "#a4b4be",
                        "inverse-surface": "#0a0f12",
                        "error-container": "#ff8b9a",
                        "on-error-container": "#782232",
                        "error": "#9e3f4e",
                        "on-primary": "#fcf5ff",
                        "inverse-on-surface": "#999da1",
                        "outline": "#6e7d86",
                        "secondary-dim": "#44546a",
                        "surface": "#f6fafe",
                        "on-surface-variant": "#52616a",
                        "surface-variant": "#d5e5ef",
                        "on-tertiary-container": "#4a2500",
                        "surface-dim": "#cadde9",
                        "primary-fixed": "#e9ddff",
                        "surface-bright": "#f6fafe",
                        "on-tertiary-fixed-variant": "#572c00",
                        "primary-container": "#e9ddff",
                        "tertiary-fixed-dim": "#ed871e",
                        "on-secondary-container": "#435368",
                        "on-background": "#26343d",
                        "error-dim": "#4f0116",
                        "surface-container-low": "#eef4fa",
                        "tertiary-dim": "#804300",
                        "on-tertiary-fixed": "#240f00",
                        "tertiary": "#914d00",
                        "surface-container": "#e5eff7",
                        "on-secondary-fixed-variant": "#4d5d73",
                        "tertiary-container": "#fe932c",
                        "background": "#f6fafe",
                        "surface-tint": "#6d3bd7",
                        "tertiary-fixed": "#fe932c",
                        "on-tertiary": "#fff7f4",
                        "secondary-fixed-dim": "#c5d6f0",
                        "secondary-fixed": "#d3e4fe",
                        "primary-fixed-dim": "#ddcdff",
                        "primary": "#6d3bd7",
                        "on-error": "#fff7f7",
                        "secondary": "#506076",
                        "surface-container-lowest": "#ffffff",
                        "surface-container-high": "#ddeaf3",
                        "surface-container-highest": "#d5e5ef",
                        "on-secondary": "#f7f9ff",
                        "on-secondary-fixed": "#314055",
                        "on-surface": "#26343d",
                        "on-primary-fixed-variant": "#6a37d4",
                        "primary-dim": "#612aca",
                        "inverse-primary": "#a078ff"
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
                }
            }
        }
    </script>
<style>
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        }
        body { font-family: 'Inter', sans-serif; }
        .geist-mono { font-family: 'Geist Mono', monospace; }
        .glass-nav { backdrop-filter: blur(20px); }
    </style>
</head>
<body class="bg-surface text-on-surface">
<div class="flex min-h-screen">
<!-- SideNavBar -->
<aside class="hidden md:flex flex-col h-screen w-64 border-r border-[#26343d]/15 bg-[#eef4fa] sticky top-0">
<div class="flex flex-col h-full py-8">
<div class="px-6 mb-10">
<h1 class="text-lg font-black text-[#26343d]">BetTracker 2.0</h1>
<div class="mt-8 flex items-center gap-3">
<div class="w-10 h-10 rounded-full bg-primary-container overflow-hidden">
<img alt="Arquitecto Alpha" class="w-full h-full object-cover" data-alt="professional avatar of a focused architect wearing glasses and a minimalist turtleneck sweater" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCdAfVbVUu6Vgo6rWdsbzxEgoPF0412W8yUz-E7gZj3PFMRTgEkpmSsBVCdTvUxLWJ307Rr0WKtvvTRh_VD_Hxgw2cpKLgeRcGRPdiF_g3_2pAsDWdXh_K-d8TTegAZ5qDnXxf72NCjkNGffGKdPVWDpWmvaquMLVb_MAKN4p6OSjFoqLf5Z_j73CRAMG332x-MVmaO7oncgKxmaS4CPvhDJ6Pq7bUKb1BnBnHagv4JujFhbKEx3ITDV2AGn_0aIdS_2vvc3TGRD-8"/>
</div>
<div>
<p class="font-['Inter'] text-sm tracking-wide uppercase font-medium text-[#26343d]">Arquitecto Alpha</p>
<p class="text-xs text-on-surface-variant">Level: Elite</p>
</div>
</div>
</div>
<nav class="flex-1 px-4 space-y-1">
<a class="flex items-center gap-3 px-4 py-3 text-[#52616a] hover:bg-[#ffffff]/50 transition-all duration-300" href="#">
<span class="material-symbols-outlined" data-icon="account_balance">account_balance</span>
<span class="font-['Inter'] text-sm tracking-wide uppercase font-medium">The Vault</span>
</a>
<a class="flex items-center gap-3 px-4 py-3 text-[#52616a] hover:bg-[#ffffff]/50 transition-all duration-300" href="#">
<span class="material-symbols-outlined" data-icon="history">history</span>
<span class="font-['Inter'] text-sm tracking-wide uppercase font-medium">History</span>
</a>
<a class="flex items-center gap-3 px-4 py-3 text-[#52616a] hover:bg-[#ffffff]/50 transition-all duration-300" href="#">
<span class="material-symbols-outlined" data-icon="insights">insights</span>
<span class="font-['Inter'] text-sm tracking-wide uppercase font-medium">Strategy</span>
</a>
<a class="flex items-center gap-3 px-4 py-3 text-[#8B5CF6] font-bold border-r-2 border-[#8B5CF6] bg-[#ffffff]/50 transition-all duration-300" href="#">
<span class="material-symbols-outlined" data-icon="person">person</span>
<span class="font-['Inter'] text-sm tracking-wide uppercase font-medium">Profile</span>
</a>
</nav>
<div class="px-4 mt-auto">
<button class="w-full py-4 bg-primary text-on-primary rounded-xl font-semibold shadow-lg hover:bg-primary-dim transition-colors flex items-center justify-center gap-2">
<span class="material-symbols-outlined text-sm">add</span>
                        New Analysis
                    </button>
</div>
</div>
</aside>
<main class="flex-1 flex flex-col">
<!-- TopNavBar -->
<header class="bg-[#f6fafe]/80 backdrop-blur-md border-b border-[#26343d]/15 shadow-[0px_20px_40px_rgba(38,52,61,0.06)] z-50 sticky top-0 px-6 py-3 flex justify-between items-center w-full">
<div class="flex items-center gap-4">
<h2 class="text-xl font-bold text-[#26343d]">Elite Progression Path</h2>
</div>
<div class="flex items-center gap-6">
<div class="flex items-center gap-2 px-3 py-1.5 bg-surface-container-lowest rounded-full border border-primary/10">
<span class="material-symbols-outlined text-primary" data-icon="shield" style="font-variation-settings: 'FILL' 1;">shield</span>
<span class="geist-mono font-bold text-[#8B5CF6]">1,250 DP</span>
</div>
<span class="material-symbols-outlined text-on-surface-variant cursor-pointer hover:text-primary transition-colors" data-icon="shield">shield</span>
</div>
</header>
<!-- Content Area -->
<div class="p-8 space-y-12 max-w-7xl mx-auto w-full">
<!-- Profile Status Card (Asymmetric Layout) -->
<section class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
<div class="lg:col-span-8 bg-surface-container-lowest p-10 rounded-xl relative overflow-hidden flex flex-col justify-between">
<div class="relative z-10">
<h3 class="text-on-surface-variant font-label tracking-[0.1em] uppercase text-xs mb-2">Authenticated User</h3>
<h1 class="text-4xl font-headline font-extrabold tracking-tight text-on-surface">Arquitecto Alpha</h1>
<p class="text-primary font-medium mt-2 flex items-center gap-2">
<span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">verified</span>
                                Elite Strategy Consultant
                            </p>
</div>
<div class="mt-12 grid grid-cols-3 gap-6 relative z-10">
<div>
<p class="text-xs text-on-surface-variant uppercase tracking-wider mb-1">Rank</p>
<p class="geist-mono text-xl font-bold">Top 0.8%</p>
</div>
<div>
<p class="text-xs text-on-surface-variant uppercase tracking-wider mb-1">Active Streak</p>
<p class="geist-mono text-xl font-bold">42 Days</p>
</div>
<div>
<p class="text-xs text-on-surface-variant uppercase tracking-wider mb-1">Consistency</p>
<p class="geist-mono text-xl font-bold text-primary">98.4%</p>
</div>
</div>
<!-- Background Decorative Element -->
<div class="absolute right-[-10%] top-[-20%] w-64 h-64 bg-primary/5 rounded-full blur-3xl"></div>
</div>
<!-- Circular Progress Indicator -->
<div class="lg:col-span-4 bg-surface-container-lowest p-10 rounded-xl border border-outline-variant/10 flex flex-col items-center justify-center text-center">
<div class="relative w-48 h-48 mb-6">
<svg class="w-full h-full transform -rotate-90">
<circle class="text-surface-container-high" cx="96" cy="96" fill="transparent" r="88" stroke="currentColor" stroke-width="6"></circle>
<circle class="text-primary-dim" cx="96" cy="96" fill="transparent" r="88" stroke="currentColor" stroke-dasharray="552.92" stroke-dashoffset="138.23" stroke-linecap="round" stroke-width="8"></circle>
</svg>
<div class="absolute inset-0 flex flex-col items-center justify-center">
<span class="geist-mono text-4xl font-bold text-on-surface">75%</span>
<span class="text-[10px] uppercase tracking-widest text-on-surface-variant mt-1">To Apex</span>
</div>
</div>
<p class="text-sm font-medium text-on-surface-variant">Next Milestone: <span class="text-on-surface">Apex Protocol Unlock</span></p>
</div>
</section>
<!-- Personal Stats Row (Bento Style) -->
<section class="grid grid-cols-1 md:grid-cols-3 gap-6">
<div class="bg-surface-container-low p-6 rounded-xl border border-transparent hover:border-primary/20 transition-all">
<p class="text-xs font-label uppercase tracking-widest text-on-surface-variant mb-4">Total DP Earned</p>
<div class="flex items-end justify-between">
<span class="geist-mono text-3xl font-bold">12,450.00</span>
<span class="material-symbols-outlined text-primary" data-icon="account_balance_wallet">account_balance_wallet</span>
</div>
</div>
<div class="bg-surface-container-low p-6 rounded-xl border border-transparent hover:border-primary/20 transition-all">
<p class="text-xs font-label uppercase tracking-widest text-on-surface-variant mb-4">Avg Discipline / Cycle</p>
<div class="flex items-end justify-between">
<span class="geist-mono text-3xl font-bold">412.5</span>
<span class="material-symbols-outlined text-tertiary" data-icon="show_chart">show_chart</span>
</div>
</div>
<div class="bg-surface-container-low p-6 rounded-xl border border-transparent hover:border-primary/20 transition-all">
<p class="text-xs font-label uppercase tracking-widest text-on-surface-variant mb-4">Account Seniority</p>
<div class="flex items-end justify-between">
<span class="geist-mono text-3xl font-bold">730<span class="text-sm font-normal ml-1">DAYS</span></span>
<span class="material-symbols-outlined text-on-surface-variant" data-icon="calendar_today">calendar_today</span>
</div>
</div>
</section>
<!-- Discipline Milestones (Minimalist Badge Grid) -->
<section>
<div class="flex items-baseline justify-between mb-8">
<h3 class="text-2xl font-headline font-bold text-on-surface">Discipline Milestones</h3>
<span class="text-xs font-label uppercase tracking-widest text-on-surface-variant">Historical Archive</span>
</div>
<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
<div class="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/20 flex flex-col items-center text-center group hover:border-primary transition-all">
<div class="w-16 h-16 rounded-full border border-primary-container flex items-center justify-center mb-4 text-primary group-hover:bg-primary-container transition-colors">
<span class="material-symbols-outlined text-3xl" data-icon="verified_user">verified_user</span>
</div>
<h4 class="text-sm font-bold text-on-surface leading-tight mb-1">30-Day Protocol Adherence</h4>
<p class="text-[10px] text-on-surface-variant uppercase tracking-tighter">Achieved: Oct 2023</p>
</div>
<div class="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/20 flex flex-col items-center text-center group hover:border-primary transition-all">
<div class="w-16 h-16 rounded-full border border-primary-container flex items-center justify-center mb-4 text-primary group-hover:bg-primary-container transition-colors">
<span class="material-symbols-outlined text-3xl" data-icon="shield_with_heart">shield_with_heart</span>
</div>
<h4 class="text-sm font-bold text-on-surface leading-tight mb-1">Maximum Drawdown Controlled</h4>
<p class="text-[10px] text-on-surface-variant uppercase tracking-tighter">Achieved: Jan 2024</p>
</div>
<div class="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/20 flex flex-col items-center text-center group hover:border-primary transition-all">
<div class="w-16 h-16 rounded-full border border-primary-container flex items-center justify-center mb-4 text-primary group-hover:bg-primary-container transition-colors">
<span class="material-symbols-outlined text-3xl" data-icon="water_drop">water_drop</span>
</div>
<h4 class="text-sm font-bold text-on-surface leading-tight mb-1">High-Liquidity Master</h4>
<p class="text-[10px] text-on-surface-variant uppercase tracking-tighter">Achieved: Mar 2024</p>
</div>
<div class="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/20 flex flex-col items-center text-center border-dashed">
<div class="w-16 h-16 rounded-full border border-outline-variant/20 flex items-center justify-center mb-4 text-outline-variant">
<span class="material-symbols-outlined text-3xl" data-icon="lock">lock</span>
</div>
<h4 class="text-sm font-bold text-on-surface-variant leading-tight mb-1">Vault Guardian</h4>
<p class="text-[10px] text-on-surface-variant/50 uppercase tracking-tighter">Locked</p>
</div>
</div>
</section>
<!-- Growth Roadmap (Timeline) -->
<section class="bg-surface-container-lowest p-10 rounded-xl border border-outline-variant/10 overflow-hidden relative">
<h3 class="text-2xl font-headline font-bold text-on-surface mb-12">Growth Roadmap</h3>
<div class="relative">
<!-- Horizontal Line -->
<div class="absolute top-8 left-0 w-full h-[2px] bg-surface-container-high"></div>
<div class="grid grid-cols-1 md:grid-cols-4 gap-8 relative z-10">
<!-- Unlocked Item -->
<div class="space-y-4">
<div class="w-16 h-16 rounded-full bg-primary flex items-center justify-center text-on-primary shadow-lg ring-8 ring-surface-container-lowest">
<span class="material-symbols-outlined" data-icon="token" style="font-variation-settings: 'FILL' 1;">token</span>
</div>
<div>
<h5 class="text-sm font-bold text-on-surface">Alpha-9 Access</h5>
<p class="text-xs text-primary font-medium mt-1">Unlocked</p>
<p class="text-xs text-on-surface-variant mt-2">Full algorithmic analysis permissions granted.</p>
</div>
</div>
<!-- Unlocked Item -->
<div class="space-y-4">
<div class="w-16 h-16 rounded-full bg-primary flex items-center justify-center text-on-primary shadow-lg ring-8 ring-surface-container-lowest">
<span class="material-symbols-outlined" data-icon="menu_book" style="font-variation-settings: 'FILL' 1;">menu_book</span>
</div>
<div>
<h5 class="text-sm font-bold text-on-surface">The Strategic Ledger</h5>
<p class="text-xs text-primary font-medium mt-1">Unlocked</p>
<p class="text-xs text-on-surface-variant mt-2">Deep-tier history archiving active.</p>
</div>
</div>
<!-- Next Unlock (Active State) -->
<div class="space-y-4">
<div class="w-16 h-16 rounded-full bg-surface-container-highest border-2 border-primary flex items-center justify-center text-primary ring-8 ring-surface-container-lowest">
<span class="material-symbols-outlined" data-icon="bolt">bolt</span>
</div>
<div>
<h5 class="text-sm font-bold text-on-surface">Sigma-2 Protocol</h5>
<p class="text-xs text-tertiary font-medium mt-1">Unlock at 2,000 DP</p>
<p class="text-xs text-on-surface-variant mt-2">Real-time risk mitigation engine activation.</p>
</div>
</div>
<!-- Locked Item -->
<div class="space-y-4 opacity-40 grayscale">
<div class="w-16 h-16 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant ring-8 ring-surface-container-lowest">
<span class="material-symbols-outlined" data-icon="diamond">diamond</span>
</div>
<div>
<h5 class="text-sm font-bold text-on-surface">Private Equity Portal</h5>
<p class="text-xs text-on-surface-variant font-medium mt-1">Locked</p>
<p class="text-xs text-on-surface-variant mt-2">Direct fund integration and management tools.</p>
</div>
</div>
</div>
</div>
</section>
<!-- Signature Component: Discipline Shield -->
<div class="flex justify-center pt-8">
<div class="bg-surface-container-lowest p-6 rounded-xl shadow-[0px_20px_40px_rgba(38,52,61,0.06)] border border-primary/5 flex items-center gap-6">
<div class="flex items-center gap-3">
<div class="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
<span class="material-symbols-outlined text-primary" data-icon="security" style="font-variation-settings: 'FILL' 1;">security</span>
</div>
<div>
<p class="text-[10px] uppercase tracking-[0.2em] font-label text-on-surface-variant">Protocol Status</p>
<p class="geist-mono font-bold text-lg text-primary">ENFORCED</p>
</div>
</div>
<div class="h-10 w-[1px] bg-outline-variant/30"></div>
<div class="flex items-center gap-3">
<div class="w-12 h-12 bg-tertiary/10 rounded-full flex items-center justify-center">
<span class="material-symbols-outlined text-tertiary" data-icon="shield" style="font-variation-settings: 'FILL' 1;">shield</span>
</div>
<div>
<p class="text-[10px] uppercase tracking-[0.2em] font-label text-on-surface-variant">Discipline Shield</p>
<p class="geist-mono font-bold text-lg">1,250 <span class="text-xs font-normal">pts</span></p>
</div>
</div>
</div>
</div>
</div>
<!-- Footer Spacing -->
<footer class="h-24 md:hidden"></footer>
</main>
</div>
<!-- Mobile Bottom NavBar -->
<nav class="md:hidden fixed bottom-0 left-0 right-0 bg-[#f6fafe]/80 backdrop-blur-md border-t border-[#26343d]/15 flex justify-around items-center py-3 z-50">
<a class="flex flex-col items-center gap-1 text-[#52616a]" href="#">
<span class="material-symbols-outlined" data-icon="account_balance">account_balance</span>
<span class="text-[10px] font-medium">Vault</span>
</a>
<a class="flex flex-col items-center gap-1 text-[#52616a]" href="#">
<span class="material-symbols-outlined" data-icon="history">history</span>
<span class="text-[10px] font-medium">History</span>
</a>
<a class="flex flex-col items-center gap-1 text-[#52616a]" href="#">
<span class="material-symbols-outlined" data-icon="insights">insights</span>
<span class="text-[10px] font-medium">Strategy</span>
</a>
<a class="flex flex-col items-center gap-1 text-[#8B5CF6] font-bold" href="#">
<span class="material-symbols-outlined" data-icon="person">person</span>
<span class="text-[10px] font-medium">Profile</span>
</a>
</nav>
</body></html>