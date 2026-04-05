<!DOCTYPE html>

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>After-Action Review | BetTracker 2.0</title>
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
          },
        },
      }
    </script>
<style>
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        }
        .geist-mono { font-family: 'Geist Mono', monospace; }
        .bg-zurich-gradient {
            background: linear-gradient(135deg, #f6fafe 0%, #eef4fa 100%);
        }
        .glass-panel {
            backdrop-filter: blur(20px);
            background: rgba(255, 255, 255, 0.8);
        }
    </style>
</head>
<body class="bg-surface font-body text-on-surface selection:bg-primary-container">
<!-- TopNavBar (Shared Component) -->
<header class="bg-[#f6fafe]/80 backdrop-blur-md sticky top-0 z-50 border-b border-[#26343d]/15 flex justify-between items-center w-full px-6 py-4 mx-auto">
<div class="text-xl font-black tracking-tighter text-[#26343d]">BetTracker 2.0</div>
<nav class="hidden md:flex items-center space-x-8">
<a class="text-[#52616a] hover:text-[#8B5CF6] transition-colors duration-200" href="#">Dashboard</a>
<a class="text-[#52616a] hover:text-[#8B5CF6] transition-colors duration-200" href="#">Ledger</a>
<a class="text-[#52616a] hover:text-[#8B5CF6] transition-colors duration-200 text-[#8B5CF6] border-b-2 border-[#8B5CF6] pb-1" href="#">Analytics</a>
<a class="text-[#52616a] hover:text-[#8B5CF6] transition-colors duration-200" href="#">Audit</a>
</nav>
<div class="flex items-center space-x-4">
<button class="material-symbols-outlined text-on-surface-variant scale-95 transition-transform" data-icon="notifications">notifications</button>
<button class="material-symbols-outlined text-on-surface-variant scale-95 transition-transform" data-icon="account_balance_wallet">account_balance_wallet</button>
<img alt="User profile" class="w-8 h-8 rounded-full border border-outline-variant/30" data-alt="Minimalist professional headshot of a business analyst in a clean corporate style with neutral lighting" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBOzmaDqTg6nql0q8Rr3oGw1ONGRIa_wwZsJv1PEE3KoMJmb3pWY0Iv1d9g3zUJJzBpaiKretJuEHw4Y8Si9E_aYTtPG_NtuHkAKGr-_OmgwVqdxGdhezHno-AEzO51hBFAZmozqgHo-sBOps0VZzsMY1KSQYmzn7umoFCP-3ChcmBNhrBiZJ6b84Kcq-GUxzuwsRD0of1HNDlAJG53Pbf2Omtu_c_8q6v7erx_965D9k8fAlNCtvm4x_R9i9LPDnjcwNO5VtLSpsI"/>
</div>
</header>
<main class="min-h-screen pt-12 pb-24 px-6 md:px-12 max-w-7xl mx-auto flex flex-col items-center">
<!-- Header Section -->
<div class="w-full mb-16 text-center">
<p class="text-xs font-semibold uppercase tracking-[0.2em] text-on-surface-variant mb-2">Final Review</p>
<h1 class="text-4xl md:text-5xl font-extrabold tracking-tight text-on-surface leading-none">After-Action Review</h1>
<p class="mt-4 text-on-surface-variant font-medium">Session: OCT 24, 2023 • Station 04</p>
</div>
<div class="w-full grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
<!-- Left Column: Primary Metrics -->
<div class="lg:col-span-7 space-y-8">
<!-- Bento Grid Metrics -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
<!-- ROI Metric -->
<div class="surface-container-low bg-[#eef4fa] rounded-xl p-8 flex flex-col justify-between aspect-square md:aspect-auto">
<div class="flex justify-between items-start">
<span class="text-xs font-semibold uppercase tracking-widest text-on-surface-variant">Today's ROI</span>
<span class="material-symbols-outlined text-primary" data-icon="trending_up">trending_up</span>
</div>
<div class="mt-8">
<div class="geist-mono text-5xl font-semibold tracking-tighter text-on-surface">+14.2%</div>
<div class="h-1.5 w-full bg-surface-container-highest rounded-full mt-4 overflow-hidden">
<div class="h-full bg-primary w-[72%]"></div>
</div>
</div>
</div>
<!-- P/L Metric -->
<div class="surface-container-low bg-[#eef4fa] rounded-xl p-8 flex flex-col justify-between">
<div class="flex justify-between items-start">
<span class="text-xs font-semibold uppercase tracking-widest text-on-surface-variant">Net Profit/Loss</span>
<span class="material-symbols-outlined text-primary" data-icon="account_balance">account_balance</span>
</div>
<div class="mt-8">
<div class="geist-mono text-5xl font-semibold tracking-tighter text-primary">+$3,420.00</div>
<p class="text-on-surface-variant text-sm mt-2">Adjusted for commission</p>
</div>
</div>
</div>
<!-- Discipline Score Section -->
<div class="bg-surface-container-lowest border border-outline-variant/15 rounded-xl p-8 flex items-center justify-between shadow-sm">
<div class="flex items-center space-x-6">
<!-- Discipline Shield -->
<div class="w-20 h-20 bg-primary-container flex items-center justify-center rounded-full shadow-[inset_0px_0px_20px_rgba(109,59,215,0.05)]">
<span class="material-symbols-outlined text-primary text-4xl" data-icon="shield" style="font-variation-settings: 'FILL' 1;">shield</span>
</div>
<div>
<h3 class="text-sm font-semibold uppercase tracking-widest text-on-surface-variant">Discipline Score of the Day</h3>
<div class="geist-mono text-4xl font-bold text-on-surface">94 / 100</div>
</div>
</div>
<div class="hidden md:block">
<span class="px-4 py-2 bg-on-primary-container/10 text-on-primary-container text-xs font-bold rounded-full uppercase tracking-tighter">Top 5% Performance</span>
</div>
</div>
<!-- Audit History / Recent Transactions (Minimalist) -->
<div class="bg-surface-container-low/50 rounded-xl p-8">
<h3 class="text-xs font-semibold uppercase tracking-widest text-on-surface-variant mb-6">Recent Ledger Entries</h3>
<div class="space-y-4">
<div class="flex items-center justify-between py-3">
<div class="flex items-center space-x-4">
<span class="w-2 h-2 rounded-full bg-primary"></span>
<span class="text-sm font-medium">Vault Allocation Transfer</span>
</div>
<span class="geist-mono text-sm">+$1,200.00</span>
</div>
<div class="flex items-center justify-between py-3">
<div class="flex items-center space-x-4">
<span class="w-2 h-2 rounded-full bg-primary"></span>
<span class="text-sm font-medium">Settled Audit Entry #0294</span>
</div>
<span class="geist-mono text-sm">+$2,220.00</span>
</div>
<div class="flex items-center justify-between py-3 opacity-40">
<div class="flex items-center space-x-4">
<span class="w-2 h-2 rounded-full bg-on-surface-variant"></span>
<span class="text-sm font-medium">Brokerage Fee Accrual</span>
</div>
<span class="geist-mono text-sm">-$0.00</span>
</div>
</div>
</div>
</div>
<!-- Right Column: Finalization Actions -->
<div class="lg:col-span-5 flex flex-col space-y-8">
<!-- Cash Reconciliation Card -->
<div class="bg-inverse-surface text-on-primary rounded-xl p-8 shadow-xl">
<div class="flex items-center space-x-3 mb-8">
<span class="material-symbols-outlined text-primary-fixed" data-icon="fact_check">fact_check</span>
<h2 class="text-lg font-bold tracking-tight">Reconciliation</h2>
</div>
<div class="space-y-6">
<div>
<label class="block text-xs font-semibold uppercase tracking-[0.15em] text-surface-variant mb-3" for="bankroll">Verify Current Bankroll Balance</label>
<div class="relative group">
<div class="absolute left-6 top-1/2 -translate-y-1/2 geist-mono text-2xl text-outline-variant">$</div>
<input class="w-full bg-on-background/5 border-0 rounded-xl py-6 pl-12 pr-6 text-3xl geist-mono font-semibold focus:ring-2 focus:ring-primary-fixed-dim transition-all text-white placeholder-on-surface-variant/40" id="bankroll" type="text" value="45,920.00"/>
</div>
</div>
<div class="bg-on-background/10 rounded-lg p-6 space-y-4">
<div class="flex justify-between text-sm">
<span class="text-surface-variant">Projected Balance</span>
<span class="geist-mono font-medium">$45,920.00</span>
</div>
<div class="flex justify-between text-sm border-t border-white/5 pt-4">
<span class="text-surface-variant">Status</span>
<span class="text-primary-fixed flex items-center space-x-1">
<span class="material-symbols-outlined text-sm" data-icon="check_circle" style="font-variation-settings: 'FILL' 1;">check_circle</span>
<span class="font-bold">Perfect Match</span>
</span>
</div>
</div>
</div>
</div>
<!-- Discipline Note / Reflections -->
<div class="bg-surface-container-low rounded-xl p-8 flex-grow">
<label class="block text-xs font-semibold uppercase tracking-[0.15em] text-on-surface-variant mb-3">Professional Reflection</label>
<textarea class="w-full bg-surface-container-lowest border-0 rounded-xl p-6 text-sm min-h-[160px] focus:ring-1 focus:ring-primary transition-all resize-none" placeholder="Enter session notes or discipline observations..."></textarea>
</div>
<!-- Finalize Button -->
<button class="w-full py-8 px-6 bg-gradient-to-r from-primary to-primary-dim text-white rounded-xl font-bold text-lg tracking-tight hover:shadow-lg transition-all active:scale-[0.98] flex items-center justify-center space-x-3 group">
<span>Close Station &amp; Finalize Day</span>
<span class="material-symbols-outlined transition-transform group-hover:translate-x-1" data-icon="arrow_forward">arrow_forward</span>
</button>
<p class="text-center text-[10px] uppercase tracking-widest text-on-surface-variant/60 font-medium">
                    This action is final and will lock the ledger for today.
                </p>
</div>
</div>
</main>
<!-- BottomNavBar (Shared Component - Mobile Only) -->
<nav class="fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-4 pb-6 pt-3 bg-[#f6fafe]/90 backdrop-blur-xl lg:hidden border-t border-[#26343d]/5 shadow-[0px_-20px_40px_rgba(38,52,61,0.06)] rounded-t-3xl">
<div class="flex flex-col items-center justify-center text-[#52616a] opacity-60 scale-90 transition-transform duration-150">
<span class="material-symbols-outlined" data-icon="account_balance">account_balance</span>
<span class="text-[10px] font-medium uppercase Inter tracking-tighter">Vault</span>
</div>
<div class="flex flex-col items-center justify-center text-[#52616a] opacity-60 scale-90 transition-transform duration-150">
<span class="material-symbols-outlined" data-icon="assignment_turned_in">assignment_turned_in</span>
<span class="text-[10px] font-medium uppercase Inter tracking-tighter">Audit</span>
</div>
<div class="flex flex-col items-center justify-center bg-[#8B5CF6]/10 text-[#8B5CF6] rounded-2xl px-6 py-2 scale-90 transition-transform duration-150">
<span class="material-symbols-outlined" data-icon="gavel">gavel</span>
<span class="text-[10px] font-medium uppercase Inter tracking-tighter">Settle</span>
</div>
<div class="flex flex-col items-center justify-center text-[#52616a] opacity-60 scale-90 transition-transform duration-150">
<span class="material-symbols-outlined" data-icon="person">person</span>
<span class="text-[10px] font-medium uppercase Inter tracking-tighter">Profile</span>
</div>
</nav>
<!-- Background Decoration -->
<div class="fixed top-0 right-0 -z-10 w-1/3 h-full bg-gradient-to-l from-primary/5 to-transparent blur-3xl pointer-events-none"></div>
<div class="fixed bottom-0 left-0 -z-10 w-1/4 h-1/2 bg-gradient-to-tr from-surface-container-high to-transparent blur-2xl pointer-events-none"></div>
</body></html>