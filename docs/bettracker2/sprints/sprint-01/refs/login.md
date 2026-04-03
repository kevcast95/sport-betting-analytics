<!DOCTYPE html>

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>BetTracker 2.0 | Access Sentinel Protocol</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&amp;family=Geist+Mono:wght@400;500&amp;display=swap" rel="stylesheet"/>
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
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        }
        .vault-gradient {
            background: radial-gradient(circle at top left, #f6fafe 0%, #ddeaf3 100%);
        }
        .glass-container {
            backdrop-filter: blur(24px);
            background: rgba(255, 255, 255, 0.75);
            border: 1px solid rgba(164, 180, 190, 0.2);
        }
    </style>
</head>
<body class="bg-background text-on-background font-body min-h-screen flex flex-col vault-gradient overflow-hidden">
<!-- Top Navigation (Shell suppressed as per Transactional Rule, but using header elements for Branding) -->
<header class="fixed top-0 w-full z-50 px-8 py-6">
<div class="max-w-7xl mx-auto flex justify-center md:justify-start">
<span class="text-xl font-bold tracking-tighter text-on-background">BetTracker 2.0</span>
</div>
</header>
<!-- Main Content Canvas -->
<main class="flex-grow flex items-center justify-center p-6 relative">
<!-- Abstract Decorative Background Element -->
<div class="absolute inset-0 pointer-events-none overflow-hidden">
<div class="absolute -top-[10%] -right-[5%] w-[40rem] h-[40rem] bg-primary/5 rounded-full blur-[120px]"></div>
<div class="absolute -bottom-[10%] -left-[5%] w-[35rem] h-[35rem] bg-secondary/5 rounded-full blur-[100px]"></div>
</div>
<div class="w-full max-w-md z-10">
<!-- Central Glassmorphism Container -->
<div class="glass-container rounded-xl p-10 shadow-[0px_20px_40px_rgba(38,52,61,0.06)] border border-outline-variant/15">
<div class="text-center mb-10">
<div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary-container mb-6">
<span class="material-symbols-outlined text-primary text-2xl">lock</span>
</div>
<h1 class="text-2xl font-bold tracking-tight text-on-background mb-2">Enter the Discipline Vault</h1>
<p class="text-on-surface-variant text-sm tracking-wide">AUTHENTICATION REQUIRED</p>
</div>
<form class="space-y-6">
<div class="space-y-1.5">
<label class="text-[0.70rem] uppercase tracking-[0.1em] font-semibold text-on-surface-variant px-1" for="email">Institutional Email</label>
<input class="w-full bg-surface-container-high/50 border-0 rounded-xl px-4 py-3.5 focus:ring-1 focus:ring-primary focus:bg-surface-container-lowest transition-all text-sm outline-none" id="email" name="email" placeholder="operator@vault.digital" type="email"/>
</div>
<div class="space-y-1.5">
<div class="flex justify-between items-center px-1">
<label class="text-[0.70rem] uppercase tracking-[0.1em] font-semibold text-on-surface-variant" for="password">Security Protocol</label>
<a class="font-mono text-[0.65rem] text-primary hover:text-primary-dim transition-colors" href="#">Forgot Password?</a>
</div>
<input class="w-full bg-surface-container-high/50 border-0 rounded-xl px-4 py-3.5 focus:ring-1 focus:ring-primary focus:bg-surface-container-lowest transition-all text-sm outline-none" id="password" name="password" placeholder="••••••••••••" type="password"/>
</div>
<button class="w-full bg-gradient-to-r from-primary to-primary-dim text-on-primary font-semibold py-4 rounded-xl shadow-lg shadow-primary/20 hover:opacity-90 active:scale-[0.98] transition-all text-sm tracking-tight" type="submit">
                        Access Sentinel Protocol
                    </button>
</form>
<div class="relative my-8">
<div class="absolute inset-0 flex items-center">
<div class="w-full border-t border-outline-variant/20"></div>
</div>
<div class="relative flex justify-center text-[0.65rem] uppercase tracking-widest">
<span class="bg-[#fcfcfd] px-4 text-on-surface-variant">External Verification</span>
</div>
</div>
<button class="w-full bg-surface-container-lowest border border-outline-variant/30 text-on-surface font-medium py-3.5 rounded-xl flex items-center justify-center gap-3 hover:bg-surface-container-low transition-colors text-sm active:scale-[0.98]">
<svg class="w-5 h-5" viewbox="0 0 24 24">
<path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"></path>
<path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"></path>
<path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"></path>
<path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"></path>
</svg>
                    Continue with Google
                </button>
<div class="mt-10 text-center">
<p class="text-sm text-on-surface-variant">
                        New Operator? 
                        <a class="text-primary font-bold ml-1 hover:underline underline-offset-4 transition-all" href="#">Create Account</a>
</p>
</div>
</div>
<!-- Contextual Branding Image (Decorative) -->
<div class="mt-12 flex justify-center opacity-40">
<div class="h-1 w-24 bg-gradient-to-r from-transparent via-primary/50 to-transparent"></div>
</div>
</div>
</main>
<!-- Footer - Shell Component Logic -->
<footer class="w-full py-8">
<div class="flex flex-col md:flex-row justify-between items-center px-8 w-full max-w-7xl mx-auto space-y-4 md:space-y-0">
<p class="font-['Inter'] text-[0.75rem] uppercase tracking-[0.05em] text-[#52616a] dark:text-[#94a3b8] opacity-80">
                © 2024 BetTracker 2.0. Secure Digital Vault Technology.
            </p>
<div class="flex gap-6">
<a class="font-['Inter'] text-[0.75rem] uppercase tracking-[0.05em] text-[#52616a] dark:text-[#94a3b8] opacity-80 hover:opacity-100 transition-opacity hover:underline decoration-[#8B5CF6]" href="#">Privacy</a>
<a class="font-['Inter'] text-[0.75rem] uppercase tracking-[0.05em] text-[#52616a] dark:text-[#94a3b8] opacity-80 hover:opacity-100 transition-opacity hover:underline decoration-[#8B5CF6]" href="#">Terms</a>
<a class="font-['Inter'] text-[0.75rem] uppercase tracking-[0.05em] text-[#52616a] dark:text-[#94a3b8] opacity-80 hover:opacity-100 transition-opacity hover:underline decoration-[#8B5CF6]" href="#">Security</a>
</div>
</div>
</footer>
<!-- Decorative Corner Image -->
<div class="fixed bottom-0 right-0 w-64 h-64 -mb-12 -mr-12 opacity-10 pointer-events-none">
<img class="w-full h-full object-cover rounded-full" data-alt="abstract close-up of a high-tech security server with glowing circuit patterns and cold blue and lavender lights" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDpUzEukAWg0EusjgVlV6enI1fle1lUHG52gynQfOzyL3MHzS55k0nBLA4mXUn0ZAIRXUY-mwpDmkhReNcbawHt-u6dM2jiSXgp_TVXBcw1-ZSwq8nGcpCkYZ7NLhpI6SxuBel3p0yp-STx6UuywddXp7kfcEhVdrs77dSaZcVQ-0ylM18khpi2w2jol6iRFHWdsnyMpSQ_8VBV59Iw6dl66HvEy1d6xGbeMLXpx4UmtGlPgilXUz-BMujqqH4rt5W9SxMknTiTkFI"/>
</div>
</body></html>