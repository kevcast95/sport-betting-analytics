<!DOCTYPE html>

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Settlement View - BetTracker 2.0</title>
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
                        "surface-dim": "#cadde9",
                        "surface-container-highest": "#d5e5ef",
                        "error-dim": "#4f0116",
                        "on-primary-fixed": "#4d00b7",
                        "on-tertiary-fixed": "#240f00",
                        "primary-fixed-dim": "#ddcdff",
                        "secondary": "#506076",
                        "on-surface-variant": "#52616a",
                        "tertiary-fixed-dim": "#ed871e",
                        "tertiary": "#914d00",
                        "inverse-on-surface": "#999da1",
                        "tertiary-fixed": "#fe932c",
                        "outline": "#6e7d86",
                        "on-secondary-fixed": "#314055",
                        "surface-container-lowest": "#ffffff",
                        "on-tertiary-container": "#4a2500",
                        "on-tertiary": "#fff7f4",
                        "surface-tint": "#6d3bd7",
                        "on-secondary-container": "#435368",
                        "surface-container-high": "#ddeaf3",
                        "secondary-container": "#d3e4fe",
                        "on-secondary": "#f7f9ff",
                        "on-tertiary-fixed-variant": "#572c00",
                        "error": "#9e3f4e",
                        "surface": "#f6fafe",
                        "on-secondary-fixed-variant": "#4d5d73",
                        "on-background": "#26343d",
                        "surface-variant": "#d5e5ef",
                        "on-surface": "#26343d",
                        "on-primary": "#fcf5ff",
                        "on-error": "#fff7f7",
                        "primary": "#6d3bd7",
                        "secondary-dim": "#44546a",
                        "primary-dim": "#612aca",
                        "on-primary-container": "#6029c9",
                        "surface-container-low": "#eef4fa",
                        "secondary-fixed": "#d3e4fe",
                        "background": "#f6fafe",
                        "tertiary-dim": "#804300",
                        "primary-container": "#e9ddff",
                        "primary-fixed": "#e9ddff",
                        "on-error-container": "#782232",
                        "surface-bright": "#f6fafe",
                        "tertiary-container": "#fe932c",
                        "outline-variant": "#a4b4be",
                        "inverse-surface": "#0a0f12",
                        "secondary-fixed-dim": "#c5d6f0",
                        "on-primary-fixed-variant": "#6a37d4",
                        "error-container": "#ff8b9a",
                        "surface-container": "#e5eff7",
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
        .geist-mono { font-family: 'Geist Mono', monospace; }
        .inter-tight { font-family: 'Inter', sans-serif; letter-spacing: -0.02em; }
    </style>
</head>
<body class="bg-surface text-on-surface font-body min-h-screen">
<!-- TopNavBar Shell -->
<header class="bg-[#f6fafe]/80 backdrop-blur-md sticky top-0 z-50 border-b border-[#26343d]/15 flex justify-between items-center w-full px-6 py-4 mx-auto">
<div class="text-xl font-black tracking-tighter text-[#26343d]">BetTracker 2.0</div>
<nav class="hidden md:flex items-center space-x-8">
<a class="text-[#52616a] hover:text-[#8B5CF6] transition-colors duration-200" href="#">Dashboard</a>
<a class="text-[#52616a] hover:text-[#8B5CF6] transition-colors duration-200" href="#">Ledger</a>
<a class="text-[#52616a] hover:text-[#8B5CF6] transition-colors duration-200" href="#">Analytics</a>
<a class="text-[#8B5CF6] border-b-2 border-[#8B5CF6] pb-1" href="#">Audit</a>
</nav>
<div class="flex items-center space-x-4">
<button class="material-symbols-outlined text-[#52616a] scale-95 transition-transform">notifications</button>
<button class="material-symbols-outlined text-[#52616a] scale-95 transition-transform">account_balance_wallet</button>
<img alt="User profile" class="w-8 h-8 rounded-full border border-outline-variant/30" src="https://lh3.googleusercontent.com/aida-public/AB6AXuC5nX7tnWVV6R1-xHnwkIndS9Kqo5zlIs-Od9l96bPcM0VEiVMOn-LsCrhneGQWPtB2RCG6Z4tFqefE05RVxmHdJR6Q5QihSNmsrYq3ZqnFC7YCFlOaiWOw8TfLOPhXW4PMlGEBKb_uXJ7QydKriTbWLHrCmFhScE-IzYfWpbhwQwNThmASVhduz_l7PFfkMIJzEC8G89Zs1L_Dz-cUqiZOfcsKDJX1eKX_gU1Y1T626ebsV_HNVj5g6x589ZHu8m2WBJGtFY-GzZ0"/>
</div>
</header>
<div class="flex max-w-[1600px] mx-auto">
<!-- SideNavBar Shell -->
<aside class="h-screen w-64 hidden lg:flex flex-col border-r border-[#26343d]/10 bg-[#eef4fa] py-8 pl-4 sticky top-[72px]">
<div class="mb-8 pl-2">
<div class="text-lg font-bold text-[#6d3bd7]">The Sentinel</div>
<div class="text-xs font-semibold uppercase tracking-widest text-on-surface-variant inter-tight">Wealth Management</div>
</div>
<nav class="flex-1 space-y-1">
<a class="flex items-center px-4 py-3 text-[#52616a] hover:pl-2 transition-all duration-300" href="#">
<span class="material-symbols-outlined mr-3">dashboard</span>
<span class="text-xs font-semibold uppercase tracking-widest inter-tight">Overview</span>
</a>
<a class="flex items-center px-4 py-3 text-[#52616a] hover:pl-2 transition-all duration-300" href="#">
<span class="material-symbols-outlined mr-3">pending_actions</span>
<span class="text-xs font-semibold uppercase tracking-widest inter-tight">Active Picks</span>
</a>
<a class="flex items-center px-4 py-3 bg-white text-[#8B5CF6] rounded-l-xl border-r-4 border-[#8B5CF6] opacity-80" href="#">
<span class="material-symbols-outlined mr-3">fact_check</span>
<span class="text-xs font-semibold uppercase tracking-widest inter-tight">Settlement</span>
</a>
<a class="flex items-center px-4 py-3 text-[#52616a] hover:pl-2 transition-all duration-300" href="#">
<span class="material-symbols-outlined mr-3">history_edu</span>
<span class="text-xs font-semibold uppercase tracking-widest inter-tight">Audit Log</span>
</a>
<a class="flex items-center px-4 py-3 text-[#52616a] hover:pl-2 transition-all duration-300" href="#">
<span class="material-symbols-outlined mr-3">settings</span>
<span class="text-xs font-semibold uppercase tracking-widest inter-tight">Settings</span>
</a>
</nav>
<div class="mt-auto pt-8 space-y-1">
<a class="flex items-center px-4 py-3 text-[#52616a] hover:pl-2 transition-all duration-300" href="#">
<span class="material-symbols-outlined mr-3">help</span>
<span class="text-xs font-semibold uppercase tracking-widest inter-tight">Support</span>
</a>
<a class="flex items-center px-4 py-3 text-[#52616a] hover:pl-2 transition-all duration-300" href="#">
<span class="material-symbols-outlined mr-3">logout</span>
<span class="text-xs font-semibold uppercase tracking-widest inter-tight">Sign Out</span>
</a>
</div>
</aside>
<!-- Main Content Canvas -->
<main class="flex-1 p-6 lg:p-12 bg-surface">
<!-- Breadcrumbs & Focus Header -->
<div class="mb-12">
<div class="flex items-center text-xs font-semibold uppercase tracking-widest text-on-surface-variant mb-2 inter-tight">
<span>Active Picks</span>
<span class="material-symbols-outlined text-[14px] mx-2">chevron_right</span>
<span class="text-primary">Settlement Terminal</span>
</div>
<h1 class="text-4xl font-black inter-tight text-on-surface">Audit ID: <span class="geist-mono">#TR-9821-X</span></h1>
</div>
<div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
<!-- Left Column: Event Specs & Reasoning (Bento Style) -->
<div class="lg:col-span-7 space-y-6">
<!-- Event Specs Card -->
<div class="bg-surface-container-lowest p-8 rounded-xl border border-outline-variant/15">
<div class="flex justify-between items-start mb-10">
<div>
<p class="text-xs font-semibold uppercase tracking-widest text-on-surface-variant mb-4 inter-tight">Asset Specification</p>
<h2 class="text-3xl font-bold inter-tight mb-2">Team A vs Team B</h2>
<p class="text-on-surface-variant inter-tight">Premier Division • Matchday 24</p>
</div>
<div class="text-right">
<p class="text-xs font-semibold uppercase tracking-widest text-on-surface-variant mb-4 inter-tight">Market</p>
<div class="bg-primary-container text-primary px-4 py-2 rounded-lg font-bold inter-tight">Over 2.5</div>
</div>
</div>
<div class="grid grid-cols-3 gap-6 pt-6 border-t border-outline-variant/10">
<div>
<p class="text-[10px] font-semibold uppercase tracking-widest text-on-surface-variant mb-1">Entry Price</p>
<p class="geist-mono text-xl">1.92</p>
</div>
<div>
<p class="text-[10px] font-semibold uppercase tracking-widest text-on-surface-variant mb-1">Risk Capital</p>
<p class="geist-mono text-xl text-primary font-semibold">$500.00</p>
</div>
<div>
<p class="text-[10px] font-semibold uppercase tracking-widest text-on-surface-variant mb-1">Potential PnL</p>
<p class="geist-mono text-xl text-primary font-semibold">+$460.00</p>
</div>
</div>
</div>
<!-- Human Translation / Reasoning -->
<div class="bg-surface-container-low p-8 rounded-xl">
<div class="flex items-center mb-6">
<span class="material-symbols-outlined text-primary mr-3">psychology</span>
<h3 class="text-lg font-bold inter-tight">Human Translation</h3>
</div>
<div class="space-y-4 text-on-surface-variant leading-relaxed">
<p>This position was initiated based on a high defensive volatility score for Team B. In the last 4 away matches, they conceded an average of 2.1 goals per game. Team A has maintained a consistent offensive output at home.</p>
<p>The suggestion serves as a <span class="text-on-surface font-semibold">variance-neutralizer</span>. We aren't betting on the winner, but rather the statistical inevitability of a structural defensive failure under high pressing conditions.</p>
</div>
</div>
</div>
<!-- Right Column: Settlement Zone -->
<div class="lg:col-span-5 space-y-6">
<!-- The Settlement Card -->
<div class="bg-surface-container-lowest p-8 rounded-xl border border-outline-variant/15 shadow-[0px_20px_40px_rgba(38,52,61,0.06)] sticky top-24">
<div class="flex justify-between items-center mb-8">
<h3 class="text-xl font-bold inter-tight">Settlement Zone</h3>
<div class="bg-primary/10 text-primary px-3 py-1 rounded-full flex items-center space-x-2 border border-primary/20">
<span class="material-symbols-outlined text-[16px]" style="font-variation-settings: 'FILL' 1;">shield</span>
<span class="geist-mono text-xs font-bold tracking-tight">DP REWARD: +25</span>
</div>
</div>
<p class="text-sm text-on-surface-variant mb-8 leading-snug">Confirm the outcome of this position to reconcile your ledger and update your discipline score.</p>
<!-- Action Buttons -->
<div class="space-y-3 mb-10">
<button class="w-full py-4 px-6 rounded-xl bg-gradient-to-r from-primary to-primary-dim text-white font-bold inter-tight flex justify-between items-center group transition-transform active:scale-95">
<span>Profit</span>
<span class="material-symbols-outlined group-hover:translate-x-1 transition-transform">trending_up</span>
</button>
<button class="w-full py-4 px-6 rounded-xl bg-surface-container-high hover:bg-surface-container-highest text-tertiary font-bold inter-tight flex justify-between items-center transition-colors active:scale-95">
<span>Loss</span>
<span class="material-symbols-outlined">trending_down</span>
</button>
<button class="w-full py-4 px-6 rounded-xl bg-surface-container-low hover:bg-surface-container-high text-on-surface-variant font-bold inter-tight flex justify-between items-center transition-colors active:scale-95">
<span>Push / Void</span>
<span class="material-symbols-outlined">restart_alt</span>
</button>
</div>
<!-- Self-Reflection Zone -->
<div class="pt-8 border-t border-outline-variant/15">
<label class="text-xs font-semibold uppercase tracking-widest text-on-surface-variant mb-3 block inter-tight">Post-Match Emotional Status</label>
<textarea class="w-full bg-surface-container-high border-none rounded-xl focus:ring-1 focus:ring-primary p-4 text-sm inter-tight min-h-[120px] placeholder:text-on-surface-variant/40" placeholder="Describe your reaction to the variance... were you disciplined?"></textarea>
<p class="text-[10px] text-on-surface-variant mt-2 italic">* This data point is used to calculate your emotional equilibrium index.</p>
</div>
</div>
</div>
</div>
<!-- Discipline Metric Preview -->
<section class="mt-12 grid grid-cols-1 md:grid-cols-4 gap-6">
<div class="bg-white p-6 rounded-xl border border-outline-variant/10 flex items-center">
<div class="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mr-4">
<span class="material-symbols-outlined text-primary">account_balance</span>
</div>
<div>
<p class="text-[10px] font-semibold uppercase tracking-widest text-on-surface-variant inter-tight">Vault Balance</p>
<p class="geist-mono text-xl font-semibold">$12,450.00</p>
</div>
</div>
<div class="bg-white p-6 rounded-xl border border-outline-variant/10 flex items-center">
<div class="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mr-4">
<span class="material-symbols-outlined text-primary">analytics</span>
</div>
<div>
<p class="text-[10px] font-semibold uppercase tracking-widest text-on-surface-variant inter-tight">Win Velocity</p>
<p class="geist-mono text-xl font-semibold">64.2%</p>
</div>
</div>
<div class="md:col-span-2 bg-[#6d3bd7] p-6 rounded-xl flex items-center justify-between text-white overflow-hidden relative">
<div class="relative z-10">
<p class="text-[10px] font-semibold uppercase tracking-widest opacity-70 inter-tight">The Discipline Shield</p>
<p class="text-3xl font-black inter-tight">Vault Master Level 4</p>
</div>
<div class="relative z-10 text-right">
<p class="geist-mono text-3xl font-bold">2,840 <span class="text-sm opacity-70">DP</span></p>
</div>
<!-- Decorative background glow -->
<div class="absolute top-0 right-0 w-32 h-32 bg-white/10 blur-3xl rounded-full translate-x-16 -translate-y-16"></div>
</div>
</section>
</main>
</div>
<!-- BottomNavBar Shell (Mobile only) -->
<nav class="fixed bottom-0 left-0 w-full z-50 flex lg:hidden justify-around items-center px-4 pb-6 pt-3 bg-[#f6fafe]/90 backdrop-blur-xl border-t border-[#26343d]/5 shadow-[0px_-20px_40px_rgba(38,52,61,0.06)]">
<button class="flex flex-col items-center justify-center text-[#52616a] opacity-60 scale-90 transition-transform duration-150">
<span class="material-symbols-outlined">account_balance</span>
<span class="text-[10px] font-medium uppercase inter-tight tracking-tighter">Vault</span>
</button>
<button class="flex flex-col items-center justify-center text-[#52616a] opacity-60 scale-90 transition-transform duration-150">
<span class="material-symbols-outlined">assignment_turned_in</span>
<span class="text-[10px] font-medium uppercase inter-tight tracking-tighter">Audit</span>
</button>
<button class="flex flex-col items-center justify-center bg-[#8B5CF6]/10 text-[#8B5CF6] rounded-2xl px-6 py-2 scale-90 transition-transform duration-150">
<span class="material-symbols-outlined">gavel</span>
<span class="text-[10px] font-medium uppercase inter-tight tracking-tighter">Settle</span>
</button>
<button class="flex flex-col items-center justify-center text-[#52616a] opacity-60 scale-90 transition-transform duration-150">
<span class="material-symbols-outlined">person</span>
<span class="text-[10px] font-medium uppercase inter-tight tracking-tighter">Profile</span>
</button>
</nav>
</body></html>