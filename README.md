# Social maps of mice from agonistic interactions

This Python script analyzes one Eco-HAB recording session from two CSV exports. It draws a social map for each focal mouse (ego). Each partner's position represents relative chasing activity and the difference in hierarchical rank. The length of the vector from the focal mouse to its partner defines the social distance.

## Installation

Install the Python dependencies:

```bash
python -m pip install numpy pandas "matplotlib>=3.5" openpyxl
```

## Input data

Export both files from the same Eco-HAB session. The script expects comma-separated files with the following column headers.

| File | Required columns | Contents |
| --- | --- | --- |
| `ranking.csv` | `animal_id`, `day`, `hour`, `mu` | Mouse ID, recording day and hour, and ranking score |
| `chasings.csv` | `chaser`, `chased`, `chasings`, `day`, `hour`, `phase_count` | IDs of the chasing and chased mice, chase count, recording day and hour, and phase ID |

If `chasings.csv` has a `phase` column, the script uses only rows labeled `dark_phase` to match ranking records to phase IDs. Each matched `day` and `hour` combination must map to a single phase ID. Mouse IDs are read as text and must be consistent across the files. The analysis requires at least two mice present in both the phase-matched ranking and the chasing matrix.

## Running the script

Save the script as `social_map_agonism.py` and replace the local paths at the top of the file. This example uses paths relative to the repository root.

```python
RANKING_CSV = Path("data/ranking.csv")
CHASINGS_CSV = Path("data/chasings.csv")
OUTPUT_DIR = Path("results_agonism")
N_DARK_PHASES = None
SCORE_COL = "mu"
```

Run the following command from the repository root:

```bash
python social_map_agonism.py
```

If you keep the original filename, run `python "social_map_agonism(6).py"`. The script creates the output directory if needed and overwrites existing files with the same names. Use a separate `OUTPUT_DIR` for each session to keep its results.

With `N_DARK_PHASES = None`, each calculation uses all phase IDs available to it. A positive integer limits each calculation to that many phase IDs in ascending order. The ranking and chasing calculations select phase IDs independently. The chasing matrix includes all rows with the selected `phase_count` values regardless of their `phase` label. To restrict both calculations to dark phases, supply a `chasings.csv` containing only dark-phase records.

## Method

The script calculates the following quantities for each ordered pair of distinct mice. The index $i$ denotes the focal mouse and $j$ denotes its partner.

1. **Relative agonism.** Let $C_{ij}$ be the total number of chases initiated by $i$ toward $j$. Pairs with no recorded chases have a count of zero. The focal mouse's mean $\bar{C}_i$ includes all other mice in the analysis cohort, including partners with zero chases. For a positive mean, the script computes $c_{ij}=C_{ij}/\bar{C}_i$ and $A_{ij}=(c_{ij}-1)/(c_{ij}+1)$. A value of $-1$ indicates zero chases, $0$ indicates a count equal to the focal mouse's mean, and positive values indicate above-average counts.
2. **Relative power.** Within each matched phase, the script averages the available hourly $\mu$ scores for each mouse and ranks the means in descending order. The highest mean receives rank 1, and ties receive the average of the occupied ranks. The script then averages each mouse's available phase ranks to obtain $R_i$. Phase ranks are calculated before restricting the analysis to the shared cohort. For a cohort of $N$ mice, relative power is $P_{ij}=(R_i-R_j)/(N-1)$. A positive value indicates that the partner ranks higher on average than the focal mouse.
3. **Social distance.** The focal mouse is at $(0,0)$ and its partner is at $(A_{ij},P_{ij})$. The distance $D_{ij}=\sqrt{A_{ij}^2+P_{ij}^2}$ is dimensionless and can change when the focal mouse and partner swap roles. If the focal mouse's mean chase count is zero, its agonism and distance values are undefined.

## Output files

| File | Contents |
| --- | --- |
| `agonism.xlsx` | Relative agonism matrix |
| `power.xlsx` | Normalized rank difference matrix |
| `social_distance.xlsx` | Social distance matrix |
| `social_map_ego_<ID>.png` | One social map per focal mouse |
| `mouse_color_legend.png` | Shared legend linking mouse IDs to colors |

In each workbook, rows represent focal mice and columns represent partners. Diagonal cells and undefined values are blank. On each map, the horizontal axis (`Agonism`) shows relative agonism and the vertical axis (`Power`) shows the normalized rank difference. Both axes run from −1 to 1. If the mice included in the ranking differ from the final analysis cohort, normalized rank differences can fall outside the plotted range. The full values are available in `power.xlsx`.
