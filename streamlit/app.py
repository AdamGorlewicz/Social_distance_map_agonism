from io import BytesIO
from pathlib import Path
from threading import Lock
from zipfile import ZIP_DEFLATED, ZipFile

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from urllib.parse import quote

from agonism import (
    calculate_agonism,
    calculate_ranking,
    load_data,
    plot_agonism_matrix,
    plot_ranking_legend,
    plot_social_distance_matrix,
    plot_social_maps,
)


@st.cache_resource
def plot_lock():
    return Lock()


def png_bytes(fig):
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
    return buffer.getvalue()


def analyze(ranking_file, chasing_file):
    ranking, chasing = load_data(ranking_file, chasing_file)
    _, mean_rank = calculate_ranking(ranking, chasing)
    agonism = calculate_agonism(chasing)
    ranks = mean_rank.loc[mean_rank.index.isin(agonism.index)]
    if len(ranks) < 2:
        raise ValueError("At least two mice must appear in both files.")

    with plot_lock():
        figures_before = set(plt.get_fignums())
        try:
            maps, distance, power = plot_social_maps(agonism, ranks)
            figures = {
                "agonism_matrix.png": plot_agonism_matrix(agonism, ranks),
                "social_distance_matrix.png": plot_social_distance_matrix(distance, ranks),
                "mouse_color_legend.png": plot_ranking_legend(ranks),
            }
            figures.update(
                (map_filename(mouse), fig) for mouse, fig in zip(ranks.index, maps)
            )
            images = {name: png_bytes(fig) for name, fig in figures.items()}
        finally:
            for number in set(plt.get_fignums()) - figures_before:
                plt.close(number)

    archive = BytesIO()
    mice = sorted(ranks.index)
    with ZipFile(archive, "w", ZIP_DEFLATED) as results:
        for name, data in images.items():
            results.writestr(name, data)
        for name, matrix in (
            ("agonism.xlsx", agonism),
            ("social_distance.xlsx", distance),
            ("power.xlsx", power),
        ):
            workbook = BytesIO()
            matrix.reindex(index=mice, columns=mice).to_excel(
                workbook, index_label="Ego / Partner", engine="openpyxl"
            )
            results.writestr(name, workbook.getvalue())
    return ranks, images, archive.getvalue(), agonism, distance


def map_filename(mouse):
    return f"social_map_ego_{quote(str(mouse), safe='')}.png"


def main():
    st.set_page_config(page_title="Eco-HAB | Agonism Maps", layout="wide")
    st.title("Eco-HAB Social Maps")

    with st.sidebar:
        ranking = st.file_uploader("Ranking", type="csv", key="ranking")
        chasing = st.file_uploader("Chases", type="csv", key="chasing")

        use_example = st.button("Use example data")

    uploads_ready = ranking is not None and chasing is not None
    upload_ids = (ranking.file_id, chasing.file_id) if uploads_ready else None
    if st.session_state.get("upload_ids") != upload_ids:
        st.session_state.pop("analysis", None)
        st.session_state["upload_ids"] = upload_ids

    generate = uploads_ready and st.button("Generate maps", type="primary")
    if use_example or generate:
        st.session_state.pop("analysis", None)
        try:
            with st.spinner("Calculating matrices and generating maps…"):
                if use_example:
                    folder = Path(__file__).resolve().parent
                    ranking = folder / "ranking.csv"
                    chasing = folder / "chasings.csv"
                st.session_state.analysis = analyze(ranking, chasing)
                st.session_state.analysis_source = "Example data" if use_example else "Uploaded data"
        except FileNotFoundError:
            st.error("Place ranking.csv and chasings.csv next to app.py to use example data.")
        except (KeyError, ValueError, TypeError) as error:
            st.error(f"Check your CSV files. {error}")

    if "analysis" not in st.session_state:
        if not uploads_ready and not use_example:
            st.info("Upload files with ranking and chasings data or select 'Use example data'.")
        return

    st.caption(st.session_state.get("analysis_source", "Results"))
    ranks, images, archive, agonism, distance = st.session_state.analysis
    st.download_button(
        "Download results (ZIP)", archive, "results_agonism.zip", "application/zip"
    )
    ranking_tab, agonism_tab, maps_tab, distance_tab = st.tabs(
        ["Ranking", "Agonism", "Social Maps", "Social Distance"]
    )
    with ranking_tab:
        st.image(images["mouse_color_legend.png"], width=560)
        st.dataframe(ranks.to_frame())
    with agonism_tab:
        st.image(images["agonism_matrix.png"], width=560)
        st.dataframe(agonism.T.sort_index().sort_index(axis=1).round(3))
    with maps_tab:
        ego = st.selectbox("Focal mouse", ranks.index)
        st.image(images[map_filename(ego)], width=560)
    with distance_tab:
        st.image(images["social_distance_matrix.png"], width=560)
        st.dataframe(distance.T.sort_index().sort_index(axis=1).round(3))



if __name__ == "__main__":
    main()
