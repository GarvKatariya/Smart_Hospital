# Bed occupancy forecast

The forecasting model is a one-layer LSTM trained from the derived daily aggregate in [`data/real/beds/hero_dmc_daily.csv`](../../data/real/beds/hero_dmc_daily.csv). The source is historical cardiology admissions at Hero DMC Heart Institute, Ludhiana. Its occupancy values are estimated from admission/discharge dates and are not normalized by staffed capacity. See [`data/real/beds/README.md`](../../data/real/beds/README.md) for provenance and limitations.

Training uses 30 days of admissions, discharges, and occupancy to forecast seven days. The data is split chronologically; the scaler is fitted on the training period only. Current held-out results are recorded in `artifacts/metrics.json`:

| Metric | LSTM | Persistence baseline |
| --- | ---: | ---: |
| Test MAE | 21.11 beds | 17.84 beds |
| Test RMSE | 29.92 beds | — |

On this holdout, the LSTM is less accurate than simply carrying forward the latest occupancy. Treat it as an experimental model, not a validated operational forecast. When the demo database has bed occupancy records, the backend scores its recent 30-day local window with this LSTM. The response and UI disclose that the model was trained on Hero DMC cardiology data and show the holdout comparison. With no local admission history, the backend returns a live-occupancy baseline instead. The Hero DMC series is never presented as the demo hospital's current census.

Rebuild and evaluate from the repository root:

```bash
python models/bed_forecasting/train.py
python models/bed_forecasting/evaluate.py
```
