<!DOCTYPE html>

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>BetTracker 2.0 - Begin Your Elite Progression</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&amp;family=Geist+Mono:wght@400;500;600&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
      tailwind.config = {
        darkMode: "class",
        theme: {
          extend: {
            "colors": {
                    "error-container": "#ff8b9a",
                    "on-tertiary-fixed-variant": "#572c00",
                    "on-surface-variant": "#52616a",
                    "on-primary-fixed-variant": "#6a37d4",
                    "background": "#f6fafe",
                    "on-primary-fixed": "#4d00b7",
                    "surface-tint": "#6d3bd7",
                    "primary-dim": "#612aca",
                    "tertiary-fixed": "#fe932c",
                    "outline-variant": "#a4b4be",
                    "on-tertiary-container": "#4a2500",
                    "on-error": "#fff7f7",
                    "on-secondary-fixed-variant": "#4d5d73",
                    "on-secondary-container": "#435368",
                    "surface-container": "#e5eff7",
                    "inverse-surface": "#0a0f12",
                    "surface-container-high": "#ddeaf3",
                    "on-background": "#26343d",
                    "surface-container-low": "#eef4fa",
                    "on-tertiary": "#fff7f4",
                    "secondary-fixed-dim": "#c5d6f0",
                    "on-surface": "#26343d",
                    "tertiary-dim": "#804300",
                    "secondary-container": "#d3e4fe",
                    "error": "#9e3f4e",
                    "on-tertiary-fixed": "#240f00",
                    "inverse-primary": "#a078ff",
                    "on-secondary-fixed": "#314055",
                    "tertiary-container": "#fe932c",
                    "primary-fixed-dim": "#ddcdff",
                    "secondary-dim": "#44546a",
                    "inverse-on-surface": "#999da1",
                    "secondary-fixed": "#d3e4fe",
                    "on-secondary": "#f7f9ff",
                    "on-primary": "#fcf5ff",
                    "primary-fixed": "#e9ddff",
                    "primary-container": "#e9ddff",
                    "tertiary-fixed-dim": "#ed871e",
                    "secondary": "#506076",
                    "primary": "#6d3bd7",
                    "error-dim": "#4f0116",
                    "surface-container-lowest": "#ffffff",
                    "on-primary-container": "#6029c9",
                    "surface-container-highest": "#d5e5ef",
                    "outline": "#6e7d86",
                    "surface-variant": "#d5e5ef",
                    "surface-bright": "#f6fafe",
                    "surface-dim": "#cadde9",
                    "on-error-container": "#782232",
                    "tertiary": "#914d00",
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
        body { font-family: 'Inter', sans-serif; }
        .geist-mono { font-family: 'Geist Mono', monospace; }
        .glass-panel {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
        }
    </style>
</head>
<body class="bg-background text-on-background min-h-screen flex flex-col items-center">
<!-- TopNavBar -->
<nav class="fixed top-0 w-full z-50 bg-[#f6fafe]/80 dark:bg-[#0a0f12]/80 backdrop-blur-xl">
<div class="flex justify-between items-center px-8 py-4 w-full max-w-7xl mx-auto">
<div class="text-xl font-bold tracking-tighter text-[#26343d] dark:text-[#f6fafe] font-['Inter']">
                BetTracker 2.0
            </div>
<div class="flex gap-6 items-center">
<span class="material-symbols-outlined text-[#52616a] dark:text-[#94a3b8] cursor-pointer hover:bg-[#eef4fa] dark:hover:bg-[#1e293b] transition-colors p-2 rounded-full">lock</span>
<span class="material-symbols-outlined text-[#52616a] dark:text-[#94a3b8] cursor-pointer hover:bg-[#eef4fa] dark:hover:bg-[#1e293b] transition-colors p-2 rounded-full">help_outline</span>
</div>
</div>
</nav>
<!-- Main Registration Container -->
<main class="flex-grow flex items-center justify-center w-full px-4 pt-20 pb-12 relative overflow-hidden">
<!-- Abstract Background Element -->
<div class="absolute inset-0 z-0 pointer-events-none overflow-hidden">
<div class="absolute -top-[10%] -left-[5%] w-[40%] h-[60%] rounded-full bg-primary/5 blur-[120px]"></div>
<div class="absolute -bottom-[10%] -right-[5%] w-[40%] h-[60%] rounded-full bg-primary-dim/5 blur-[120px]"></div>
</div>
<div class="w-full max-w-lg z-10">
<div class="glass-panel border border-outline-variant/15 p-10 md:p-12 rounded-[2rem] shadow-[0px_20px_40px_rgba(38,52,61,0.06)]">
<!-- Header Section -->
<header class="mb-10 space-y-3">
<div class="inline-flex items-center gap-2 px-3 py-1 bg-primary/10 rounded-full mb-2">
<span class="material-symbols-outlined text-[1rem] text-primary" style="font-variation-settings: 'FILL' 1;">shield</span>
<span class="text-[0.65rem] font-bold tracking-[0.1em] uppercase text-on-primary-container">Secure Vault Access</span>
</div>
<h1 class="text-3xl font-extrabold tracking-tight text-on-surface">Begin Your Elite Progression</h1>
<p class="text-on-surface-variant text-sm leading-relaxed">System registration for professional bankroll management and disciplined risk assessment.</p>
</header>
<!-- Registration Form -->
<form class="space-y-6">
<!-- Operator Name -->
<div class="space-y-2">
<label class="text-[0.7rem] font-bold uppercase tracking-[0.05em] text-on-surface-variant ml-1">Operator Name</label>
<div class="relative">
<input class="w-full bg-surface-container-high border-none rounded-xl px-5 py-4 text-on-surface focus:ring-1 focus:ring-primary focus:bg-surface-container-lowest transition-all placeholder:text-outline/50" placeholder="Full Legal Name" type="text"/>
</div>
</div>
<!-- Email -->
<div class="space-y-2">
<label class="text-[0.7rem] font-bold uppercase tracking-[0.05em] text-on-surface-variant ml-1">Secure Email Address</label>
<div class="relative">
<input class="w-full bg-surface-container-high border-none rounded-xl px-5 py-4 text-on-surface focus:ring-1 focus:ring-primary focus:bg-surface-container-lowest transition-all placeholder:text-outline/50" placeholder="name@vault.com" type="email"/>
</div>
</div>
<!-- Password Grid -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
<div class="space-y-2">
<label class="text-[0.7rem] font-bold uppercase tracking-[0.05em] text-on-surface-variant ml-1">Password</label>
<input class="w-full bg-surface-container-high border-none rounded-xl px-5 py-4 text-on-surface focus:ring-1 focus:ring-primary focus:bg-surface-container-lowest transition-all placeholder:text-outline/50" placeholder="••••••••" type="password"/>
</div>
<div class="space-y-2">
<label class="text-[0.7rem] font-bold uppercase tracking-[0.05em] text-on-surface-variant ml-1">Confirm Password</label>
<input class="w-full bg-surface-container-high border-none rounded-xl px-5 py-4 text-on-surface focus:ring-1 focus:ring-primary focus:bg-surface-container-lowest transition-all placeholder:text-outline/50" placeholder="••••••••" type="password"/>
</div>
</div>
<!-- Disclaimer -->
<div class="flex items-start gap-3 pt-2">
<div class="mt-1">
<input class="w-5 h-5 rounded-md border-outline-variant/30 text-primary focus:ring-primary focus:ring-offset-0 bg-surface-container-high" id="protocol" type="checkbox"/>
</div>
<label class="text-xs text-on-surface-variant leading-relaxed select-none cursor-pointer" for="protocol">
                            I accept the <span class="text-on-surface font-semibold underline decoration-primary/30">Strict Adherence Protocol</span>. I understand that all analytical data is processed through secure digital vault technology.
                        </label>
</div>
<!-- CTA Button -->
<div class="pt-4">
<button class="w-full py-4 bg-gradient-to-r from-primary to-primary-dim text-on-primary font-bold rounded-xl shadow-[0px_10px_20px_rgba(109,59,215,0.2)] hover:opacity-95 transition-all active:scale-[0.98]" type="submit">
                            Initialize Risk Profile
                        </button>
</div>
</form>
<!-- Footer Switch -->
<footer class="mt-10 pt-8 border-t border-outline-variant/10 text-center">
<p class="text-sm text-on-surface-variant">
                        Already an Operator? 
                        <a class="text-primary font-bold hover:underline ml-1" href="#">Login</a>
</p>
</footer>
</div>
<!-- Discipline Badge (Signature Component) -->
<div class="mt-8 flex justify-center">
<div class="inline-flex items-center gap-3 px-6 py-3 bg-surface-container-lowest border border-outline-variant/15 rounded-full shadow-sm">
<div class="w-2 h-2 rounded-full bg-tertiary shadow-[0_0_8px_rgba(145,77,0,0.4)]"></div>
<span class="text-[0.7rem] font-bold tracking-[0.1em] uppercase text-on-surface-variant">System Status: Awaiting Authentication</span>
<span class="geist-mono text-xs font-semibold text-primary">LVL 0.00</span>
</div>
</div>
</div>
</main>
<!-- Footer Component -->
<footer class="w-full py-8 bg-transparent">
<div class="flex flex-col md:flex-row justify-between items-center px-8 w-full max-w-7xl mx-auto">
<p class="font-['Inter'] text-[0.75rem] uppercase tracking-[0.05em] text-[#52616a] dark:text-[#94a3b8]">
                © 2024 BetTracker 2.0. Secure Digital Vault Technology.
            </p>
<div class="flex gap-8 mt-4 md:mt-0">
<a class="font-['Inter'] text-[0.75rem] uppercase tracking-[0.05em] text-[#52616a] dark:text-[#94a3b8] hover:underline decoration-[#8B5CF6] transition-opacity opacity-80 hover:opacity-100" href="#">Privacy</a>
<a class="font-['Inter'] text-[0.75rem] uppercase tracking-[0.05em] text-[#52616a] dark:text-[#94a3b8] hover:underline decoration-[#8B5CF6] transition-opacity opacity-80 hover:opacity-100" href="#">Terms</a>
<a class="font-['Inter'] text-[0.75rem] uppercase tracking-[0.05em] text-[#52616a] dark:text-[#94a3b8] hover:underline decoration-[#8B5CF6] transition-opacity opacity-80 hover:opacity-100" href="#">Security</a>
</div>
</div>
</footer>
</body></html>