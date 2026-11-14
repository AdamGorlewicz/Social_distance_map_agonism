from io import BytesIO
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
    return ranks, images, archive.getvalue()


def map_filename(mouse):
    return f"social_map_ego_{quote(str(mouse), safe='')}.png"


def main():
    st.set_page_config(page_title="Eco-HAB | Agonism Maps", layout="wide")
    st.title("Eco-HAB Social Maps")
    st.caption("Agonism · Ranking · Social Distance")

    with st.sidebar:
        ranking = st.file_uploader("Ranking", type="csv", key="ranking")
        chasing = st.file_uploader("Chases", type="csv", key="chasing")

    if ranking is None or chasing is None:
        st.session_state.pop("analysis", None)
        st.info("Upload ranking.csv and chasings.csv to begin.")
        return

    inputs = (ranking.file_id, chasing.file_id)
    if st.session_state.get("analysis_inputs") != inputs:
        st.session_state.pop("analysis", None)
    if st.button("Generate maps", type="primary"):
        st.session_state.pop("analysis", None)
        try:
            with st.spinner("Calculating matrices and generating maps…"):
                st.session_state.analysis = analyze(ranking, chasing)
                st.session_state.analysis_inputs = inputs
        except (KeyError, ValueError, TypeError) as error:
            st.error(f"Check your CSV files. {error}")

    if "analysis" not in st.session_state:
        return

    ranks, images, archive = st.session_state.analysis
    st.download_button(
        "Download results (ZIP)", archive, "results_agonism.zip", "application/zip"
    )
    matrices, maps, legend = st.tabs(["Matrices", "Social Maps", "Ranking"])
    with matrices:
        left, right = st.columns(2)
        left.image(images["agonism_matrix.png"], caption="Agonism")
        right.image(images["social_distance_matrix.png"], caption="Social Distance")
    with maps:
        ego = st.selectbox("Focal mouse", ranks.index)
        st.image(images[map_filename(ego)], width=560)
    with legend:
        st.image(images["mouse_color_legend.png"], width=560)
        st.dataframe(ranks.to_frame())


if __name__ == "__main__":
    main()
