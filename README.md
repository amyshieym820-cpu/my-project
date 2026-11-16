# Film Green Book

Film Green Book is a Streamlit app for estimating the carbon footprint of art-department props and materials. It compares sourcing methods such as new online purchases, store purchases, second-hand items, rentals, and reuse.

## Files

- `App.py` — Streamlit user interface and app logic
- `factors.py` — emission factors and calculation functions
- `requirements.txt` — Python dependencies
- `.streamlit/config.toml` — app theme and server settings

## Run locally

Python 3.9 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate     # Windows

pip install -r requirements.txt
streamlit run App.py
```

## Deploy from GitHub with Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload `App.py`, `factors.py`, `requirements.txt`, `README.md`, and the `.streamlit/config.toml` file. Keep the `.streamlit` folder name.
3. Open [Streamlit Community Cloud](https://share.streamlit.io/).
4. Choose **Create app**, connect the repository, and select `App.py` as the main file.
5. Deploy. Streamlit will install packages from `requirements.txt`.

## Address and route lookup

The app can look up Korean addresses with OpenStreetMap Nominatim and request driving distances from the public OSRM demo service. These services require an internet connection and may apply usage limits. If lookup fails, enter the one-way distance manually.

## Calculation assumptions

The factors are simplified estimates, not a verified product life-cycle assessment. Edit the `CFG` dictionary in `factors.py` to adjust the assumptions for a production. Meal, water, and tree comparisons are illustrative equivalents.
