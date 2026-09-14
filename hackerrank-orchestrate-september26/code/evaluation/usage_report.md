# Final full-dataset usage report

The final run that generated `output.csv` used the local deterministic Python
forecasting pipeline in `code/main.py` for all 250 evaluation requests.

| Metric | Value |
| --- | ---: |
| Model providers and names | None (deterministic rules engine) |
| Model calls | 0 |
| Input tokens | 0 |
| Output tokens | 0 |
| Total tokens | 0 |
| Average tokens per request | 0 |
| Estimated total model cost | $0.00 |
| Estimated model cost per request | $0.00 |

The pipeline reads only the participant-facing CSV files and supplied image
amount mapping. It uses no remote model, API, credentials, or live financial
data.
