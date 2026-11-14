# Eco-HAB Agonism Social Maps

Streamlit app for generating agonism and social distance heatmaps, a ranking legend, and vector social maps from Eco-HAB CSV exports.

## Run locally

In the project directory, with Python 3.12:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Deploy on Streamlit Community Cloud

Upload `app.py`, `agonism.py`, `requirements.txt`, and this README to the same directory in your GitHub repository. In [Streamlit Community Cloud](https://share.streamlit.io/), select **Create app**, choose the repository and branch, and set the main file path to `app.py` (or its repository-relative path if the files are in a subdirectory). Select Python 3.12 in the advanced settings and deploy.

## Input and output

Upload two CSVs from the same recording session and click **Generate maps**.

| Export | Required columns |
| --- | --- |
| `ranking.csv` | `animal_id`, `day`, `hour`, `phase`, `mu` |
| `chasings.csv` | `chaser`, `chased`, `chasings`, `day`, `hour`, `phase`, `phase_count` |

At least two mice must appear in both datasets. Agonism is normalized to the cohort mean across directed non-self pairs. Power is the mean rank difference divided by the number of shared mice minus one. Social distance is the vector length from `(0, 0)` to `(agonism, power)`.

**Download results (ZIP)** downloads three Excel matrices and the PNG figures. No sample data are required in the GitHub repository.
