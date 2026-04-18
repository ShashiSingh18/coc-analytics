# ⚔️ Clash of Clans — Player Analytics Dashboard

I've been playing Clash of Clans for years, and at some point I thought — why not actually analyze the game I keep coming back to? This project started as a personal challenge to apply data analysis on something I genuinely care about, and ended up becoming one of the more interesting projects I've worked on.

The idea was simple: pull real player and clan data from the official COC API, dump it into a database, and find patterns that the game itself never shows you.

**Live Demo → [coc-analytics.streamlit.app](https://coc-analytics.streamlit.app)**

---

## What the Dashboard Shows

**📈 Progression Analysis**
Which troops do players actually upgrade and which ones get ignored? Turns out pets and siege machines are consistently underupgraded across all TH levels — dark elixir is the real bottleneck.

**⚔️ War Performance**
Does hero completion actually matter in war? Spoiler: yes, but not as much as attack duration. The sweet spot is 100–140 seconds.

**⏱️ Attack Duration**
Longer attacks aren't always better. Under 60 seconds almost always means something went wrong.

**🏆 Clan Analysis**
Clan level is a surprisingly poor predictor of win rate. Ties dominate at high clan levels — matchmaking gets too precise at the elite tier.

**💀 Churn Risk**
43% of players fall into high or critical churn risk. Lower TH players churn the most — the early game experience needs work.

**🎯 Donation Behavior**
Elite donors have 10x higher trophies and 70% more war stars than inactive players. Donation activity is probably the best single proxy for player retention.

---

## Tech Stack

- **Data Collection** — COC Official API (Python, async requests)
- **Database** — MySQL (local) → Railway (cloud)
- **Analysis** — pandas, SQL window functions
- **Dashboard** — Streamlit + Plotly
- **Deployment** — Streamlit Community Cloud

---

## The Deployment Struggle (Real Talk)

Getting this live was honestly the hardest part — not the analysis, but the infrastructure.

The full `troop_levels` table alone was **630MB**. Both Aiven and Railway free tiers crashed during import — one with a server shutdown mid-import, the other with a "table is full" error. After a few failed attempts, the fix was to sample 10,000 players per TH level instead of all 64K, bringing the troop data down from 5M rows to ~800K. The dashboard patterns hold — aggregations don't change much with a representative sample.

If you're trying to do something similar: free tier cloud databases are fine for small projects but will struggle with anything above ~200MB. Plan for this early.

---

## Running Locally

```bash
git clone https://github.com/ShashiSingh18/coc-analytics.git
cd coc-analytics
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:
```toml
db_url = "your_mysql_connection_string"
```

```bash
streamlit run app.py
```

Note: you'll need your own database with the COC data schema. The live demo runs on a sampled dataset hosted on Railway.

---

## About

M.Sc. Digital Engineering student at OVGU Magdeburg. Background in statistics, ML, and data mining — looking to work in the data field. This project was a way to combine that with something I actually enjoy outside of university.

Feel free to reach out or open an issue if you have questions.
