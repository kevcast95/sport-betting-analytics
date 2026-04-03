<!DOCTYPE html>

<html class="light" lang="en"><head>
<!--
  Nota de traduccion (punto 7 de `04_IDENTIDAD_VISUAL_UI.md`):
  Este ref viene con texto original en ingles. Al adaptarlo a React, todo el copy visible en UI debe quedar en espanol.
-->
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&amp;family=Geist+Mono:wght@400;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
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
        body { -webkit-font-smoothing: antialiased; }
    </style>
</head>
<body class="bg-surface text-on-background font-body selection:bg-primary-container selection:text-on-primary-container">
<!-- Top Navigation (Shell suppressed for transactional focus, but using style guide for branding) -->
<header class="sticky top-0 z-50 flex justify-between items-center w-full px-8 h-16 bg-[#f6fafe]/80 backdrop-blur-md border-b border-[#0a0f12]/5 shadow-sm">
<div class="text-xl font-bold tracking-tighter text-[#0a0f12]">
            Silent Sentinel
        </div>
<div class="flex items-center gap-6">
<span class="geist-mono text-sm font-bold tracking-normal text-on-surface-variant">VOL: 4.2.1-δ</span>
<div class="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center overflow-hidden border border-outline-variant/10">
<img alt="User profile" class="w-full h-full object-cover" data-alt="close-up minimalist black and white portrait of a stoic person in a high-end architectural setting" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAptOAEvtCD_SYXg3G2v0aSG0gF_q7v3v1ABbpDpZDiVAyDkdPtykgfVWW5EV2RpWWCiP4c2Ax07193rfqFOraplWDa58U-iD10TQDVJvsuTiiia4jI6Q3XobWRKyD-DH6bYh3oB-ALzQOTmWTLhsIcncB4GL8onFfQYSFj2spC5UVZZS2ys8qA7TAbTSxCYFOW13eFt3auVlRVU0VwixORARpdLM675YyFIdotsaC-Yg4D7MfcanuipUe-gsKFtlmhlrGL3CFT9JY"/>
</div>
</div>
</header>
<main class="min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center py-20 px-6">
<!-- Background Aesthetic Element -->
<div class="fixed inset-0 pointer-events-none overflow-hidden -z-10">
<div class="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[120px]"></div>
<div class="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] bg-secondary/5 rounded-full blur-[140px]"></div>
</div>
<section class="max-w-3xl w-full">
<!-- Hero Title Section -->
<div class="text-center mb-16">
<div class="inline-flex items-center gap-2 px-3 py-1 bg-surface-container-low rounded-full mb-6">
<span class="material-symbols-outlined text-primary text-sm" style="font-variation-settings: 'FILL' 1;">security</span>
<span class="text-[10px] uppercase tracking-[0.2em] font-bold text-on-surface-variant">Institutional Protocol</span>
</div>
<h1 class="text-4xl md:text-5xl font-extrabold tracking-tight text-inverse-surface mb-4 leading-tight">
                    The Contract of Discipline
                </h1>
<p class="text-lg text-on-surface-variant max-w-xl mx-auto font-light leading-relaxed">
                    Transparency is the Foundation of Profit. By proceeding, you align your strategy with the vault's core mechanics.
                </p>
</div>
<!-- The Main "Document" Container -->
<div class="bg-surface-container-lowest border border-outline-variant/10 rounded-[2rem] p-8 md:p-12 shadow-[0px_20px_40px_rgba(38,52,61,0.04)] relative overflow-hidden">
<!-- Signature Aesthetic Accent -->
<div class="absolute top-0 right-0 w-32 h-32 opacity-[0.03] pointer-events-none">
<span class="material-symbols-outlined text-[8rem]">verified_user</span>
</div>
<div class="space-y-12">
<!-- Section: Philosophy -->
<div>
<h3 class="text-[10px] uppercase tracking-widest font-black text-outline mb-6 flex items-center gap-2">
<span class="w-8 h-[1px] bg-outline-variant/30"></span>
                            I. Core Axioms
                        </h3>
<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
<div class="p-6 rounded-xl bg-surface-container-low/50 border border-transparent hover:border-primary/10 transition-colors">
<p class="geist-mono text-sm font-bold text-primary mb-2">AXIOM_01</p>
<p class="text-on-surface leading-snug">Discipline &gt; Luck. I acknowledge that the model operates on statistical probability, not fortune.</p>
</div>
<div class="p-6 rounded-xl bg-surface-container-low/50 border border-transparent hover:border-primary/10 transition-colors">
<p class="geist-mono text-sm font-bold text-primary mb-2">AXIOM_02</p>
<p class="text-on-surface leading-snug">Transparency is the Foundation of Profit. Omissions in reporting lead to structural failure.</p>
</div>
</div>
</div>
<!-- Section: Compliance Checkboxes -->
<div class="space-y-4">
<h3 class="text-[10px] uppercase tracking-widest font-black text-outline mb-6 flex items-center gap-2">
<span class="w-8 h-[1px] bg-outline-variant/30"></span>
                            II. Engagement Protocols
                        </h3>
<!-- Checkbox 1 -->
<label class="group flex items-start gap-4 p-5 rounded-2xl cursor-pointer hover:bg-surface-container-low transition-all border border-transparent hover:border-outline-variant/10">
<div class="mt-1">
<input class="w-5 h-5 rounded border-outline-variant text-primary focus:ring-primary/20 bg-surface" type="checkbox"/>
</div>
<div class="flex-1">
<p class="font-semibold text-on-surface group-hover:text-primary transition-colors">Absolute Ledger Accuracy</p>
<p class="text-sm text-on-surface-variant mt-1 leading-relaxed">I commit to reporting all entry points, closing prices, and slippage exactly as they occur, without exception or delay.</p>
</div>
</label>
<!-- Checkbox 2 -->
<label class="group flex items-start gap-4 p-5 rounded-2xl cursor-pointer hover:bg-surface-container-low transition-all border border-transparent hover:border-outline-variant/10">
<div class="mt-1">
<input class="w-5 h-5 rounded border-outline-variant text-primary focus:ring-primary/20 bg-surface" type="checkbox"/>
</div>
<div class="flex-1">
<p class="font-semibold text-on-surface group-hover:text-primary transition-colors">Strict Adherence to Suggested Stakes</p>
<p class="text-sm text-on-surface-variant mt-1 leading-relaxed">I will not exceed the recommended stake size calculated by the Sentinel Vault, recognizing that over-exposure is the primary catalyst for ruin.</p>
</div>
</label>
<!-- Checkbox 3 -->
<label class="group flex items-start gap-4 p-5 rounded-2xl cursor-pointer hover:bg-surface-container-low transition-all border border-transparent hover:border-outline-variant/10">
<div class="mt-1">
<input class="w-5 h-5 rounded border-outline-variant text-primary focus:ring-primary/20 bg-surface" type="checkbox"/>
</div>
<div class="flex-1">
<p class="font-semibold text-on-surface group-hover:text-primary transition-colors">Emotional Equilibrium</p>
<p class="text-sm text-on-surface-variant mt-1 leading-relaxed">I accept that a series of losses is a mathematical certainty. I will remain compliant with the protocol through drawdowns.</p>
</div>
</label>
</div>
<!-- Final Action Section -->
<div class="pt-8 border-t border-outline-variant/10 flex flex-col md:flex-row items-center justify-between gap-8">
<div class="flex items-center gap-4">
<div class="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
<span class="material-symbols-outlined text-primary" data-icon="verified">verified</span>
</div>
<div>
<p class="geist-mono text-xs font-bold text-on-surface-variant">AUTHENTICATION_TOKEN</p>
<p class="geist-mono text-sm text-on-surface">SS-VAULT-772-K9</p>
</div>
</div>
<button class="w-full md:w-auto px-10 py-4 bg-gradient-to-r from-primary to-primary-dim text-white font-bold rounded-xl shadow-lg shadow-primary/20 hover:translate-y-[-2px] transition-all active:scale-95 flex items-center justify-center gap-3 group">
                            Commit to the Protocol
                            <span class="material-symbols-outlined text-sm group-hover:translate-x-1 transition-transform" data-icon="arrow_forward">arrow_forward</span>
</button>
</div>
</div>
</div>
<!-- Footer Compliance Metadata -->
<div class="mt-12 text-center">
<p class="text-[10px] text-outline font-medium uppercase tracking-[0.3em] mb-4">
                    The Silent Sentinel • Vault Compliance Division • Zurich
                </p>
<div class="flex justify-center gap-6">
<a class="text-xs text-on-surface-variant hover:text-primary underline decoration-outline-variant/30 underline-offset-4" href="#">Privacy Framework</a>
<a class="text-xs text-on-surface-variant hover:text-primary underline decoration-outline-variant/30 underline-offset-4" href="#">Audit Logs</a>
<a class="text-xs text-on-surface-variant hover:text-primary underline decoration-outline-variant/30 underline-offset-4" href="#">System Integrity</a>
</div>
</div>
</section>
</main>
<!-- Bottom Navigation (Mobile Only - Suppressed for focus as per task logic, but structure maintained for shell consistency) -->
<!-- The user is in a focused journey (Contract signing), so we suppress the global nav shell as per the "Semantic Shell Mandate" -->
</body></html>