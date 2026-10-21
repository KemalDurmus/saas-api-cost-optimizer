# SaaS/API Cost Optimizer — product facts

Source of truth for sales and marketing. Only claims listed under "What it does" may be made.

## What it does
- Web tool: the customer uploads or pastes a CSV of their SaaS / API / cloud costs (one charge per line).
- Shows total spend, spend and share by vendor, and spend by month (when there is a date column).
- Findings, each from a concrete rule:
  - Possible double charges: same vendor, same day, same amount more than once (the only finding with an exact money figure).
  - Spikes: a single charge at least 2.5× that vendor's usual (median) charge.
  - Fast-growing vendors: more than 25% growth from the previous month to the latest month.
  - Unit-price increases: cost per unit up more than 15% (needs a usage/quantity column).
  - Fixed subscriptions: vendors billed the same amount every month, with their yearly total.
  - Concentration: one vendor at 40% or more of spend.
- Latest-month spend and a simple annualized run-rate (latest month × 12).
- Accepts English or Turkish column names (Service/Vendor, Date, Usage/Quantity, Cost/Amount); comma, semicolon or tab separated; amounts like $1,250.00, 1.250,50 or (12.00); common date formats. Up to 20,000 lines.
- Currency label: USD, EUR, GBP or TRY (no conversion).
- Results appear immediately after uploading (typical files are analyzed in seconds).
- Privacy: the file is analyzed in memory and never stored. No account needed.
- Interface language: English.

## What it does NOT do (never claim these)
- Does not connect to Stripe, AWS, OpenAI, banks or any vendor; no API integrations, no automatic import, no ongoing monitoring, alerts or dashboard.
- Does not read AWS "wide" Cost Explorer reports where months are columns, PDFs or invoices; only one-charge-per-line CSVs.
- Does not find unused seats or licenses (it has no usage-per-user data); it only lists fixed subscriptions to review.
- Does not cancel, negotiate or change anything; it only reports.
- No AI or machine learning; it uses transparent rules.
- No saved history, reports or user accounts; nothing is stored.
- No measured savings, customers or case studies exist; do not promise savings amounts or percentages.

## Pricing and offer
- Using the tool is currently free; there is no paid plan or payment page yet.
- "I want to buy" on the site only collects an email; payment details are sent manually afterwards.
- Do not quote prices, trials, pilots, audits or quotas.

## Good fit
Small SaaS and AI startups paying several usage-based vendors (LLM APIs, cloud, messaging) who can export their costs to CSV and want a quick check for double charges, spikes and creeping costs.
