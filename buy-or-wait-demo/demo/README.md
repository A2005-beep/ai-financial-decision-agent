# Buy or Wait? — AI Financial Decision Agent (Live Demo)

An interactive demo of a financial decision agent built for the **HackerRank
Orchestrate** hackathon (Sept 2026). Given a user's balance, recurring
expenses, pending payments, income schedule, and a natural-language request
("Can I afford this laptop?"), the agent decides whether they should pay in
full, pay partially, use installments, wait, or not proceed — and shows the
90-day cash-flow forecast behind that decision.

**[Live demo →](#)** *(add your deployed URL here once live)*

## How it works

1. **Reconstructs financial state** from raw transaction history — separating
   one-off events from recurring monthly/weekly patterns, reserving pending
   debits, and counting confirmed salary only on its settlement date.
2. **Fills in missing data** by resolving amounts referenced only in linked
   receipt/statement images.
3. **Simulates 90 days forward** to find the largest payment that never lets
   the balance drop below the user's required minimum.
4. **Chooses a plan** — full payment, partial payment, installments (matched
   to a supplied option), or wait — and explains the decision in terms of the
   actual forecasted numbers.

The engine is deterministic and fully explainable: every recommendation
traces back to a specific simulated balance, not a black-box score.

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy it (free, ~2 minutes)

This app has no API keys or external services — it's pure Python + pandas,
so it deploys anywhere that runs Streamlit:

1. Push this folder to a public GitHub repo (or a subfolder of one).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with
   GitHub, click **New app**, point it at this repo and `app.py`.
3. Click **Deploy**. You'll get a public `*.streamlit.app` URL in about a
   minute.

(Render, Railway, and Hugging Face Spaces all work too, if you'd rather host
it elsewhere.)

## Project structure

```
app.py              Streamlit demo UI
engine/              Core decision engine (cash-flow model, FX conversion,
                     message parsing, plan evaluation)
dataset/             Sample dataset (250 requests across 5 currencies)
requirements.txt
```
