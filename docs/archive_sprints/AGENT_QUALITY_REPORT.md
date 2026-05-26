# Agent Quality Report

Generated from real local code and live API runs on 2026-05-25. Secrets were not printed. Raw artifacts are saved in `/tmp/pulselens_agent_quality/`.

## Executive Verdict

- **Agent 1:** ALMOST READY. Step-Back is useful and structurally valid, but it is not a perfect paper-faithful abstraction and query coverage is too sparse for an 8 company × 7 signal matrix.
- **Agent 2:** WORKS BUT NEEDS QUALITY HARDENING. BrightData is configured and live collection works. Output contains many usable pages, but SERP discovery frequently returns broad/off-target pages and dynamic page scraping failed for the tested Azure query.
- **Agent 3:** NOT READY FOR PIPELINE. Standalone extraction/validation/SAFE work on a small live sample, but LangGraph still has placeholder Agent 3 nodes, RASG is JSON-schema prompting rather than true tool use, and SAFE fails open on LLM errors.

Key blockers before trusting Agent 1 → 3 end to end:
1. Increase Agent 1 coverage and validate company × high-weight signal coverage, not only global signal minimums.
2. Add post-SERP relevance filtering in Agent 2 before scraping and route `dynamic_pages`/protected domains with the correct BrightData zone/tool.
3. Wire Agent 3 and validation nodes into LangGraph; current `graph.py` placeholders return `{}`.

## PART 1 — Agent 1: Step-Back Paper Faithfulness

### 1a. Right Type Of Abstraction

Paper definition from `papers/TAKE_A_STEP_BACK.pdf`: a step-back question is **"a derived question from the original question at a higher level of abstraction"**. The paper also describes abstraction as deriving **"high-level concepts and first principles"** and then reasoning from them.

Implementation: [agent1_query_planner.py](backend/app/pipeline/agent1_query_planner.py:115) asks:

> What would the web evidence landscape look like for the market under different conditions — accelerating, decelerating, or under structural stress?

Verdict: **PARTIAL / ADAPTED**. This is not exactly the paper’s “what is the high-level concept/principle behind the question?” pattern. It is an evidence-pattern abstraction. For PulseLens, that adaptation is reasonable because the downstream task is query planning, not answer reasoning. But it should be documented as “Step-Back-inspired evidence abstraction,” not pure Step-Back Prompting.

### 1b. Is The Output Used Correctly?

Yes. Agent 1 performs abstraction first, validates it, serializes it, and injects it into query generation:

- Step-Back LLM call: [agent1_query_planner.py](backend/app/pipeline/agent1_query_planner.py:287)
- Step-Back validation: [agent1_query_planner.py](backend/app/pipeline/agent1_query_planner.py:292)
- Serialized `abstract_principles`: [agent1_query_planner.py](backend/app/pipeline/agent1_query_planner.py:293)
- Injected into Multi-HyDE prompt: [agent1_query_planner.py](backend/app/pipeline/agent1_query_planner.py:316) and prompt slot [agent1_query_planner.py](backend/app/pipeline/agent1_query_planner.py:163)

Verdict: **FAITHFUL ENOUGH**. The paper’s reasoning step is “grounded on” the abstraction. Here, query generation is grounded on `abstract_principles`.

### 1c. Few-Shot Examples

The paper uses few-shot exemplar demonstrations. Our prompt includes one structured example for `hiring_momentum` at [agent1_query_planner.py](backend/app/pipeline/agent1_query_planner.py:137).

Verdict: **PASS WITH CAVEAT**. One example is consistent with the paper’s ablation finding that one demonstration can be enough. But the single example only covers hiring. For this project, examples for `investor_signal` and `pricing_pressure` would likely improve the highest-value signals.

### 1d. Live Step-Back Output

Real run output: well-formed JSON, exactly 7 signal keys, all required fields present. It is more useful than generic filler: it names source classes, positive/negative patterns, and search terms. Weakness: it is generic at the market/signal level and does not name company-specific product lines enough.

Full live Step-Back JSON:
```json
{
  "investor_signal": {
    "positive_evidence": "Positive revisions to earnings guidance, particularly upward for AI hardware segments. Numerous analyst upgrades and price target increases citing AI growth. Increased institutional ownership (13F filings) in AI-centric companies. Companies announcing significant share buybacks or increased dividends, signaling strong financial health. Positive commentary on AI-related revenue and backlog during earnings calls.",
    "negative_evidence": "Downward revisions to earnings guidance, especially for AI hardware/semiconductor divisions. Analyst downgrades citing demand weakness or competitive pressure. Institutional investors (13F filings) reducing positions in key AI hardware players. Negative outlook or missed expectations on AI revenue during earnings calls. Increased debt issuance without clear growth plans.",
    "reliable_sources": "SEC filings (10-K, 10-Q, 8-K), company investor relations (IR) pages for earnings transcripts and guidance, reputable financial news services (e.g., Bloomberg, Reuters, WSJ) reporting on analyst actions, institutional investor databases for 13F filings.",
    "query_angles": [
      "Company earnings guidance revision AI",
      "Analyst upgrade AI hardware semiconductor",
      "13F filing institutional ownership Nvidia AMD",
      "Earnings call transcript AI outlook"
    ],
    "source_domains": [
      "sec.gov",
      "ir.nvidia.com",
      "ir.amd.com",
      "ir.intel.com",
      "reuters.com",
      "bloomberg.com",
      "wsj.com"
    ],
    "search_terms": [
      "guidance",
      "earnings",
      "analyst upgrade",
      "13F",
      "institutional ownership",
      "8-K",
      "10-Q",
      "AI revenue",
      "data center"
    ],
    "avoid_patterns": [
      "generic stock market news",
      "unattributed rumors about guidance",
      "blog posts without verifiable sources"
    ]
  },
  "news_sentiment": {
    "positive_evidence": "Frequent positive headlines from major financial news outlets (Reuters, Bloomberg, WSJ) covering strong demand for AI chips, successful partnerships, significant customer wins for AI infrastructure, and government support for domestic semiconductor manufacturing. Analyst reports highlighting upward revisions to market forecasts and sustained growth. Focus on new applications and expanding markets for AI hardware.",
    "negative_evidence": "Negative headlines from major financial news outlets discussing oversupply concerns, canceled orders, competitive losses, regulatory hurdles (e.g., export controls impacting sales), or market saturation fears. Analyst reports with downward revisions, supply chain disruptions, or warnings about pricing pressure. Reports of major customer delays or shifting to competitors.",
    "reliable_sources": "Top-tier financial news agencies (Reuters, Bloomberg, Wall Street Journal), reputable tech news sites with strong financial reporting (e.g., The Information, TechCrunch with a focus on finance), equity research reports from major investment banks.",
    "query_angles": [
      "Nvidia AI market positive sentiment",
      "AMD AI chip demand news",
      "Intel data center positive coverage",
      "Samsung/TSMC AI influence (indirect for US companies)"
    ],
    "source_domains": [
      "reuters.com",
      "bloomberg.com",
      "wsj.com",
      "theinformation.com",
      "techcrunch.com"
    ],
    "search_terms": [
      "AI server",
      "accelerator",
      "data center",
      "chip demand",
      "semiconductor",
      "market outlook",
      "customer win",
      "partnership"
    ],
    "avoid_patterns": [
      "social media chatter",
      "clickbait articles from unknown sources",
      "purely speculative opinion pieces without data"
    ]
  },
  "pricing_pressure": {
    "positive_evidence": "Stable or increasing average selling prices (ASPs) for key AI GPUs and high-end servers. Limited or no significant discounts observed on distributor websites or in public tenders. Extended lead times for high-demand AI components without price drops. Cloud providers announcing stable or increased pricing for flagship AI instances. Company earnings calls mentioning strong margin performance in AI segments.",
    "negative_evidence": "Reports of discounting on volume orders for AI GPUs or servers. Visible price cuts on distributor websites (e.g., CDW, Insight) or in large enterprise procurement listings. Shorter lead times for previously constrained components. Cloud providers announcing price reductions for AI compute or new, more competitive pricing tiers. Company earnings calls noting margin pressure due to increased competition or inventory buildup.",
    "reliable_sources": "Distributor websites (e.g., CDW, Insight, Newegg Business), enterprise IT procurement portals, credible tech news outlets reporting on market pricing, financial news outlets covering earnings calls and market dynamics, cloud provider pricing pages (AWS, Azure, GCP).",
    "query_angles": [
      "Nvidia H100 price availability",
      "AI server discount Dell HPE Supermicro",
      "Cloud GPU pricing AWS Microsoft Azure",
      "AMD Instinct MI300X lead times"
    ],
    "source_domains": [
      "cdw.com",
      "insight.com",
      "neweggbusiness.com",
      "aws.amazon.com",
      "azure.microsoft.com",
      "cloud.google.com",
      "reuters.com",
      "wsj.com"
    ],
    "search_terms": [
      "price",
      "discount",
      "availability",
      "lead time",
      "ASP",
      "margin",
      "GPU",
      "server",
      "data center",
      "H100",
      "MI300X"
    ],
    "avoid_patterns": [
      "consumer electronics pricing sites",
      "forums speculating on future prices",
      "unverified claims of 'super deals'"
    ]
  },
  "strategic_messaging": {
    "positive_evidence": "CEO/CFO comments from earnings calls, investor days, or major conferences emphasizing long-term AI growth strategy, significant R&D investments in next-gen AI hardware, expansion into new AI markets (e.g., edge AI, sovereign AI), and strong customer relationships for future AI deployments. Focus on robust AI roadmap and technological leadership. Announcements of strategic AI acquisitions or investments.",
    "negative_evidence": "CEO/CFO remarks expressing caution about the pace of AI hardware adoption, emphasizing cost optimization over growth, or signaling a shift in strategic focus away from aggressive AI expansion. Downplaying near-term AI revenue potential. Comments indicating increased competitive hurdles or difficulty securing critical supply. Lack of new strategic AI initiatives.",
    "reliable_sources": "Company investor relations (IR) pages for earnings call transcripts, investor day webcasts and presentations, official press releases on strategy, reputable financial news outlets quoting executives from interviews or conferences.",
    "query_angles": [
      "Nvidia CEO AI strategy comments",
      "Intel data center roadmap investor day",
      "AMD AI hardware outlook earnings call",
      "Micron HBM strategic positioning"
    ],
    "source_domains": [
      "ir.nvidia.com",
      "ir.amd.com",
      "ir.intel.com",
      "ir.micron.com",
      "reuters.com",
      "bloomberg.com"
    ],
    "search_terms": [
      "AI strategy",
      "roadmap",
      "data center",
      "capex",
      "investor day",
      "CEO comment",
      "earnings call",
      "long-term growth",
      "innovation"
    ],
    "avoid_patterns": [
      "analyst opinions masquerading as management quotes",
      "speculative articles on company future without direct executive attribution",
      "generic mission statements"
    ]
  },
  "hiring_momentum": {
    "positive_evidence": "High volume of open requisitions on company career pages and LinkedIn for specialized AI hardware roles (e.g., GPU architects, AI/ML hardware engineers, HBM designers, data center sales, CUDA developers). Multiple identical postings for critical senior roles at various levels. Management commentary during earnings calls or investor presentations about expanding AI-focused workforce and talent acquisition initiatives.",
    "negative_evidence": "Noticeable decline in open requisitions for AI hardware roles. Announcements of hiring freezes impacting AI divisions. Reports of layoffs affecting hardware engineering teams or AI/ML specific roles. Less frequent updates on career pages. Management commentary during earnings calls indicating headcount reductions or hiring slowdowns.",
    "reliable_sources": "Company career websites, LinkedIn Jobs, reputable tech/financial news outlets reporting on hiring trends or layoffs, WARN Act notices (for severe layoffs, though less common within 7 days for US-wide signals unless very large scale).",
    "query_angles": [
      "Nvidia careers AI hardware jobs",
      "AMD LinkedIn GPU architect openings",
      "Intel data center hiring momentum news",
      "Micron HBM engineer jobs"
    ],
    "source_domains": [
      "careers.nvidia.com",
      "linkedin.com/jobs/nvidia",
      "careers.amd.com",
      "careers.intel.com",
      "reuters.com",
      "theinformation.com"
    ],
    "search_terms": [
      "GPU architect",
      "AI accelerator engineer",
      "CUDA developer",
      "HBM designer",
      "data center sales",
      "hiring freeze",
      "layoffs",
      "AI hardware jobs"
    ],
    "avoid_patterns": [
      "generic IT job sites",
      "old job postings without date filters",
      "social media rumors about hiring changes"
    ]
  },
  "product_launch": {
    "positive_evidence": "Official press releases and product pages announcing new AI chips (GPUs, accelerators), server platforms optimized for AI, or significant updates improving performance or efficiency. Benchmarking results showing competitive leadership. Major customer announcements adopting new AI products. Partner ecosystem expanding with new software or hardware integrations. Availability announcements for new products.",
    "negative_evidence": "Delays announced for previously anticipated AI product launches. Reduced feature sets or performance expectations for upcoming products. Lack of new significant product announcements from key players. Negative reviews or poor benchmark performance for recently launched AI hardware. Customer adoption lagging expectations.",
    "reliable_sources": "Company press release sections (IR newsrooms), official product pages, reputable tech news sites (e.g., AnandTech, ServeTheHome, The Register) covering hardware launches, industry analyst reports on new products.",
    "query_angles": [
      "Nvidia new AI GPU launch",
      "AMD Instinct accelerator announcement",
      "Intel Gaudi server release date",
      "Supermicro AI server new models"
    ],
    "source_domains": [
      "nvidia.com/en-us/news",
      "amd.com/en/newsroom",
      "intel.com/content/www/us/en/newsroom",
      "supermicro.com/en/newsroom",
      "anandtech.com",
      "servethehome.com"
    ],
    "search_terms": [
      "launch",
      "release",
      "announce",
      "available",
      "AI chip",
      "GPU",
      "accelerator",
      "server",
      "roadmap update",
      "benchmark"
    ],
    "avoid_patterns": [
      "unsubstantiated rumors on forums",
      "historical product catalogs without new announcements",
      "marketing fluff without concrete product details"
    ]
  },
  "supplier_risk": {
    "positive_evidence": "News reports or company statements indicating diversified supply chains, successful qualification of multiple component suppliers (e.g., HBM, CoWoS packaging), increased capacity at critical foundries (TSMC, Samsung), reduced lead times for key components, and strong inventory levels for critical materials. Positive commentary from leadership about supply chain resilience.",
    "negative_evidence": "News reports detailing HBM (High Bandwidth Memory) shortages impacting AI chip production. Mentions of CoWoS (Chip-on-Wafer-on-Substrate) packaging capacity constraints at TSMC or other foundries. Reports on increased component lead times for critical materials like specialty logic or substrates. Geopolitical news suggesting new export controls impacting specific materials or technologies. Company earnings calls mentioning supply chain as a limiting factor for AI hardware revenue.",
    "reliable_sources": "Reputable financial and industry news outlets (Reuters, Bloomberg, Nikkei Asia, DigiTimes), official statements from chip manufacturers (TSMC, Samsung), company earnings call transcripts discussing supply chain, industry analyst reports on component markets.",
    "query_angles": [
      "HBM supply shortage impact AI hardware",
      "TSMC CoWoS capacity for Nvidia AMD",
      "Export control semiconductor supply chain USA",
      "Micron HBM production constraints"
    ],
    "source_domains": [
      "reuters.com",
      "bloomberg.com",
      "asia.nikkei.com",
      "digitimes.com",
      "ir.nvidia.com",
      "ir.amd.com"
    ],
    "search_terms": [
      "supply risk",
      "shortage",
      "export control",
      "HBM",
      "CoWoS",
      "foundry capacity",
      "component lead time",
      "supply chain disruption",
      "geopolitical risk"
    ],
    "avoid_patterns": [
      "generalized economic gloom predictions",
      "outdated articles on past supply chain issues (without current relevance)",
      "social media speculation on component failures"
    ]
  }
}
```

### 1e. Query Quantity Check

The live normal run produced **26** validated queries, not 29. Matrix size is 8 companies × 7 signal types = 56 company-signal cells.

| Run | Query count | Company-signal cells covered | Coverage of 56 cells | Missing investor_signal companies |
|---|---:|---:|---:|---|
| Normal target 24-32 | 26 | 24 | 42.9% | Dell, HPE, Micron |
| Forced target 40-50 | 43 | 37 | 66.1% | Dell, HPE, Micron |

Normal coverage by signal:
```json
{
  "investor_signal": 5,
  "news_sentiment": 4,
  "pricing_pressure": 4,
  "strategic_messaging": 3,
  "hiring_momentum": 4,
  "product_launch": 4,
  "supplier_risk": 2
}
```

Forced 40-50 coverage by signal:
```json
{
  "investor_signal": 7,
  "news_sentiment": 5,
  "pricing_pressure": 9,
  "strategic_messaging": 7,
  "hiring_momentum": 7,
  "product_launch": 6,
  "supplier_risk": 2
}
```

Verdict: **26 is not enough** for a useful full-market intelligence report. It covers only 24/56 company-signal cells, and the missing cells include high-weight `investor_signal` for Dell, HPE, and Micron. If a company has 0 investor-signal queries, Agent 2 cannot retrieve earnings/filing/guidance evidence for that company, and downstream scoring will mistake “not searched” for “no signal.”

Recommendation: **increase target to 40-50, but also add hard coverage constraints.** The 43-query run improved coverage to 37/56 cells, but still missed investor-signal for Dell/HPE/Micron and generated stale `Q3 2024` queries. Quantity alone is insufficient; validation must enforce high-weight signal coverage per company and time-anchor correctness.

### 1f. Query Quality Check

Five worst queries from the normal run:

| Query | Why weak |
|---|---|
| `HPE Cloud GPU pricing Microsoft Azure May 2026 site:azure.microsoft.com` | Targets HPE but retrieves Azure pages; dynamic_pages run returned 0 docs with repeated BrightData 400 errors. |
| `Micron HBM production constraints` | No time anchor, no source operator, too broad; violates the prompt but validation does not catch it. |
| `AI hardware market demand forecast analyst report May 2026 site:theinformation.com` | Broad market query on a likely protected/paywalled source; weak company/signal specificity. |
| `Nvidia AI chip demand strong news last 7 days site:wsj.com` | Generic sentiment phrase and paywalled source; likely broad articles, not a precise signal. |
| `Supermicro AI server roadmap outlook last 7 days site:reuters.com` | Generic and overconstrained to Reuters; live run returned only 3 docs with some off-target failures. |

Five best queries from the normal run:

| Query | Why strong |
|---|---|
| `AMD 13F institutional ownership May 2026 site:sec.gov` | Specific investor signal, authoritative source, time anchored. |
| `Nvidia Q1 2026 earnings guidance revision AI site:ir.nvidia.com last 7 days` | Targets earnings/guidance and produced an official Nvidia earnings release. |
| `AMD Instinct MI300X lead times distributor pricing May 2026 site:insight.com` | Concrete product + pricing/availability angle + distributor source. |
| `AMD GPU architect openings LinkedIn May 2026 site:linkedin.com/jobs/amd` | Specific hiring role pattern and source type. |
| `Nvidia H100 GPU price availability CDW last 7 days site:cdw.com` | Concrete product/SKU pricing query; returned actual CDW H100 product pages. |

Pattern: good queries combine company + specific signal + source/operator + time/product/filing term. Bad queries are broad, overconstrained to a weak source, missing time anchors, or target the wrong source ecosystem.

Does Step-Back influence quality? **Yes, but weakly.** The strongest queries mirror Step-Back fields like `reliable_sources`, `query_angles`, and `search_terms`. But the prompt influence is not enforced: `Micron HBM production constraints` lacks a time anchor despite the rule, and the target-40 run generated stale `Q3 2024` queries despite the current date and time window. Add validators for time anchors, source/operator-source consistency, and stale-year rejection.

## PART 2 — Agent 2: BrightData Real Run + Output Quality

### 2a. Live Run For 5 Source Types

#### `serp_news`

- Exact query sent: `Intel analyst upgrade price target AI hardware last 7 days site:reuters.com OR site:bloomberg.com`
- Tool path in code: SERP API for discovery, then Web Scraper API
- Documents returned: **5**

1. `https://www.reuters.com/technology/`
   - source_tier: `2`
   - title: Tech News | Today's Latest Technology News | Reuters
   - quality: **POOR** — SERP result landed on Reuters technology index; content begins with support/browser scripts, not the Intel analyst-upgrade fact requested.
   - first 300 chars: `Tech News | Today&#x27;s Latest Technology News | Reuters (function(){ var current_location = window.location.href; if (current_location.indexOf('/info-pages/supported-browsers/') === -1) { var supportFetchApi = 'fetch' in window; var supportCSSGrid = window.CSS && CSS.supports('display', 'grid'); i`

2. `https://www.bloomberg.com/news/articles/2025-12-29/nvidia-samsung-and-lenovo-test-consumer-demand-for-ai-gadgets-at-ces`
   - source_tier: `2`
   - title: Nvidia, Samsung and Lenovo Test Consumer Demand for AI Gadgets at CES - Bloomberg
   - quality: **MEDIUM** — Relevant to AI hardware broadly but not Intel analyst upgrade; heavy CSS/JS noise.
   - first 300 chars: `Nvidia, Samsung and Lenovo Test Consumer Demand for AI Gadgets at CES - Bloomberg /* Declare CSS layer order before any stylesheets load. */ /* This must be an inline style in the document head so */ /* it survives Next.js hydration style-tag replacement and */ /* always comes first, guaranteeing ta`

3. `https://www.reuters.com/business/storage-stocks-jump-seagates-upbeat-forecast-fuels-confidence-ai-spending-2026-04-28/`
   - source_tier: `2`
   - title: Data-storage stocks jump as Seagate's upbeat forecast fuels confidence in AI spending | Reuters
   - quality: **MEDIUM** — Specific AI-spending article, but about storage stocks rather than Intel; extractable but off-target.
   - first 300 chars: `Data-storage stocks jump as Seagate&#x27;s upbeat forecast fuels confidence in AI spending | Reuters (function(){ var current_location = window.location.href; if (current_location.indexOf('/info-pages/supported-browsers/') === -1) { var supportFetchApi = 'fetch' in window; var supportCSSGrid = windo`

4. `https://www.bloomberg.com/graphics/2026-investment-outlooks/`
   - source_tier: `2`
   - title: Stock Market Predictions 2026: AI Boom, Dollar’s Decline and Sticky Inflation
   - quality: **MEDIUM** — Broad 2026 market outlook; likely contains AI-boom context but not the target Intel fact.
   - first 300 chars: `@font-face{font-family:AvenirNextPForBBG;font-display:swap;font-weight:400;font-style:normal;src:url('https://assets.bwbx.io/s3/fontservice/fonts/AvenirNextPForBBG-Regular-eb3bb1b816.woff2') format('woff2'),url('https://assets.bwbx.io/s3/fontservice/fonts/AvenirNextPForBBG-Regular-093448f517.woff')`

5. `https://www.bloomberg.com/news/audio/2025-09-15/stock-movers-seagate-western-digital-corteva-podcast`
   - source_tier: `2`
   - title: Stock Movers : Seagate, Western Digital, Corteva - Bloomberg
   - quality: **POOR** — Specific article metadata, but unrelated to Intel AI hardware and stale relative to May 2026.
   - first 300 chars: `Stock Movers : Seagate, Western Digital, Corteva - Bloomberg {"@context":"http://schema.org","@type":"NewsArticle","author":"Bloomberg","dateCreated":"2025-09-15T15:16:21.513Z","datePublished":"2025-09-15T15:16:21.513Z","description":"On this episode of Stock Movers:\n\nSeagate (STX; +7%) -- compute`

#### `ir_pages`

- Exact query sent: `Nvidia Q1 2026 earnings guidance revision AI site:ir.nvidia.com last 7 days`
- Tool path in code: SERP API for discovery, then Web Scraper API
- Documents returned: **5**

1. `https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2026`
   - source_tier: `4`
   - title: NVIDIA Announces Financial Results for First Quarter Fiscal 2026 | NVIDIA Newsroom
   - quality: **GOOD** — Official Nvidia earnings release with revenue, data-center, inventory charge, guidance facts.
   - first 300 chars: `NVIDIA Announces Financial Results for First Quarter Fiscal 2026 | NVIDIA Newsroom function OptanonWrapper() { var event = new Event('bannerLoaded'); window.dispatchEvent(event); if (typeof OnetrustActiveGroups !== 'undefined') { // C0002 = Performance/Analytics cookies if (OnetrustActiveGroups.incl`

2. `https://www.cnbc.com/2026/05/20/nvidia-nvda-earnings-report-q1-2027.html`
   - source_tier: `4`
   - title: Nvidia (NVDA) Q1 2027 earnings report: Live updates
   - quality: **MEDIUM** — Relevant earnings live page, but scraper content starts as CSS; may still contain facts later.
   - first 300 chars: `@charset "UTF-8";.Modal-modalBackground{background:#000000b3;height:100%;left:0;overflow-y:auto;position:fixed;top:0;transition:background-color .4s;width:100%;z-index:100001}.Modal-modalBackgroundBlur{backdrop-filter:blur(4px);background:#00000040}.Modal-modalBackgroundCentered{align-items:center;b`

3. `https://www.kiplinger.com/investing/live/nvidia-earnings-live-updates-and-commentary-may-2026`
   - source_tier: `4`
   - title: Nvidia Earnings: Updates and Commentary May 2026 | Kiplinger
   - quality: **MEDIUM** — Relevant live updates, but heavy styling noise; facts may be buried.
   - first 300 chars: `Nvidia Earnings: Updates and Commentary May 2026 | Kiplinger @layer reset, legacy, tw-components, components, tw-utilities, utilities, van-ds, hawk, global; @layer legacy { :root { --color-primary-50: 251 208 210; --color-primary-100: 248 175 179; --color-primary-200: 245 142 147; --color-primary-30`

4. `https://www.investing.com/equities/nvidia-corp-earnings`
   - source_tier: `4`
   - title: NVIDIA (NVDA) Earnings Date Report - Investing.com
   - quality: **MEDIUM** — Earnings calendar/report page; relevant but likely market-data layout noise.
   - first 300 chars: `NVIDIA (NVDA) Earnings Date Report - Investing.com window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)};window.__imntz=window.__imntz||{};window.__imntz.queue=window.__imntz.queue||[];window.googletag=window.googletag||{cmd:[]};window.yaContextCb=window.yaContextCb||[];wi`

5. `https://www.spglobal.com/market-intelligence/en/news-insights/research/2025/05/nvidia-earnings-preview-fiscal-q1-2026`
   - source_tier: `4`
   - title: Nvidia earnings preview: Fiscal Q1 2026 | S&P Global
   - quality: **MEDIUM** — Relevant earnings preview but older and script-heavy.
   - first 300 chars: `!function(d,s){var ip=d.createElement(s);ip.async=1,s=d.getElementsByTagName(s)[0],ip.src='//s.idio.co/ip.js',s.parentNode.insertBefore(ip,s)}(document,'script'); var _rollbarConfig = { accessToken: "4b67105e5046468aa40a0673e3219199", captureUncaught: false, captureUnhandledRejections: false, captur`

#### `job_pages`

- Exact query sent: `Nvidia careers AI hardware jobs site:nvidia.com last 7 days`
- Tool path in code: SERP API for discovery, then Web Scraper API
- Documents returned: **5**

1. `https://jobs.nvidia.com/`
   - source_tier: `4`
   - title: Careers at NVIDIA Corporation
   - quality: **MEDIUM** — Relevant careers page but broad; not a specific dated job fact.
   - first 300 chars: `window.COUNTRY_CODE = "US"; window.USER_LOCALE = window.i18nUtils?.getLocale() || 'en'; #hiring_title-content .stack-module_gap-m__-jQR9 .checkbox-module_selector__iBN7W:last-of-type {display: none;} #hiring_title-content {height:300px} window.dataLayer = window.dataLayer || []; function gtag(){data`

2. `https://www.nvidia.com/en-us/about-nvidia/careers/university-recruiting/`
   - source_tier: `4`
   - title: University Recruiting and Early-Talent Programs | NVIDIA Career
   - quality: **POOR** — Recruiting landing page, not specific hiring momentum evidence.
   - first 300 chars: `function OptanonWrapper() { var event = new Event('bannerLoaded'); window.dispatchEvent(event); } var NVIDIAGDC = NVIDIAGDC || {}; ;(function ( nvidiaGDC ){ nvidiaGDC.addProperty = function(obj, name, val){ if (!obj && !name){ return; } nvidiaGDC[obj] = nvidiaGDC[obj] || {}; if(typeof val != "undefi`

3. `http://jobs.nvidia.com/careers/job/893392855558`
   - source_tier: `4`
   - title: Senior AI Infrastructure Software Engineer | NVIDIA Corporation
   - quality: **GOOD** — Specific JobPosting JSON with title, datePosted, and description; strong fact-extraction candidate.
   - first 300 chars: `window.COUNTRY_CODE = "US"; window.USER_LOCALE = window.i18nUtils?.getLocale() || 'en'; {"@context": "http://schema.org", "@type": "JobPosting", "datePosted": "2026-01-19T00:00:00", "description": "NVIDIA has been transforming accelerated computing with innovation that\u2019s fueled by great technol`

4. `https://www.nvidia.com/en-us/about-nvidia/careers/how-we-hire/`
   - source_tier: `4`
   - title: How We Hire
   - quality: **POOR** — Hiring-process page, not current momentum evidence.
   - first 300 chars: `function OptanonWrapper() { var event = new Event('bannerLoaded'); window.dispatchEvent(event); } var NVIDIAGDC = NVIDIAGDC || {}; ;(function ( nvidiaGDC ){ nvidiaGDC.addProperty = function(obj, name, val){ if (!obj && !name){ return; } nvidiaGDC[obj] = nvidiaGDC[obj] || {}; if(typeof val != "undefi`

5. `https://jobs.nvidia.com/careers?filter_job_type=intern+%28fixed+term%29%2Cnew+college+graduate`
   - source_tier: `4`
   - title: Careers at NVIDIA Corporation
   - quality: **MEDIUM** — Careers listing with structured data, but broad and duplicate-ish.
   - first 300 chars: `window.COUNTRY_CODE = "US"; window.USER_LOCALE = window.i18nUtils?.getLocale() || 'en'; #hiring_title-content .stack-module_gap-m__-jQR9 .checkbox-module_selector__iBN7W:last-of-type {display: none;} #hiring_title-content {height:300px} window.dataLayer = window.dataLayer || []; function gtag(){data`

#### `pricing_pages`

- Exact query sent: `Nvidia H100 GPU price availability CDW last 7 days site:cdw.com`
- Tool path in code: SERP API for discovery, then Web Scraper API
- Documents returned: **5**

1. `https://www.uk.cdw.com/about/octo/insights/ai-platforms/`
   - source_tier: `4`
   - title: Hybrid Platforms Trends Series - AI - Platforms | CDW UK
   - quality: **POOR** — CDW UK thought-leadership page, not H100 price/availability.
   - first 300 chars: `function OptanonWrapper() { } Hybrid Platforms Trends Series - AI - Platforms | CDW UK sessionStorage.fontsLoaded && document.documentElement.classList.add("wf-active"); html{box-sizing:border-box}*,:after,:before{box-sizing:inherit}/*! normalize.css v5.0.0 | MIT License | github.com/necolas/normali`

2. `https://www.cdw.com/product/nvidia-h100-gpu-computing-processor-nvidia-h100-tensor-core-80-gb/8268491`
   - source_tier: `4`
   - title: NVIDIA H100 - GPU computing processor - NVIDIA H100 Tensor Core - 80 GB - UCSC-GPU-H100-80= - CPUs - CDW.com
   - quality: **GOOD** — Actual product page for H100; should contain SKU/availability/pricing fields if present.
   - first 300 chars: `NVIDIA H100 - GPU computing processor - NVIDIA H100 Tensor Core - 80 GB - UCSC-GPU-H100-80= - CPUs - CDW.com // akam-sw.js install script version 1.3.6 "serviceWorker"in navigator&&"find"in[]&&function(){var e=new Promise(function(e){"complete"===document.readyState||!1?e():(window.addEventListener(`

3. `https://www.uk.cdw.com/about/octo/insights/hpe-discover-2024/`
   - source_tier: `4`
   - title: What did I Discover at HPE Discover 2024? | CDW UK
   - quality: **POOR** — HPE Discover article, off-target for Nvidia H100 pricing.
   - first 300 chars: `function OptanonWrapper() { } What did I Discover at HPE Discover 2024?&#xA0;| CDW UK sessionStorage.fontsLoaded && document.documentElement.classList.add("wf-active"); html{box-sizing:border-box}*,:after,:before{box-sizing:inherit}/*! normalize.css v5.0.0 | MIT License | github.com/necolas/normaliz`

4. `https://www.cdw.com/product/nvidia-h100-nvl-gpu-computing-processor-nvidia-h100-nvl-tensor-core-9/8388278`
   - source_tier: `4`
   - title: NVIDIA H100 NVL - GPU computing processor - NVIDIA H100 NVL Tensor Core - 94 GB - UCSX-GPU-H100-NVL= - CPUs - CDW.com
   - quality: **GOOD** — Actual H100 NVL product page; strong pricing/availability candidate.
   - first 300 chars: `NVIDIA H100 NVL - GPU computing processor - NVIDIA H100 NVL Tensor Core - 94 GB - UCSX-GPU-H100-NVL= - CPUs - CDW.com // akam-sw.js install script version 1.3.6 "serviceWorker"in navigator&&"find"in[]&&function(){var e=new Promise(function(e){"complete"===document.readyState||!1?e():(window.addEvent`

5. `https://www.uk.cdw.com/about/octo/insights/netapp-insight-2023/`
   - source_tier: `4`
   - title: Reflecting on Netapp Insight 2023: A Key Focus on AI Data Pipeline, Storage Consistency and Data Protection
   - quality: **POOR** — NetApp 2023 thought-leadership page, off-target and stale.
   - first 300 chars: `function OptanonWrapper() { } Reflecting on Netapp Insight 2023: A Key Focus on AI Data Pipeline, Storage Consistency and Data Protection sessionStorage.fontsLoaded && document.documentElement.classList.add("wf-active"); html{box-sizing:border-box}*,:after,:before{box-sizing:inherit}/*! normalize.cs`

#### `dynamic_pages`

- Exact query sent: `HPE Cloud GPU pricing Microsoft Azure May 2026 site:azure.microsoft.com`
- Tool path in code: SERP API for discovery, then Scraping Browser/browser_zone
- Documents returned: **0**

_No documents returned._


### 2b. Content Quality Assessment

Summary from the selected live documents:

```json
{
  "POOR": 7,
  "MEDIUM": 9,
  "GOOD": 4
}
```

The useful pages are real product pages, official earnings releases, and specific job postings. The weak pages are index pages, broad thought-leadership pages, paywalled/news pages with 200k chars of CSS/JS, and off-target search results. Agent 2 should add relevance filtering before scraping or before passing documents to Agent 3.

### 2c. Light JSON vs Full JSON Decision

Current live SERP response shape from `pulselens_serp`:
```json
{
  "query": "Intel analyst upgrade price target AI hardware last 7 days site:reuters.com OR site:bloomberg.com",
  "payload_type": "dict",
  "top_keys": [
    "organic"
  ],
  "organic_count": 10,
  "first_organic_keys": [
    "link",
    "title",
    "description",
    "global_rank"
  ]
}
```

First organic result from current zone:
```json
{
  "link": "https://www.reuters.com/technology/",
  "title": "Tech News | Today's Latest Technology News",
  "description": "Technology · Nvidia says its forecast for $200 billion CPU market includes China · China's DeepSeek to make permanent 75% price cut on flagship V4‑Pro AI model.Read more",
  "global_rank": 1
}
```

I could not do a true same-zone Light JSON vs Full JSON A/B from code because the data format is a BrightData zone configuration, not something this client currently switches per request. The current zone returns a light-shaped payload: top-level key `organic`, with each result containing `link`, `title`, `description`, and `global_rank`.

Recommendation: **keep Light JSON for SERP discovery**. Full JSON may include ads, knowledge panels, related searches, and extra SERP metadata, but Agent 3 extracts facts from scraped result pages, not from SERP metadata. Full JSON would increase parsing noise and cost without materially improving extractable facts. The bigger improvement is better query/result relevance filtering.

### 2d. `ir_pages` Routing Check

Two live `ir_pages` runs:

| Query | Docs returned | Notes |
|---|---:|---|
| `Nvidia Q1 2026 earnings guidance revision AI site:ir.nvidia.com last 7 days` | 5 | top domains: nvidianews.nvidia.com, cnbc.com, spglobal.com; tiers: 4, 4, 4 |
| `AMD 13F institutional ownership May 2026 site:sec.gov` | 5 | top domains: sec.gov, sec.gov, sec.gov; tiers: 1, 1, 1 |

Verdict: **fixed for zero-result behavior, not fixed for precision/tiering**. `ir_pages` queries now return documents because Agent 2 always uses SERP discovery first. But `Nvidia site:ir.nvidia.com` returned `nvidianews.nvidia.com`, CNBC, Kiplinger, Investing.com, etc.; most were tier 4. The query expected Tier 1 but got mixed sources. Correct fix: preserve SERP discovery, then filter candidate URLs by allowed domain for `ir_pages` when a `site:` operator or company IR domain is specified. Also consider tiering official company newsroom subdomains.

### 2e. Zero-Result Queries

- Total normal queries scanned: **26**
- Zero-result queries: **1**
  - `dynamic_pages`: `HPE Cloud GPU pricing Microsoft Azure May 2026 site:azure.microsoft.com`

Zero-result rate by source type:
```json
{
  "ir_pages": {
    "queries": 8,
    "zero_result": 0
  },
  "serp_news": {
    "queries": 11,
    "zero_result": 0
  },
  "pricing_pages": {
    "queries": 3,
    "zero_result": 0
  },
  "dynamic_pages": {
    "queries": 1,
    "zero_result": 1
  },
  "job_pages": {
    "queries": 3,
    "zero_result": 0
  }
}
```

Verdict: one zero-result out of 26 is acceptable numerically, but the failed query is meaningful: `dynamic_pages` currently has a 100% failure rate in this sample. BrightData returned repeated 400s for Azure URLs through the current dynamic route. This should be fixed before relying on dynamic source types.

## PART 3 — Agent 3: Implementation Quality Check

### 3a. RASG Implementation Check

| RASG requirement | Status | Evidence |
|---|---|---|
| Forbid free-form summarization | PASS | Prompt says return only JSON and extract only explicit facts at [agent3_fact_extractors.py](backend/app/pipeline/agent3_fact_extractors.py:28). |
| Exact JSON schema | PASS | Schema fields listed at [agent3_fact_extractors.py](backend/app/pipeline/agent3_fact_extractors.py:32). |
| GOOD/BAD examples | FAIL | No examples in the extraction prompt. |
| Verbatim evidence quote | PASS | Prompt requires exact substring at [agent3_fact_extractors.py](backend/app/pipeline/agent3_fact_extractors.py:37) and [agent3_fact_extractors.py](backend/app/pipeline/agent3_fact_extractors.py:43). |
| Claim cap 150 chars | PASS in prompt, PARTIAL in code | Prompt says max 150 at [agent3_fact_extractors.py](backend/app/pipeline/agent3_fact_extractors.py:36), but `_build_fact()` silently truncates at [agent3_fact_extractors.py](backend/app/pipeline/agent3_fact_extractors.py:115) instead of rejecting. |
| True tool use | PARTIAL / FAIL | The implementation uses `call_json()`, not OpenAI/Anthropic function/tool calling. It is schema-constrained prompting, not hard tool invocation. |

Verdict: **RASG-inspired, not full RASG tool use**. Good enough for a hackathon prototype, not robust enough for production extraction.

### 3b. Validation Completeness

Validation code checks verbatim quote, claim length, confidence, and entity at [node_validate_and_split.py](backend/app/pipeline/node_validate_and_split.py:47).

Break-test result from real code:
```json
{
  "input_fact_ids": [
    "fact_test_base",
    "fact_test_near_quote",
    "fact_test_low_conf",
    "fact_test_bad_entity",
    "fact_test_long_claim"
  ],
  "passed_fact_ids": [
    "fact_test_base"
  ]
}
```

Only the base fact passed. A one-character near-quote failed, confidence `0.59` failed, `FakeCompany` failed, and a 151-character claim failed. So `validate_facts()` itself works.

Important caveats:
- `_build_fact()` truncates claims and evidence quotes before validation. That can hide overlong claims rather than reject them.
- `KNOWN_ENTITIES` includes aliases such as lowercase company names; validation passes aliases but does not canonicalize them.
- The `0.6` confidence threshold is acceptable as a recall-oriented hackathon threshold, but for financial intelligence I would raise extraction validation to `0.7` after you have enough source volume.

### 3c. SAFE Atomic Verification Check

| SAFE step | Status | Evidence |
|---|---|---|
| Decompose claim into atomic sub-claims | IMPLEMENTED | LLM `call_json()` at [node_validate_and_split.py](backend/app/pipeline/node_validate_and_split.py:103). |
| Verify each atomic claim against evidence_quote | IMPLEMENTED | `call_text()` with atomic claim and quote at [node_validate_and_split.py](backend/app/pipeline/node_validate_and_split.py:123). |
| Enforce 50% threshold | IMPLEMENTED | `_MIN_SUPPORT_RATIO = 0.5` at [node_validate_and_split.py](backend/app/pipeline/node_validate_and_split.py:19), checked at [node_validate_and_split.py](backend/app/pipeline/node_validate_and_split.py:138). |
| Conservative behavior on LLM failure | FAIL | Split failure marks fact verified at [node_validate_and_split.py](backend/app/pipeline/node_validate_and_split.py:115); verify failure counts atomic as supported at [node_validate_and_split.py](backend/app/pipeline/node_validate_and_split.py:132). |

SAFE is structurally implemented but **fails open**. For trustworthiness, SAFE should fail closed or mark facts as `safe_verified=False` when the verifier fails.

### 3d. Live Agent 3 Run On Real Agent 2 Output

Input: first returned document from each successful selected Agent 2 source type. Dynamic page had 0 docs, so Agent 3 received 4 documents.

| Stage | Count |
|---|---:|
| Input documents | 4 |
| Raw facts extracted | 3 |
| Passed `validate_facts()` | 2 |
| Passed SAFE | 2 |

Raw fact failure observed: one fact used `evidence_quote: "revenue ... up 69% from a year ago."`, which was not a verbatim substring and was correctly discarded by validation.

Final SAFE-verified FactObjects:
```json
[
  {
    "fact_id": "fact_9add84f8f7c6",
    "doc_id": "doc_1ad079f9efdb",
    "entity": "Nvidia",
    "signal_type": "investor_signal",
    "claim": "NVIDIA's revenue for the first quarter ended April 27, 2025, was $44.1 billion, a 12% increase from the previous quarter.",
    "evidence_quote": "NVIDIA (NASDAQ: NVDA) today reported revenue for the first quarter ended April 27, 2025, of $44.1 billion, up 12% from the previous quarter",
    "source_url": "https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2026",
    "source_tier": 4,
    "published_date": "2025-05-28",
    "sentiment": "neutral",
    "sentiment_score": 0.0,
    "confidence": 0.95,
    "atomic_claims": [
      "NVIDIA's revenue for the first quarter was $44.1 billion.",
      "NVIDIA's first quarter ended on April 27, 2025.",
      "NVIDIA's revenue increased by 12% from the previous quarter."
    ],
    "safe_verified": true
  },
  {
    "fact_id": "fact_73173aa14f2c",
    "doc_id": "doc_1ad079f9efdb",
    "entity": "Nvidia",
    "signal_type": "investor_signal",
    "claim": "NVIDIA incurred a $4.5 billion charge in Q1 fiscal 2026 due to H20 excess inventory and purchase obligations linked to new export license requirements",
    "evidence_quote": "NVIDIA incurred a $4.5 billion charge in the first quarter of fiscal 2026 associated with H20 excess inventory and purchase obligations as the demand for H20 diminished.",
    "source_url": "https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2026",
    "source_tier": 4,
    "published_date": "2025-05-28",
    "sentiment": "neutral",
    "sentiment_score": 0.0,
    "confidence": 0.9,
    "atomic_claims": [
      "NVIDIA incurred a charge of $4.5 billion.",
      "The charge occurred in Q1 fiscal 2026.",
      "The charge was due to H20 excess inventory."
    ],
    "safe_verified": true
  }
]
```

Assessment: the final facts are factual and the surviving evidence quotes are genuinely verbatim. However, the live extraction yield is too low: 2 final facts from 4 documents. This is caused mainly by noisy scraped pages and weak relevance filtering before Agent 3. Agent 3 cannot rescue low-quality Agent 2 inputs.

### 3e. LangGraph Integration Status

Agent 3 is **not integrated into LangGraph yet**. `graph.py` still has placeholders:

- `fact_extractor()` returns `{}` at [graph.py](backend/app/pipeline/graph.py:59).
- `validate_fact()` returns `{}` at [graph.py](backend/app/pipeline/graph.py:65).
- `validate_and_split()` returns `{}` at [graph.py](backend/app/pipeline/graph.py:71).

This means standalone Agent 3 works, but pipeline Agent 3 does not run.

## Issues Prioritized

### Critical

1. **Agent 3 and validation are not wired into LangGraph.** `graph.py` placeholder nodes return `{}`. Pipeline cannot actually produce facts yet.
2. **SAFE fails open on LLM errors.** A failed split or verify can mark facts as verified. This violates the trustworthiness goal.

### High

1. **Agent 1 undercovers the company-signal matrix.** Normal run covered 24/56 cells; even 43 queries covered only 37/56 and missed investor-signal for Dell/HPE/Micron.
2. **Agent 2 lacks relevance filtering.** SERP query for Intel analyst upgrade returned Reuters technology index and unrelated Bloomberg/Seagate pages.
3. **Dynamic pages failed in live run.** The only `dynamic_pages` query returned 0 docs after repeated BrightData 400 errors.
4. **Source tiering is too exact-domain based.** Official Nvidia Newsroom result was tier 4, while the query expected tier 1-like official source quality.

### Medium

1. **Step-Back is adapted evidence abstraction, not pure paper-faithful concept/principle abstraction.** This is acceptable if documented honestly.
2. **Query validation does not enforce time anchors or stale-year rejection.** Target-40 generated Q3 2024 queries during a May 2026 audit.
3. **RASG lacks examples and true tool calling.** It is schema-prompted JSON, not actual function/tool use.
4. **Agent 3 silently truncates claims and quotes.** Rejecting is safer than truncating for auditability.

### Low

1. Prompt says source type `job_pages` means LinkedIn/Glassdoor/Indeed, but live queries often target company careers pages. That may be fine, but the source taxonomy should say so.
2. Agent 2 comment says Bright Data SDK, but implementation is an HTTP wrapper. Not harmful, just naming precision.

## Final Readiness Verdict

| Component | Verdict | Why |
|---|---|---|
| Agent 1 | ALMOST READY | Good Step-Back and query fan-out, but coverage and time-anchor validation are insufficient. |
| Agent 2 | PARTIALLY READY | Live BrightData works and most queries return docs, but relevance/content quality is uneven and dynamic routing failed. |
| Agent 3 | NOT READY FOR PIPELINE | Standalone works on a small sample, but graph integration is missing and SAFE fails open. |
| End-to-end Agent 1→3 pipeline | NOT READY | Agent 3/validation placeholders prevent real fact flow through LangGraph. |

Recommended next work order:
1. Wire Agent 3, `validate_facts()`, and `run_safe_verification()` into `graph.py`.
2. Add Agent 2 relevance filters: domain matching for `site:` queries, title/snippet target-entity matching, source-type/domain allowlists, and stale-page filtering.
3. Strengthen Agent 1 validation: require all 7 signals, require high-weight investor/news coverage per company or per priority company group, enforce time anchors, and reject stale years.
4. Make SAFE fail closed on LLM errors.