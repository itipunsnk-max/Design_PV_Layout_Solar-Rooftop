# Solar Rooftop String & MPPT Design Assistant

Thai-first Streamlit app for preliminary Solar Rooftop string, MPPT and DC cable design.

## Architecture

- `calculation_engine.py` — pure calculation layer: voltage/current validation, MPPT grouping, DC cable calculation, QA/QC and PVsyst-preparation table.
- `streamlit_app.py` — friendly Thai interface, inputs, visual output and exports.
- `PROGRAM_GUIDE.md` — คู่มือรายละเอียดองค์ประกอบ จุด Config การแบ่งชุด Inverter และโครงสร้างสูตร

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy to Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. In Streamlit Community Cloud choose **Create app**.
3. Select the repository and set the main file to `streamlit_app.py`.
4. Deploy. Streamlit will install `requirements.txt` automatically.

## Engineering limits

This is an engineering-assistance tool. It must not replace latest official manufacturer datasheets, PVsyst, site-specific assessments, statutory requirements, or licensed-engineer approval. PAN/OND files and every field marked `REQUIRES VERIFICATION` must be checked before design issue.
