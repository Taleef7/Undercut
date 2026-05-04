from typing import Tuple, List, Optional
import pandas as pd
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "undercut.db"

POSITION_BANDS = {
    "P1-P3": 3,
    "P4-P6": 6,
    "P7-P10": 10,
    "P11-P15": 15,
    "P16+": 25,
}

BAND_ORDER = ["P1-P3", "P4-P6", "P7-P10", "P11-P15", "P16+"]


class FinishPositionDataset:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH

    def build(
        self,
        session_id: str = "2024_21_R",
        test_split: float = 0.2,
        random_seed: int = 42,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, List[str]]:
        conn = duckdb.connect(str(self.db_path))

        final_positions = conn.execute("""
            SELECT driver_id, position_order
            FROM fact_session_result
            WHERE session_id = ?
        """, [session_id]).fetchdf()

        if final_positions.empty:
            conn.close()
            return pd.DataFrame(), pd.Series(), pd.DataFrame(), pd.Series(), []

        final_positions["final_position_band"] = final_positions["position_order"].apply(
            lambda p: self._position_to_band(p)
        )

        df = conn.execute("""
            SELECT
                fl.session_id,
                dd.driver_id,
                fl.lap_number,
                fl.lap_time_ms
            FROM fact_lap fl
            INNER JOIN dim_driver dd ON CAST(fl.driver_ref AS INTEGER) = dd.driver_number
            WHERE fl.session_id = ?
            ORDER BY dd.driver_id, fl.lap_number
        """, [session_id]).fetchdf()

        conn.close()

        df = df.merge(final_positions[["driver_id", "final_position_band", "position_order"]],
                      on="driver_id", how="left")

        df["laps_remaining"] = 69 - df["lap_number"]
        df["label"] = df["final_position_band"].map({b: i for i, b in enumerate(BAND_ORDER)})

        feature_cols = ["lap_number", "lap_time_ms", "laps_remaining"]
        df = df.dropna(subset=feature_cols)

        from sklearn.model_selection import train_test_split
        X = df[feature_cols]
        y = df["label"]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_split, random_state=random_seed
        )
        return X_train, y_train, X_test, y_test, feature_cols

    @staticmethod
    def _position_to_band(position: int) -> str:
        for band in BAND_ORDER:
            if position <= POSITION_BANDS[band]:
                return band
        return "P16+"

    @staticmethod
    def band_label_to_index(band: str) -> int:
        return BAND_ORDER.index(band) if band in BAND_ORDER else 4
