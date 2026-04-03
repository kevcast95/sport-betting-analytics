<!DOCTYPE html>

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Capital Management Protocol | Silent Sentinel</title>
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
                        "inverse-primary": "#a078ff",
                        "error-dim": "#4f0116",
                        "tertiary-fixed": "#fe932c",
                        "on-surface-variant": "#52616a",
                        "tertiary": "#914d00",
                        "primary-fixed-dim": "#ddcdff",
                        "on-background": "#26343d",
                        "error-container": "#ff8b9a",
                        "surface-container-high": "#ddeaf3",
                        "surface-container": "#e5eff7",
                        "on-primary-fixed-variant": "#6a37d4",
                        "secondary-fixed-dim": "#c5d6f0",
                        "inverse-surface": "#0a0f12",
                        "on-tertiary-container": "#4a2500",
                        "on-secondary-fixed": "#314055",
                        "primary-container": "#e9ddff",
                        "secondary-container": "#d3e4fe",
                        "on-surface": "#26343d",
                        "on-error-container": "#782232",
                        "error": "#9e3f4e",
                        "on-error": "#fff7f7",
                        "on-primary-container": "#6029c9",
                        "surface-bright": "#f6fafe",
                        "on-primary-fixed": "#4d00b7",
                        "primary": "#6d3bd7",
                        "outline-variant": "#a4b4be",
                        "on-secondary-container": "#435368",
                        "surface": "#f6fafe",
                        "surface-container-lowest": "#ffffff",
                        "secondary-dim": "#44546a",
                        "on-secondary-fixed-variant": "#4d5d73",
                        "secondary": "#506076",
                        "on-tertiary-fixed-variant": "#572c00",
                        "on-tertiary": "#fff7f4",
                        "surface-container-low": "#eef4fa",
                        "outline": "#6e7d86",
                        "surface-container-highest": "#d5e5ef",
                        "on-primary": "#fcf5ff",
                        "surface-tint": "#6d3bd7",
                        "on-tertiary-fixed": "#240f00",
                        "on-secondary": "#f7f9ff",
                        "tertiary-fixed-dim": "#ed871e",
                        "inverse-on-surface": "#999da1",
                        "background": "#f6fafe",
                        "secondary-fixed": "#d3e4fe",
                        "surface-variant": "#d5e5ef",
                        "surface-dim": "#cadde9",
                        "primary-dim": "#612aca",
                        "tertiary-dim": "#804300",
                        "primary-fixed": "#e9ddff",
                        "tertiary-container": "#fe932c"
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
        .emerald-accent { color: #10b981; }
    </style>
</head>
<body class="bg-surface text-on-surface font-body selection:bg-primary-container selection:text-on-primary-container">
<!-- Sidebar Shell -->
<aside class="hidden lg:flex flex-col h-screen w-64 border-r border-inverse-surface/5 bg-surface-container-low py-6 px-4 fixed left-0 top-0 z-40">
<div class="mb-10 px-2">
<h1 class="text-lg font-black text-inverse-surface tracking-tighter">THE VAULT</h1>
<p class="text-[10px] uppercase tracking-widest text-on-surface-variant">Institutional Grade</p>
</div>
<nav class="flex-1 space-y-2">
<a class="flex items-center gap-3 px-3 py-2 bg-white text-primary font-semibold rounded-xl hover:translate-x-1 transition-transform duration-200" href="#">
<span class="material-symbols-outlined" data-icon="dashboard">dashboard</span>
<span class="text-xs uppercase tracking-widest">Dashboard</span>
</a>
<a class="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:bg-white/50 rounded-xl hover:translate-x-1 transition-transform duration-200" href="#">
<span class="material-symbols-outlined" data-icon="monitoring">monitoring</span>
<span class="text-xs uppercase tracking-widest">Analytics</span>
</a>
<a class="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:bg-white/50 rounded-xl hover:translate-x-1 transition-transform duration-200" href="#">
<span class="material-symbols-outlined" data-icon="account_balance_wallet">account_balance_wallet</span>
<span class="text-xs uppercase tracking-widest">Positions</span>
</a>
<a class="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:bg-white/50 rounded-xl hover:translate-x-1 transition-transform duration-200" href="#">
<span class="material-symbols-outlined" data-icon="receipt_long">receipt_long</span>
<span class="text-xs uppercase tracking-widest">History</span>
</a>
<a class="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:bg-white/50 rounded-xl hover:translate-x-1 transition-transform duration-200" href="#">
<span class="material-symbols-outlined" data-icon="settings">settings</span>
<span class="text-xs uppercase tracking-widest">Settings</span>
</a>
</nav>
<div class="mt-auto pt-6 space-y-1">
<button class="w-full bg-gradient-to-br from-primary to-primary-dim text-white text-sm font-medium py-3 rounded-xl mb-4 shadow-sm">
                New Strategy
            </button>
<a class="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:bg-white/50 rounded-xl" href="#">
<span class="material-symbols-outlined text-sm" data-icon="help_outline">help_outline</span>
<span class="text-xs uppercase tracking-widest">Support</span>
</a>
<a class="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:bg-white/50 rounded-xl" href="#">
<span class="material-symbols-outlined text-sm" data-icon="logout">logout</span>
<span class="text-xs uppercase tracking-widest">Sign Out</span>
</a>
</div>
</aside>
<!-- Top Navigation -->
<header class="sticky top-0 z-30 flex justify-between items-center w-full px-8 h-16 bg-surface/80 backdrop-blur-md border-b border-inverse-surface/5 lg:pl-72">
<div class="flex items-center gap-8">
<span class="text-xl font-bold tracking-tighter text-inverse-surface">Silent Sentinel</span>
<nav class="hidden md:flex items-center gap-6">
<a class="text-on-surface-variant hover:text-inverse-surface text-sm font-medium tracking-tight" href="#">Portfolio</a>
<a class="text-on-surface-variant hover:text-inverse-surface text-sm font-medium tracking-tight" href="#">Strategy</a>
<a class="text-on-surface-variant hover:text-inverse-surface text-sm font-medium tracking-tight" href="#">Risk</a>
<a class="text-on-surface-variant hover:text-inverse-surface text-sm font-medium tracking-tight" href="#">Ledger</a>
</nav>
</div>
<div class="flex items-center gap-6">
<span class="geist-mono text-sm font-bold emerald-accent">Total Equity: $1,248,502.00</span>
<div class="flex items-center gap-3">
<button class="p-2 rounded-full hover:bg-surface-container-low transition-colors">
<span class="material-symbols-outlined text-on-surface-variant" data-icon="security">security</span>
</button>
<button class="p-2 rounded-full hover:bg-surface-container-low transition-colors">
<span class="material-symbols-outlined text-on-surface-variant" data-icon="notifications">notifications</span>
</button>
<div class="h-8 w-8 rounded-full bg-surface-container-highest overflow-hidden">
<img alt="User profile" class="h-full w-full object-cover" data-alt="Professional portrait of an executive trader in a corporate setting with soft neutral background lighting" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCnNprOrqMFDSZabuSjC2Ol1Ma8RQ4huwvOOkVED9npjA0Tyte5J1UlOZcVXCUdnb00grK20wR-tTFblsAEtxCoRh3qUiI2cgKiqqhwFyaxMtYxbPMW-HXM_8LKk2BodIe_o-JVmnRsrCsU3fKuAkfG2n45vxyY8wMKw5SwSyPTV6YX9mB9TluNz-rD7w1-W6NytEhwq8WpIzOvuMBlKRH5LuAJbvn1wyjpSJJI9paX8hoatr2YTW8bBnmg6cfpmsGTqS-iek9pnQE"/>
</div>
</div>
</div>
</header>
<!-- Main Content Canvas (Blurred Background Content) -->
<main class="lg:pl-64 min-h-screen p-8 bg-surface">
<div class="max-w-6xl mx-auto space-y-12 opacity-40 select-none pointer-events-none">
<!-- Asymmetric Bento Grid Mockup -->
<div class="grid grid-cols-12 gap-6">
<div class="col-span-8 p-10 bg-surface-container-lowest rounded-3xl shadow-sm">
<h2 class="text-3xl font-bold tracking-tight mb-8">Performance Architecture</h2>
<div class="h-64 bg-surface-container-low rounded-2xl flex items-end p-6 gap-4">
<div class="w-full bg-primary/10 h-32 rounded-lg"></div>
<div class="w-full bg-primary/20 h-48 rounded-lg"></div>
<div class="w-full bg-primary/30 h-40 rounded-lg"></div>
<div class="w-full bg-primary/40 h-56 rounded-lg"></div>
<div class="w-full bg-primary/10 h-32 rounded-lg"></div>
<div class="w-full bg-primary/60 h-64 rounded-lg"></div>
</div>
</div>
<div class="col-span-4 space-y-6">
<div class="p-8 bg-primary rounded-3xl text-on-primary">
<p class="text-xs uppercase tracking-widest opacity-80 mb-2">Discipline Score</p>
<p class="geist-mono text-5xl font-bold">98.4</p>
</div>
<div class="p-8 bg-surface-container-lowest rounded-3xl shadow-sm border border-outline-variant/10">
<p class="text-xs uppercase tracking-widest text-on-surface-variant mb-2">Active Risk</p>
<p class="geist-mono text-3xl font-bold">0.42%</p>
</div>
</div>
</div>
</div>
</main>
<!-- THE MODAL OVERLAY (Treasury Modal) -->
<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
<!-- Backdrop -->
<div class="absolute inset-0 bg-inverse-surface/40 backdrop-blur-sm"></div>
<!-- Modal Container: Zurich Calm Aesthetic -->
<div class="relative w-full max-w-2xl bg-surface-bright rounded-[2rem] shadow-2xl overflow-hidden border border-white/20">
<!-- Modal Header: Institutional -->
<div class="p-10 border-b border-surface-container flex justify-between items-start">
<div>
<h2 class="text-2xl font-extrabold tracking-tight text-inverse-surface">Capital Management Protocol</h2>
<p class="text-sm text-on-surface-variant mt-1">Authorized access to central vault configuration and bankroll units.</p>
</div>
<div class="bg-surface-container-low p-2 rounded-xl">
<span class="material-symbols-outlined text-primary" data-icon="lock" style="font-variation-settings: 'FILL' 1;">lock</span>
</div>
</div>
<div class="p-10 space-y-10">
<!-- Section 1: Update Real Bankroll -->
<section>
<div class="flex justify-between items-end mb-4">
<label class="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Update Real Bankroll</label>
<span class="text-[10px] text-on-surface-variant geist-mono opacity-60">ID: TRX-992-SENTINEL</span>
</div>
<div class="relative group">
<div class="absolute left-6 top-1/2 -translate-y-1/2 geist-mono text-on-surface-variant font-bold">$</div>
<input class="w-full bg-surface-container h-16 pl-12 pr-6 rounded-2xl border-none focus:ring-2 focus:ring-primary/20 text-xl geist-mono font-bold text-inverse-surface transition-all" type="text" value="1,248,502.00"/>
<div class="absolute right-4 top-1/2 -translate-y-1/2 bg-white px-3 py-1 rounded-lg text-[10px] font-bold text-primary shadow-sm">VALIDATED</div>
</div>
</section>
<!-- Section 2: Register Transaction (Asymmetric Layout) -->
<section>
<label class="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4 block">Register Withdrawal/Deposit</label>
<div class="grid grid-cols-2 gap-4">
<button class="flex flex-col items-start p-6 bg-surface-container-low rounded-2xl border-2 border-transparent hover:border-primary/20 transition-all text-left">
<span class="material-symbols-outlined text-primary mb-3" data-icon="south_west">south_west</span>
<span class="text-sm font-bold text-inverse-surface">New Deposit</span>
<span class="text-[10px] text-on-surface-variant uppercase tracking-tighter">Inbound Capital Flow</span>
</button>
<button class="flex flex-col items-start p-6 bg-surface-container-low rounded-2xl border-2 border-transparent hover:border-primary/20 transition-all text-left">
<span class="material-symbols-outlined text-tertiary mb-3" data-icon="north_east">north_east</span>
<span class="text-sm font-bold text-inverse-surface">Withdrawal</span>
<span class="text-[10px] text-on-surface-variant uppercase tracking-tighter">Outbound Distribution</span>
</button>
</div>
</section>
<!-- Section 3: Stake Unit Configuration (The Ledger Style) -->
<section class="p-8 bg-surface-container-lowest rounded-3xl border border-surface-container-high">
<div class="flex items-center justify-between mb-6">
<div class="flex items-center gap-3">
<div class="h-10 w-10 bg-primary/10 rounded-xl flex items-center justify-center">
<span class="material-symbols-outlined text-primary text-sm" data-icon="shield" style="font-variation-settings: 'FILL' 1;">shield</span>
</div>
<div>
<h3 class="text-sm font-bold text-inverse-surface">Stake Unit Configuration</h3>
<p class="text-[10px] text-on-surface-variant uppercase tracking-widest">Base Risk Calibration</p>
</div>
</div>
<div class="text-right">
<span class="geist-mono text-2xl font-bold emerald-accent">1.00%</span>
</div>
</div>
<div class="space-y-4">
<div class="flex justify-between items-center py-3 border-b border-surface-container-low">
<span class="text-xs text-on-surface-variant">Definition</span>
<span class="text-xs font-medium text-inverse-surface">1 Unit = 1% of Bankroll</span>
</div>
<div class="flex justify-between items-center py-3">
<span class="text-xs text-on-surface-variant">Unit Value</span>
<span class="geist-mono text-sm font-bold emerald-accent">$12,485.02</span>
</div>
</div>
<!-- Range Slider Custom Styled -->
<div class="mt-6">
<input class="w-full h-1.5 bg-surface-container-high rounded-lg appearance-none cursor-pointer accent-primary" type="range"/>
<div class="flex justify-between mt-2">
<span class="geist-mono text-[9px] text-on-surface-variant">0.25%</span>
<span class="geist-mono text-[9px] text-on-surface-variant">2.50%</span>
<span class="geist-mono text-[9px] text-on-surface-variant">5.00%</span>
</div>
</div>
</section>
</div>
<!-- Footer Actions -->
<div class="px-10 pb-10 flex gap-4">
<button class="flex-1 py-4 bg-surface-container-highest text-inverse-surface text-sm font-bold rounded-2xl hover:bg-surface-container-high transition-colors">
                    Discard Changes
                </button>
<button class="flex-[2] py-4 bg-gradient-to-r from-primary to-primary-dim text-white text-sm font-bold rounded-2xl shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all">
                    Commit Protocol Changes
                </button>
</div>
</div>
</div>
<!-- Bottom Navigation (Mobile Only) -->
<nav class="lg:hidden fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-4 pb-6 pt-3 bg-white/90 backdrop-blur-xl rounded-t-3xl border-t border-inverse-surface/5">
<a class="flex flex-col items-center justify-center text-on-surface-variant" href="#">
<span class="material-symbols-outlined" data-icon="home">home</span>
<span class="font-medium text-[10px] uppercase tracking-wider mt-1">Home</span>
</a>
<a class="flex flex-col items-center justify-center bg-primary/10 text-primary rounded-xl px-3 py-1" href="#">
<span class="material-symbols-outlined" data-icon="account_balance_wallet">account_balance_wallet</span>
<span class="font-medium text-[10px] uppercase tracking-wider mt-1">Positions</span>
</a>
<a class="flex flex-col items-center justify-center text-on-surface-variant" href="#">
<span class="material-symbols-outlined" data-icon="database">database</span>
<span class="font-medium text-[10px] uppercase tracking-wider mt-1">Ledger</span>
</a>
<a class="flex flex-col items-center justify-center text-on-surface-variant" href="#">
<span class="material-symbols-outlined" data-icon="menu">menu</span>
<span class="font-medium text-[10px] uppercase tracking-wider mt-1">Menu</span>
</a>
</nav>
</body></html>