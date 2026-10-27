# Hero DMC Bed Occupancy Series

This daily aggregate is derived from the Kaggle **Hospital Admissions Data** dataset by Ashish Sahani. The source describes cardiology admissions at Hero DMC Heart Institute, Ludhiana, from April 2017 through March 2019. Source rows include patient-level identifiers and clinical fields; this project retains none of those rows or fields.

- Kaggle source: <https://www.kaggle.com/datasets/ashishsahani/hospital-admissions-data>
- Dataset author: Ashish Sahani
- Stated source: Hero DMC Heart Institute, Unit of Dayanand Medical College and Hospital
- Source license: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
- Derived data license: CC BY-NC-SA 4.0; attribution and share-alike terms are preserved.

`hero_dmc_daily.csv` contains only `date`, `admissions`, `discharges`, and `occupied_beds`. Occupancy is estimated by counting each admission from its admission date through its discharge date, inclusive; the Kaggle source has dates but no admission/discharge times or staffed-bed capacity. Admission dates are disambiguated using the source's `month year` field, and discharge dates are selected using the reported length of stay. Four inconsistent/unparseable source rows were excluded.

This is historical cardiology data from one hospital, not the current SmartHospital demo inventory and not a capacity-normalized series. It is used to train and evaluate the bed forecasting model. It should not be interpreted as current hospital status or clinical guidance.

The LSTM's chronological holdout MAE is about 21 beds, compared with about 18 beds for a persistence baseline. The trained model therefore does not currently outperform that simple baseline; see [`models/bed_forecasting/README.md`](../../../models/bed_forecasting/README.md) for the results and limitations.

To recreate the aggregate from Kaggle:

```bash
python3 scripts/import_kaggle_bed_occupancy.py
```
