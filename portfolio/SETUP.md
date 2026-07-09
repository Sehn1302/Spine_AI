# How to launch your portfolio & sell Spine AI

## Step 1 — Personalise `config.js`

Open `portfolio/config.js` and set:

```js
email: "your.real@email.com",
linkedin: "https://linkedin.com/in/your-profile",
product: {
  price: "€49",           // your price
  buyUrl: "https://...",  // payment link (see Step 2)
  salesEnabled: true,       // flip to true when ready
}
```

## Step 2 — Choose a payment platform (no coding needed)

### Option A: Gumroad (easiest, recommended)

1. Create account at [gumroad.com](https://gumroad.com)
2. **New product** → Digital product
3. Upload Spine AI as a `.zip` (see Step 4)
4. Set price (e.g. €49)
5. Copy product link → paste into `config.js` → `buyUrl`
6. Set `salesEnabled: true`

Gumroad handles payment, tax, and automatic file delivery by email.

### Option B: Stripe Payment Links

1. [stripe.com](https://stripe.com) → Payment Links → Create
2. One-time payment, your price
3. After payment: redirect to a Google Drive / Dropbox download link
4. Paste Stripe link into `buyUrl`

### Option C: Lemon Squeezy

Similar to Gumroad — good for software licenses. [lemonsqueezy.com](https://lemonsqueezy.com)

## Step 3 — Deploy portfolio (free hosting)

### GitHub Pages (recommended)

1. Create repo: `Sehn1302.github.io` (must match your username)
2. Copy everything from `portfolio/` into that repo root
3. GitHub → Settings → Pages → Deploy from `main` branch
4. Live at: **https://sehn1302.github.io**

### Or: Netlify

1. Drag `portfolio/` folder to [netlify.com/drop](https://app.netlify.com/drop)
2. Get instant URL, add custom domain later

## Step 4 — Package Spine AI for sale

Create a zip buyers receive (do **not** include `.venv`, `.git`, or your personal `memory/`):

```
Spine_AI_Release/
├── Install Spine.bat
├── Launch Spine.bat
├── README.md
├── requirements.txt
├── spine/
├── agents/
├── Scripts/
├── installer/
└── memory/knowledge/README.txt
```

Add a `LICENSE.txt` — personal use only, no redistribution.

## Step 5 — Your link everywhere

Use your portfolio URL as the **only** public link:

| Platform | Link |
|----------|------|
| LinkedIn bio | `https://sehn1302.github.io` |
| GitHub profile | same |
| Thesis / resume | same |
| GitHub Spine repo README | "Purchase at [sehn1302.github.io](...)" |

Keep the GitHub **code** public for portfolio credibility, but sell the **packaged installer + support** as the product.

## Step 6 — Optional custom domain

Buy `sehan.dev` or `spine-ai.com` (~€10/year) and point DNS to GitHub Pages or Netlify.

## Pricing suggestions

| Tier | Price | Includes |
|------|-------|----------|
| Personal | €29–49 | Full app, updates, email support |
| Pro | €79–99 | + 1hr setup call |
| Enterprise | Custom | Multi-seat, custom agents |

Start at **€49** — one-time feels fair vs monthly ChatGPT subscriptions.

## Legal minimum

- Add `TERMS.md` to product zip: personal license, no resale
- Gumroad/Stripe handles VAT in EU if configured
- You're selling software license, not SAAS

## Quick test locally

Double-click `portfolio/index.html` in your browser to preview before deploying.
