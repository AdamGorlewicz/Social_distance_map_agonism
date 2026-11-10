# Running the agonism app in Streamlit

## Local setup

From the directory containing the app files, run:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Streamlit Community Cloud

Add `app.py`, `requirements.txt` and `social_map_agonism.py` to the same directory in your GitHub repository. If a dependency file already exists, merge the dependencies into it. The included analysis module preserves the command-line entry point and shares its export code with the app.

Open [Streamlit Community Cloud](https://share.streamlit.io/), create an app from your GitHub repository and select the branch containing the files. Set the main file path to `app.py` for files in the repository root, or `streamlit-agonism/app.py` if you keep the package directory. Then deploy.

Upload `ranking.csv` and `chasings.csv` from the same Eco-HAB session in the browser. Generate the results, select a focal mouse to preview its map, and download the ZIP containing every map, the color legend and the three Excel workbooks. The repository does not need to contain your CSV files.
