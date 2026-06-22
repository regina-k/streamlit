# Repository Guidelines

## Scope

This guide applies to the `streamlit/` app repository. Treat this folder as the runnable project root for UI, RAG, model inference, and app documentation work.

## Project Structure

- `app.py`: Streamlit UI and workflow orchestration.
- `config.py`: shared paths and constants.
- `modules/`: reusable app logic. Keep business logic here instead of burying it in UI code.
- `data/apartment/`: local KB apartment CSVs. Git ignored except `.gitkeep`.
- `data/additional/`: local school, station, and hospital location data. Git ignored except `.gitkeep`.
- `data/additional/preprocessed/`: normalized POI CSVs used when rebuilding integrated ML feature stores: `school.csv`, `station.csv`, and `hospital.csv`.
- `data/integration/`: local ML feature stores. Git ignored except `.gitkeep`.
- `data/rag_docs/`: RAG source documents. These are tracked.
- `vector_store/`: generated FAISS indexes. Never commit these files.
- `ml_model/`: ML configs, training code, model outputs, and experiment documentation.
- `docs/`: product docs and implementation status docs.

## Setup And Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

For RAG, `.env` must contain `OPENAI_API_KEY`, then run:

```powershell
python scripts\build_vectorstore.py
```

## Local Files Required

The app expects these local artifacts:

- `data/apartment/kb_apt_seoul_full.csv`
- `data/apartment/kb_timeseries_seoul.csv`
- `data/integration/apartment_multihorizon_ver9_latest_features.csv`
- `ml_model/outputs/models/ver16_service_multihorizon_base_model.pkl`

To regenerate or extend integrated ML features, also keep these POI files available:

- `data/additional/preprocessed/school.csv`
- `data/additional/preprocessed/station.csv`
- `data/additional/preprocessed/hospital.csv`

Do not commit `.env`, large data files, model binaries, generated predictions, logs, or FAISS files.

## Development Rules

- Preserve function contracts used by `app.py`, especially `predict_price_growth`, `get_loan_advice`, `filter_apartments`, and loan calculator helpers.
- Keep Streamlit display code in `app.py`; keep calculations, API calls, and model/RAG logic in `modules/`.
- Before changing ML behavior, read `ml_model/docs/model_version_performance_summary.md` and `ml_model/outputs/performance/VERSION_LOG.md`.
- Before changing feature engineering, read `data/additional/preprocessed/README.md`, `data/apartment/preprocessed/README.md`, and `data/integration/README.md`.
- Before changing product behavior, read `docs/prd_refined.md` and update `docs/feature_implementation_status.md`.

## Verification

Run these before handoff:

```powershell
python -m pip check
$files = @('app.py','config.py') + (Get-ChildItem modules -Filter *.py | ForEach-Object { $_.FullName }) + (Get-ChildItem scripts -Filter *.py | ForEach-Object { $_.FullName })
python -m py_compile @files
streamlit run app.py
```

If RAG changed, also rebuild FAISS with `python scripts\build_vectorstore.py` and confirm `vector_store/shinhan_faiss/` is still ignored by Git.
