from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from urllib.parse import quote
from zipfile import ZIP_DEFLATED, ZipFile

import matplotlib
import streamlit as st

matplotlib.use("Agg")

from social_map_agonism import export_results, load_session


@st.cache_resource
def plot_lock():
    return Lock()


def analyze(ranking_bytes, chasing_bytes, phase_limit, session_name):
    with TemporaryDirectory() as folder:
        work_dir = Path(folder)
        ranking = work_dir / "ranking.csv"
        chasing = work_dir / "chasings.csv"
        ranking.write_bytes(ranking_bytes)
        chasing.write_bytes(chasing_bytes)

        session = load_session(ranking, chasing, n_dark_phases=phase_limit)
        session["session"] = session_name
        output_dir = work_dir / "results"
        with plot_lock():
            export_results(session, output_dir, close_figures=True)

        archive = BytesIO()
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zip_file:
            for result in sorted(output_dir.iterdir()):
                zip_file.write(result, arcname=result.name)
        return session["mice"], archive.getvalue()


def main():
    st.set_page_config(page_title="Eco-HAB social distance map (agonism)")
    st.title("Eco-HAB social distance maps (agonism)")
    st.write("Upload the ranking and chasing CSV files from one recording session.")

    with st.form("analysis"):
        ranking = st.file_uploader("Ranking (.csv)", type="csv")
        chasing = st.file_uploader("Chasing (.csv)", type="csv")
        session_name = st.text_input("Session name", value="Eco-HAB session")
        phase_count = st.number_input(
            "Number of phases for analysis (0 = all)",
            min_value=0,
            value=0,
            step=1,
        )
        submitted = st.form_submit_button("Generate social maps")

    st.caption(
        "Both rankings and chase counts must contain dark-phase data only."
    )

    if submitted:
        st.session_state.pop("results", None)
        st.session_state.pop("focal_mouse", None)
        if ranking is None or chasing is None:
            st.error("Upload both CSV files.")
        else:
            try:
                with st.spinner("Generating maps and workbooks…"):
                    st.session_state["results"] = analyze(
                        ranking.getvalue(),
                        chasing.getvalue(),
                        int(phase_count) or None,
                        session_name.strip() or "Eco-HAB session",
                    )
            except (ValueError, TypeError, KeyError) as exc:
                st.error(f"Could not analyze the CSV files. {exc}")

    if "results" in st.session_state:
        mice, archive = st.session_state["results"]
        st.download_button(
            "Download all results (ZIP)",
            data=archive,
            file_name="agonism_results.zip",
            mime="application/zip",
        )
        ego = st.selectbox("Focal mouse", mice, key="focal_mouse")
        with ZipFile(BytesIO(archive)) as results:
            ego_id = quote(str(ego), safe="")
            legend_col, map_col = st.columns([2, 3])
            with legend_col:
                st.image(results.read("mouse_color_legend.png"))
            with map_col:
                st.image(results.read(f"social_map_ego_{ego_id}.png"))


if __name__ == "__main__":
    main()
