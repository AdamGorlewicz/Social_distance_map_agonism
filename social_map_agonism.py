from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colormaps
from matplotlib.lines import Line2D
from urllib.parse import quote


# Input files for one session.
RANKING_CSV = Path(r"C:\Users\agorlewicz\Desktop\EcoHab\do chmury\example data\ranking.csv")
CHASINGS_CSV = Path(r"C:\Users\agorlewicz\Desktop\EcoHab\do chmury\example data\chasings.csv")

# Output directory for social maps.
OUTPUT_DIR = Path(r"C:\Users\agorlewicz\Desktop\EcoHab\do chmury\results_agonism")

# Analysis and plot settings.
N_DARK_PHASES = None  # Use a positive integer or None to include all phases.
SCORE_COL = "mu"
FONT_SIZE = 14


def select_phases(df, n_dark_phases):
    phases = sorted(df["_dark_phase_id"].unique())
    chosen = phases if n_dark_phases is None else phases[:n_dark_phases]
    return df[df["_dark_phase_id"].isin(chosen)].copy()


def prepare_ranking(ranking, chasing, chasing_file, score_col, n_dark_phases):
    phase_by_hour = chasing[["day", "hour", "phase_count"]].copy()
    for column in phase_by_hour.columns:
        phase_by_hour[column] = pd.to_numeric(
            phase_by_hour[column], errors="coerce"
        )

    if phase_by_hour.isna().any().any():
        raise ValueError(f"{chasing_file}: invalid day, hour, or phase_count values.")

    if "phase" in chasing.columns:
        phase_by_hour = phase_by_hour.loc[chasing["phase"].eq("dark_phase")]

    phase_by_hour = phase_by_hour.drop_duplicates().rename(
        columns={"phase_count": "_dark_phase_id"}
    )
    phase_by_hour = select_phases(phase_by_hour, n_dark_phases)

    ranking = ranking.merge(
        phase_by_hour, on=["day", "hour"], how="left", validate="many_to_one"
    )
    ranking = ranking.dropna(subset=["_dark_phase_id"])

    phase_values = (
        ranking.groupby(["_dark_phase_id", "animal_id"], as_index=False)[score_col]
        .mean()
    )
    scores_wide = phase_values.pivot(
        index="_dark_phase_id", columns="animal_id", values=score_col
    ).sort_index()

    ranks_wide = scores_wide.rank(axis=1, ascending=False, method="average")
    mean_rank = ranks_wide.mean(axis=0).rename("mean_rank")
    return ranks_wide, mean_rank


def prepare_chasing_matrix(chasing, chasing_file, n_dark_phases):
    df = chasing.copy()

    if df[["chaser", "chased"]].isna().any().any():
        raise ValueError(f"{chasing_file}: missing mouse IDs.")

    df["_dark_phase_id"] = pd.to_numeric(df["phase_count"], errors="coerce")
    df["chasings"] = pd.to_numeric(df["chasings"], errors="coerce")

    if df[["_dark_phase_id", "chasings"]].isna().any().any():
        raise ValueError(f"{chasing_file}: invalid phase_count or chasings values.")
    if (df["chasings"] < 0).any():
        raise ValueError(f"{chasing_file}: negative chase counts.")

    df = select_phases(df, n_dark_phases)
    mice = sorted(set(df["chaser"]) | set(df["chased"]))

    return (
        df.groupby(["chaser", "chased"])["chasings"]
        .sum()
        .unstack(level="chased")
        .reindex(index=mice, columns=mice)
        .fillna(0.0)
    )


def calculate_individual_agonism(chasing_matrix):
    matrix = chasing_matrix.astype(float)
    matrix_values = matrix.to_numpy(copy=True)
    np.fill_diagonal(matrix_values, np.nan)
    matrix = pd.DataFrame(
        matrix_values, index=matrix.index, columns=matrix.columns
    )

    ego_mean = matrix.mean(axis=1, skipna=True)
    c_matrix = matrix.div(ego_mean, axis=0)
    agonism = (c_matrix - 1) / (c_matrix + 1)
    return agonism, ego_mean, c_matrix


def load_session(
    ranking_file, chasing_file, score_col=SCORE_COL, n_dark_phases=N_DARK_PHASES
):
    ranking_file = Path(ranking_file)
    chasing_file = Path(chasing_file)

    folder_name = ranking_file.parent.name
    name = {
        "control-before": "Pre-surgery",
        "control-after": "Post-surgery",
    }.get(folder_name, folder_name)

    ranking = pd.read_csv(ranking_file, dtype={"animal_id": str})
    chasing = pd.read_csv(chasing_file, dtype={"chaser": str, "chased": str})

    ranks, mean_rank = prepare_ranking(
        ranking, chasing, chasing_file, score_col, n_dark_phases
    )
    chasing_matrix = prepare_chasing_matrix(chasing, chasing_file, n_dark_phases)

    mice = sorted(set(mean_rank.index) & set(chasing_matrix.index))
    if len(mice) < 2:
        raise ValueError(
            "Power calculation requires at least two mice present in both "
            "the ranking and the chasing matrix for this session."
        )

    mean_rank = mean_rank.reindex(mice)
    chasing_matrix = chasing_matrix.reindex(index=mice, columns=mice)
    agonism, ego_mean, c_matrix = calculate_individual_agonism(chasing_matrix)

    rank = mean_rank.to_numpy(dtype=float)
    power = (rank[:, None] - rank[None, :]) / (len(mice) - 1)
    power_matrix = pd.DataFrame(power, index=mice, columns=mice)

    vectors = []
    for ego in mice:
        for partner in mice:
            if ego == partner:
                continue

            x = float(agonism.loc[ego, partner])
            y = float(power_matrix.loc[ego, partner])
            vectors.append(
                {
                    "session": name,
                    "ego": ego,
                    "partner": partner,
                    "raw_chasing": chasing_matrix.loc[ego, partner],
                    "ego_mean_chasing": ego_mean.loc[ego],
                    "c": c_matrix.loc[ego, partner],
                    "agonism": x,
                    "power": y,
                    "distance": float(np.hypot(x, y)),
                }
            )

    return {
        "session": name,
        "mice": mice,
        "ranks": ranks,
        "mean_rank": mean_rank,
        "chasing_matrix": chasing_matrix,
        "agonism_matrix": agonism,
        "ego_mean_chasing": ego_mean,
        "c_matrix": c_matrix,
        "power_matrix": power_matrix,
        "vectors": pd.DataFrame(vectors),
    }


def plot_mouse_legend(mice, color_map):
    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markersize=9,
            markerfacecolor=color_map[mouse],
            markeredgecolor=color_map[mouse],
            label=mouse,
        )
        for mouse in mice
    ]

    fig, ax = plt.subplots(figsize=(5, max(2, 0.42 * len(mice) + 0.6)))
    ax.axis("off")
    ax.legend(handles=handles, loc="center", frameon=False, fontsize=FONT_SIZE)
    fig.tight_layout()
    return fig


def plot_social_map(session, ego, color_map):
    fig, ax = plt.subplots()
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.axhline(0, color="black", linewidth=0.8, zorder=1)
    ax.axvline(0, color="black", linewidth=0.8, zorder=1)
    ax.scatter(0, 0, s=65, color=color_map[ego], zorder=10, clip_on=False)
    ax.annotate(
        "Ego",
        xy=(0, 0),
        xytext=(6, 6),
        textcoords="offset points",
        fontsize=8,
        color="black",
    )

    for other in session["mice"]:
        if other == ego:
            continue

        agonism = session["agonism_matrix"].loc[ego, other]
        power = session["power_matrix"].loc[ego, other]
        ax.annotate(
            "",
            xy=(agonism, power),
            xytext=(0, 0),
            arrowprops={
                "arrowstyle": "->",
                "linewidth": 1.3,
                "color": color_map[other],
                "alpha": 0.85,
            },
            zorder=3,
        )
        ax.scatter(
            agonism, power, s=40, color=color_map[other], zorder=5, clip_on=False
        )

    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_aspect("equal", adjustable="box")

    ticks = np.linspace(-1, 1, 5)
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.tick_params(axis="both", labelsize=10, width=0.5, colors="black")
    ax.set_xlabel("Agonism", fontsize=10)
    ax.set_ylabel("Power", fontsize=10)
    ax.set_title(session["session"], y=1.10, fontsize=10)

    ax.grid(linestyle=":", linewidth=0.5, color="grey", alpha=0.9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#E8E8E8")
    ax.spines["bottom"].set_color("#E8E8E8")

    fig.tight_layout()
    return fig


def main():
    for input_file in (RANKING_CSV, CHASINGS_CSV):
        if not input_file.is_file():
            raise FileNotFoundError(f"Input CSV not found: {input_file}")

    session = load_session(RANKING_CSV, CHASINGS_CSV)
    mice = session["mice"]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Export matrices with ego IDs as rows and partner IDs as columns.
    agonism_matrix = session["agonism_matrix"].reindex(index=mice, columns=mice)
    distance_matrix = (
        session["vectors"]
        .pivot(index="ego", columns="partner", values="distance")
        .reindex(index=mice, columns=mice)
    )
    power_matrix = session["power_matrix"].reindex(index=mice, columns=mice)

    # Leave the diagonal blank in each workbook.
    diagonal = np.eye(len(mice), dtype=bool)

    for filename, matrix in (
        ("agonism.xlsx", agonism_matrix),
        ("social_distance.xlsx", distance_matrix),
        ("power.xlsx", power_matrix),
    ):
        output_file = OUTPUT_DIR / filename
        matrix.mask(diagonal).to_excel(
            output_file,
            index_label="Ego / Partner",
            na_rep="",
            engine="openpyxl",
        )

    # Use the same mouse colors in the legend and all social maps.
    cmap = colormaps.get_cmap("tab20")
    color_map = {
        mouse: cmap(i / (len(mice) - 1))
        for i, mouse in enumerate(mice)
    }

    legend_fig = plot_mouse_legend(mice, color_map)
    legend_file = OUTPUT_DIR / "mouse_color_legend.png"
    legend_fig.savefig(legend_file, dpi=300, bbox_inches="tight")

    for ego in mice:
        fig = plot_social_map(session, ego, color_map)

        # Encode characters that could be interpreted as path separators.
        ego_id = quote(str(ego), safe="")
        output_file = OUTPUT_DIR / f"social_map_ego_{ego_id}.png"

        fig.savefig(output_file, dpi=300, bbox_inches="tight")

    plt.show()


if __name__ == "__main__":
    main()