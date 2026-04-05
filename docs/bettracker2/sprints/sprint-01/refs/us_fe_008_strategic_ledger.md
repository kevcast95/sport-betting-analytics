<!DOCTYPE html>

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>The Strategic Ledger - BetTracker 2.0</title>
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
                        "surface": "#f6fafe",
                        "surface-container-lowest": "#ffffff",
                        "secondary-dim": "#44546a",
                        "on-primary-fixed": "#4d00b7",
                        "primary": "#6d3bd7",
                        "outline-variant": "#a4b4be",
                        "on-secondary-container": "#435368",
                        "surface-container-low": "#eef4fa",
                        "on-secondary-fixed-variant": "#4d5d73",
                        "secondary": "#506076",
                        "on-tertiary-fixed-variant": "#572c00",
                        "on-tertiary": "#fff7f4",
                        "tertiary-fixed-dim": "#ed871e",
                        "inverse-on-surface": "#999da1",
                        "background": "#f6fafe",
                        "outline": "#6e7d86",
                        "surface-container-highest": "#d5e5ef",
                        "on-primary": "#fcf5ff",
                        "surface-tint": "#6d3bd7",
                        "on-tertiary-fixed": "#240f00",
                        "on-secondary": "#f7f9ff",
                        "primary-dim": "#612aca",
                        "tertiary-dim": "#804300",
                        "primary-fixed": "#e9ddff",
                        "tertiary-container": "#fe932c",
                        "secondary-fixed": "#d3e4fe",
                        "surface-variant": "#d5e5ef",
                        "surface-dim": "#cadde9",
                        "on-surface-variant": "#52616a",
                        "tertiary": "#914d00",
                        "primary-fixed-dim": "#ddcdff",
                        "on-background": "#26343d",
                        "error-container": "#ff8b9a",
                        "inverse-primary": "#a078ff",
                        "error-dim": "#4f0116",
                        "tertiary-fixed": "#fe932c",
                        "surface-container": "#e5eff7",
                        "surface-container-high": "#ddeaf3",
                        "on-tertiary-container": "#4a2500",
                        "on-secondary-fixed": "#314055",
                        "primary-container": "#e9ddff",
                        "on-primary-fixed-variant": "#6a37d4",
                        "secondary-fixed-dim": "#c5d6f0",
                        "inverse-surface": "#0a0f12",
                        "on-primary-container": "#6029c9",
                        "surface-bright": "#f6fafe",
                        "secondary-container": "#d3e4fe",
                        "on-surface": "#26343d",
                        "on-error-container": "#782232",
                        "error": "#9e3f4e",
                        "on-error": "#fff7f7"
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
        body { font-family: 'Inter', sans-serif; background-color: #f6fafe; color: #26343d; }
        .mono-text { font-family: 'Geist Mono', monospace; }
        .ghost-border { border: 1px solid rgba(164, 180, 190, 0.15); }
    </style>
</head>
<body class="flex min-h-screen bg-surface selection:bg-primary-fixed selection:text-on-primary-fixed">
<!-- SideNavBar (Authority Source: JSON) -->
<aside class="h-screen w-64 border-r border-[#26343d]/15 bg-[#eef4fa] dark:bg-[#0d151a] flex flex-col py-8 fixed left-0 top-0 hidden md:flex">
<div class="px-6 mb-10">
<h1 class="text-lg font-black text-[#26343d] dark:text-[#eef4fa] font-['Inter']">BetTracker 2.0</h1>
<div class="mt-8 flex items-center gap-3">
<div class="w-10 h-10 rounded-full bg-surface-container-highest overflow-hidden">
<img alt="Arquitecto Alpha" class="w-full h-full object-cover" data-alt="Close up portrait of a professional architect with glasses and a thoughtful expression, high-end corporate photography style" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAWjQyFfSi-q6rjY_b_2SyKtRuc3B2zdXN_fDr1jRx-i_jd1Zh_p06u72U_dO9_Dc5lQ8xtiheuyhLaBwNko_KiCKj-BX11RiEqv0IEimHGT7gXwz6anIi6iE8NrqEHrTqnE7-G1QkRCxAdHMk5P7oxZvUB2vlDnfUK0if4om24eXFpCIZD0mDAZbEYWzZZt4ochxVewLwLw2reqPfe4pOL9ALSGXv9MUth6K828IEBJA3_LEF3iaDBCdFHLWaIYSzFfhD8lA-wGj0"/>
</div>
<div>
<p class="text-[#26343d] font-bold text-sm leading-tight">Arquitecto Alpha</p>
<p class="text-[#52616a] text-[10px] uppercase tracking-widest font-medium">Level: Elite</p>
</div>
</div>
</div>
<nav class="flex-1 space-y-1">
<!-- The Vault -->
<a class="flex items-center px-6 py-3 transition-all duration-300 ease-in-out hover:bg-[#ffffff]/50 text-[#52616a] font-['Inter'] text-sm tracking-wide uppercase font-medium" href="#">
<span class="material-symbols-outlined mr-3 text-lg" data-icon="account_balance">account_balance</span>
                The Vault
            </a>
<!-- History (ACTIVE STATE LOGIC: Exact Match Priority) -->
<a class="flex items-center px-6 py-3 transition-all duration-300 ease-in-out text-[#8B5CF6] font-bold border-r-2 border-[#8B5CF6] bg-[#ffffff]/30 font-['Inter'] text-sm tracking-wide uppercase" href="#">
<span class="material-symbols-outlined mr-3 text-lg" data-icon="history">history</span>
                History
            </a>
<!-- Strategy -->
<a class="flex items-center px-6 py-3 transition-all duration-300 ease-in-out hover:bg-[#ffffff]/50 text-[#52616a] font-['Inter'] text-sm tracking-wide uppercase font-medium" href="#">
<span class="material-symbols-outlined mr-3 text-lg" data-icon="insights">insights</span>
                Strategy
            </a>
<!-- Profile -->
<a class="flex items-center px-6 py-3 transition-all duration-300 ease-in-out hover:bg-[#ffffff]/50 text-[#52616a] font-['Inter'] text-sm tracking-wide uppercase font-medium" href="#">
<span class="material-symbols-outlined mr-3 text-lg" data-icon="person">person</span>
                Profile
            </a>
</nav>
<div class="px-6 mt-auto">
<button class="w-full bg-gradient-to-r from-primary to-primary-dim text-white py-3 rounded-xl font-semibold shadow-[0px_20px_40px_rgba(38,52,61,0.06)] hover:scale-95 transition-transform duration-200">
                New Analysis
            </button>
</div>
</aside>
<!-- Main Content Canvas -->
<main class="flex-1 md:ml-64 min-h-screen">
<!-- TopAppBar (Authority Source: JSON) -->
<header class="bg-[#f6fafe]/80 dark:bg-[#0a0f12]/80 backdrop-blur-md border-b border-[#26343d]/15 docked full-width top-0 z-50 sticky px-6 py-3 flex justify-between items-center w-full shadow-[0px_20px_40px_rgba(38,52,61,0.06)]">
<div class="flex items-center gap-4">
<span class="md:hidden material-symbols-outlined text-on-surface" data-icon="menu">menu</span>
<span class="text-xl font-bold text-[#26343d] dark:text-[#eef4fa] font-['Inter'] tracking-tight">The Strategic Ledger</span>
</div>
<div class="flex items-center gap-4">
<div class="flex items-center bg-surface-container-lowest px-4 py-1.5 rounded-full ghost-border">
<span class="material-symbols-outlined text-primary text-sm mr-2" data-icon="shield" style="font-variation-settings: 'FILL' 1;">shield</span>
<span class="mono-text font-semibold text-on-surface text-sm">1,250 DP</span>
</div>
<span class="material-symbols-outlined text-on-surface-variant cursor-pointer hover:text-primary transition-colors" data-icon="shield">shield</span>
<div class="w-8 h-8 rounded-full overflow-hidden border border-outline-variant/30">
<img alt="Arquitecto Alpha" class="w-full h-full object-cover" data-alt="Profile icon of a digital workspace user in a professional setting" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBrReYGYbC7gUnU6XL_7RUwn0-QZe1DKE6k53V6MkJmYxUMk-xFm9NLJ78kuvt3JpNAOVT-N56JZ54w0aR9ZtrIWKXnPBKHFXVoTh9s3oTMd8ny0WVzbvIxc6ZaO0i-snkMjzIxE2cfiL1vUC7iqQR5wx-K6sPxoOU8xFvFbzObC3o_-IcplwNq0jq2ZbirCvHUnHmUgQHPNt5PJ4Yg8UpE74UG0iCsikETQf09LQNUZ6-cgHrCfJdWNbkOz2soSRzBT97TLhTp6Js"/>
</div>
</div>
</header>
<!-- Canvas Content -->
<div class="p-6 md:p-12 max-w-7xl mx-auto space-y-10">
<!-- Page Hero/Intro -->
<section class="flex flex-col md:flex-row md:items-end justify-between gap-6">
<div>
<h2 class="text-4xl font-extrabold text-on-surface tracking-tight mb-2">The Strategic Ledger</h2>
<p class="text-on-surface-variant font-medium">A chronological record of disciplined execution.</p>
</div>
<!-- Controls Row -->
<div class="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
<div class="relative flex-1 sm:w-64">
<span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-sm" data-icon="search">search</span>
<input class="w-full pl-10 pr-4 py-2.5 bg-surface-container-high rounded-xl border-none focus:ring-1 focus:ring-primary focus:bg-surface-container-lowest transition-all text-sm font-medium" placeholder="Search entries..." type="text"/>
</div>
<div class="relative">
<select class="appearance-none w-full sm:w-48 pl-4 pr-10 py-2.5 bg-surface-container-high rounded-xl border-none focus:ring-1 focus:ring-primary focus:bg-surface-container-lowest transition-all text-sm font-medium">
<option>Filter by Protocol</option>
<option>Alpha-9</option>
<option>Delta-4</option>
<option>Sigma-1</option>
</select>
<span class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-outline pointer-events-none" data-icon="expand_more">expand_more</span>
</div>
</div>
</section>
<!-- Ledger Table Section -->
<section class="bg-surface-container-lowest rounded-xl ghost-border overflow-hidden">
<div class="overflow-x-auto">
<table class="w-full border-collapse">
<thead>
<tr class="bg-surface-container-low text-left">
<th class="px-6 py-4 text-[10px] uppercase tracking-[0.1em] font-bold text-on-surface-variant">Date</th>
<th class="px-6 py-4 text-[10px] uppercase tracking-[0.1em] font-bold text-on-surface-variant">Strategic Protocol</th>
<th class="px-6 py-4 text-[10px] uppercase tracking-[0.1em] font-bold text-on-surface-variant">Outcome</th>
<th class="px-6 py-4 text-[10px] uppercase tracking-[0.1em] font-bold text-on-surface-variant text-center">Discipline Points</th>
<th class="px-6 py-4 text-[10px] uppercase tracking-[0.1em] font-bold text-on-surface-variant text-right">Action</th>
</tr>
</thead>
<tbody class="divide-y divide-surface-container">
<!-- Entry 1 -->
<tr class="hover:bg-surface transition-colors group">
<td class="px-6 py-6 mono-text text-sm font-medium text-on-surface">2023.10.24</td>
<td class="px-6 py-6">
<span class="px-3 py-1 bg-primary-container text-on-primary-container text-xs font-bold rounded-full uppercase tracking-wide">Alpha-9</span>
</td>
<td class="px-6 py-6 mono-text font-bold text-primary">
                                    +14.2% ROI
                                </td>
<td class="px-6 py-6 text-center">
<div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-variant/30 border border-primary/10">
<span class="material-symbols-outlined text-primary text-[16px]" data-icon="shield" style="font-variation-settings: 'FILL' 1;">shield</span>
<span class="mono-text text-sm font-semibold">+45</span>
</div>
</td>
<td class="px-6 py-6 text-right">
<a class="text-xs font-bold text-primary hover:underline underline-offset-4 uppercase tracking-wider" href="#">View Details</a>
</td>
</tr>
<!-- Entry 2 -->
<tr class="hover:bg-surface transition-colors group">
<td class="px-6 py-6 mono-text text-sm font-medium text-on-surface">2023.10.23</td>
<td class="px-6 py-6">
<span class="px-3 py-1 bg-surface-container-highest text-on-secondary-container text-xs font-bold rounded-full uppercase tracking-wide">Delta-4</span>
</td>
<td class="px-6 py-6 mono-text font-bold text-on-surface-variant">
                                    -0.0% PUSH
                                </td>
<td class="px-6 py-6 text-center">
<div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-variant/30 border border-primary/10">
<span class="material-symbols-outlined text-primary text-[16px]" data-icon="shield" style="font-variation-settings: 'FILL' 1;">shield</span>
<span class="mono-text text-sm font-semibold">+12</span>
</div>
</td>
<td class="px-6 py-6 text-right">
<a class="text-xs font-bold text-primary hover:underline underline-offset-4 uppercase tracking-wider" href="#">View Details</a>
</td>
</tr>
<!-- Entry 3 (Loss handled with Amber Warning/Neutral per Design System) -->
<tr class="hover:bg-surface transition-colors group">
<td class="px-6 py-6 mono-text text-sm font-medium text-on-surface">2023.10.22</td>
<td class="px-6 py-6">
<span class="px-3 py-1 bg-primary-container text-on-primary-container text-xs font-bold rounded-full uppercase tracking-wide">Alpha-9</span>
</td>
<td class="px-6 py-6 mono-text font-bold text-tertiary">
                                    -5.0% RECAP
                                </td>
<td class="px-6 py-6 text-center">
<div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-variant/30 border border-primary/10">
<span class="material-symbols-outlined text-primary text-[16px]" data-icon="shield" style="font-variation-settings: 'FILL' 1;">shield</span>
<span class="mono-text text-sm font-semibold">+30</span>
</div>
</td>
<td class="px-6 py-6 text-right">
<a class="text-xs font-bold text-primary hover:underline underline-offset-4 uppercase tracking-wider" href="#">View Details</a>
</td>
</tr>
<!-- Entry 4 -->
<tr class="hover:bg-surface transition-colors group">
<td class="px-6 py-6 mono-text text-sm font-medium text-on-surface">2023.10.21</td>
<td class="px-6 py-6">
<span class="px-3 py-1 bg-secondary-container text-on-secondary-container text-xs font-bold rounded-full uppercase tracking-wide">Sigma-1</span>
</td>
<td class="px-6 py-6 mono-text font-bold text-primary">
                                    +8.4% ROI
                                </td>
<td class="px-6 py-6 text-center">
<div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-variant/30 border border-primary/10">
<span class="material-symbols-outlined text-primary text-[16px]" data-icon="shield" style="font-variation-settings: 'FILL' 1;">shield</span>
<span class="mono-text text-sm font-semibold">+50</span>
</div>
</td>
<td class="px-6 py-6 text-right">
<a class="text-xs font-bold text-primary hover:underline underline-offset-4 uppercase tracking-wider" href="#">View Details</a>
</td>
</tr>
</tbody>
</table>
</div>
<!-- Pagination / Footer of Section -->
<div class="px-6 py-4 bg-surface-container-low flex items-center justify-between">
<p class="text-xs font-medium text-on-surface-variant">Showing 1-4 of 128 Analyses</p>
<div class="flex gap-2">
<button class="p-2 rounded-lg bg-surface-container-lowest ghost-border hover:bg-surface-container transition-colors disabled:opacity-50">
<span class="material-symbols-outlined text-sm" data-icon="chevron_left">chevron_left</span>
</button>
<button class="p-2 rounded-lg bg-surface-container-lowest ghost-border hover:bg-surface-container transition-colors">
<span class="material-symbols-outlined text-sm" data-icon="chevron_right">chevron_right</span>
</button>
</div>
</div>
</section>
<!-- Bottom Asymmetric Stats -->
<section class="grid grid-cols-1 md:grid-cols-3 gap-8">
<div class="md:col-span-2 bg-surface-container-low p-8 rounded-xl flex items-center gap-8">
<div class="w-1/3 aspect-video rounded-lg overflow-hidden ghost-border">
<img alt="Strategy Visual" class="w-full h-full object-cover grayscale opacity-60 hover:grayscale-0 transition-all duration-500" data-alt="Minimalist abstract graph showing consistent upward growth lines on a clean white background with soft lavender accents" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDxRyEgZtoJg7kDklfimBKcGyDih1RkCk-PYl8pcLUaY8doFy5zjEXmL863HFnCJzfEGxBdNznItzv4C92o3KwaMY-3bq7_M1bk8swv1aZs_4l7dzAQAv3ZPrK1X-M3qL2lRezR9QFAm1erOmeBdFn5Ku9z1M-sazlXxkCeKnqpX2K0_Ew4AtSo6GqNExvC4yFotAm0KCttb0hqWeizOaiiiazb_RaT8FHv6O-EqOvbZXnK00CkbF84TWYo4AmobNUPXjSSZUamRxQ"/>
</div>
<div class="flex-1">
<h4 class="text-xs uppercase tracking-widest font-bold text-on-surface-variant mb-2">Protocol Efficiency</h4>
<p class="text-on-surface leading-relaxed text-sm">The Alpha-9 protocol continues to demonstrate a <span class="mono-text font-bold text-primary">68.4%</span> success rate over the last 30 intervals. Discipline remains the primary driver of capital preservation.</p>
</div>
</div>
<div class="bg-gradient-to-br from-surface-container-lowest to-surface-container-low p-8 rounded-xl ghost-border flex flex-col justify-center">
<span class="text-[10px] uppercase tracking-widest font-bold text-outline mb-4">Total Discipline Factor</span>
<div class="flex items-baseline gap-2">
<span class="text-5xl font-black tracking-tight text-on-surface">8.4</span>
<span class="text-sm font-bold text-primary uppercase">Elite</span>
</div>
<div class="w-full h-1.5 bg-surface-container-high rounded-full mt-4 overflow-hidden">
<div class="w-[84%] h-full bg-primary rounded-full"></div>
</div>
</div>
</section>
</div>
</main>
<!-- Mobile Bottom NavBar (Authority Source: Component Shell visibility rule) -->
<nav class="md:hidden fixed bottom-0 left-0 right-0 bg-[#f6fafe]/95 backdrop-blur-lg border-t border-[#26343d]/10 px-4 py-3 flex justify-around items-center z-[100]">
<a class="flex flex-col items-center text-[#52616a]" href="#">
<span class="material-symbols-outlined" data-icon="account_balance">account_balance</span>
<span class="text-[10px] font-bold uppercase mt-1">Vault</span>
</a>
<a class="flex flex-col items-center text-[#8B5CF6]" href="#">
<span class="material-symbols-outlined" data-icon="history" style="font-variation-settings: 'FILL' 1;">history</span>
<span class="text-[10px] font-bold uppercase mt-1">History</span>
</a>
<a class="flex flex-col items-center text-[#52616a]" href="#">
<span class="material-symbols-outlined" data-icon="insights">insights</span>
<span class="text-[10px] font-bold uppercase mt-1">Strategy</span>
</a>
<a class="flex flex-col items-center text-[#52616a]" href="#">
<span class="material-symbols-outlined" data-icon="person">person</span>
<span class="text-[10px] font-bold uppercase mt-1">Profile</span>
</a>
</nav>
</body></html>