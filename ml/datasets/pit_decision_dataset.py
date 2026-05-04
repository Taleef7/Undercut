from typing import Tuple, List, Optional
import pandas as pd
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "undercut.db"

COMPOUND_HARDNESS_MAP = {
    "SOFT": 1, "MEDIUM": 2, "HARD": 3,
    "INTERMEDIATE": 4, "WET": 5,
    "C1": 1, "C2": 2, "C3": 3, "C4": 4, "C5": 5,
}


class PitDecisionDataset:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH

    def build(
        self,
        session_id: str = "2024_21_R",
        test_split: float = 0.2,
        random_seed: int = 42,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, List[str]]:
        """Build pit decision dataset from base tables.
        
        Returns: X_train, y_train, X_test, y_test, feature_names
        """
        conn = duckdb.connect(str(self.db_path))
        df = self._query_features(conn, session_id)
        conn.close()
        
        if df.empty:
            return pd.DataFrame(), pd.Series(), pd.DataFrame(), pd.Series(), []

        df = self._compute_position(df, session_id)
        df = self._engineer_features(df)
        df = self._compute_label(df, session_id)
        df = self._add_weather(df, session_id)
        df = self._add_track_status(df, session_id)
        df = self._add_session_info(df, session_id)

        feature_cols = [c for c in df.columns if c not in ("label", "driver_ref", "lap_number", "session_id")]
        df = df.dropna(subset=feature_cols, thresh=len(feature_cols) // 2)
        df = df.dropna(subset=["label"])

        X = df[feature_cols].copy()
        y = df["label"].astype(int)

        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_split, random_state=random_seed, stratify=y
        )
        return X_train, y_train, X_test, y_test, feature_cols

    def _query_features(self, conn, session_id: str) -> pd.DataFrame:
        return conn.execute("""
            SELECT 
                fl.session_id,
                fl.driver_ref,
                fl.lap_number,
                fl.lap_time_ms,
                fl.is_pit_out_lap,
                fl.lap_start_time,
                fs.tyre_compound_id AS stint_compound,
                fs.stint_number AS stint_number,
                fs.lap_start AS stint_lap_start,
                fs.lap_end AS stint_lap_end,
                fpi.lap_number AS pit_stop_lap,
                fpi.pit_duration_seconds
            FROM fact_lap fl
            LEFT JOIN fact_stint fs 
                ON fl.session_id = fs.session_id 
                AND fl.driver_ref = fs.driver_ref
                AND fl.lap_number BETWEEN fs.lap_start AND fs.lap_end
            LEFT JOIN fact_pit_stop fpi
                ON fl.session_id = fpi.session_id
                AND fl.driver_ref = fpi.driver_ref
                AND fl.lap_number = fpi.lap_number
            WHERE fl.session_id = ?
            ORDER BY fl.driver_ref, fl.lap_number
        """, [session_id]).fetchdf()

    def _compute_position(self, df: pd.DataFrame, session_id: str) -> pd.DataFrame:
        conn = duckdb.connect(str(self.db_path))
        
        drivers = sorted(df["driver_ref"].unique())
        total_laps = int(df["lap_number"].max())

        pit_data = conn.execute("""
            SELECT driver_ref, lap_number, pit_duration_seconds
            FROM fact_pit_stop
            WHERE session_id = ?
        """, [session_id]).fetchdf()
        conn.close()

        lap_time_lookup = df.set_index(["driver_ref", "lap_number"])["lap_time_ms"].to_dict()
        driver_has_lap = {d: {lap for lap in df[df["driver_ref"] == d]["lap_number"]} for d in drivers}
        pit_lookup = {}
        for _, row in pit_data.iterrows():
            pit_lookup[(str(row["driver_ref"]), int(row["lap_number"]))] = row["pit_duration_seconds"]

        positions = {}
        cum_times = {d: 0.0 for d in drivers}

        for lap in range(1, total_laps + 1):
            for d in drivers:
                lap_time = lap_time_lookup.get((d, lap))
                if lap_time is not None and pd.notna(lap_time):
                    cum_times[d] += lap_time
                pit_secs = pit_lookup.get((d, lap))
                if pit_secs is not None:
                    cum_times[d] += pit_secs * 1000

            lap_drivers = [(d, cum_times[d]) for d in drivers if lap in driver_has_lap[d]]
            lap_drivers.sort(key=lambda x: x[1])

            for pos, (d, _) in enumerate(lap_drivers, 1):
                positions[(d, lap)] = pos

        df["approx_position"] = df.apply(
            lambda r: positions.get((r["driver_ref"], r["lap_number"]), None), axis=1
        )
        return df

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        result_rows = []
        for driver in df["driver_ref"].unique():
            driver_df = df[df["driver_ref"] == driver].sort_values("lap_number")
            for _, row in driver_df.iterrows():
                stint_age = row["lap_number"] - row["stint_lap_start"] if pd.notna(row["stint_lap_start"]) else None
                compound = row["stint_compound"] if pd.notna(row["stint_compound"]) else None
                compound_hardness = COMPOUND_HARDNESS_MAP.get(compound, 0) if compound else 0
                is_wet = 1 if compound in ("INTERMEDIATE", "WET") else 0
                rolling = driver_df[
                    (driver_df["lap_number"] < row["lap_number"]) &
                    (driver_df["lap_number"] >= row["lap_number"] - 3)
                ]["lap_time_ms"]
                rolling_avg = rolling.mean() if len(rolling) >= 2 else None
                result_rows.append({
                    "session_id": row["session_id"],
                    "driver_ref": row["driver_ref"],
                    "lap_number": row["lap_number"],
                    "stint_age_laps": stint_age,
                    "compound_hardness": compound_hardness,
                    "is_wet_compound": is_wet,
                    "lap_time_ms": row["lap_time_ms"],
                    "rolling_3_lap_avg_ms": rolling_avg,
                    "is_pit_out_lap": 1 if row["is_pit_out_lap"] else 0,
                    "approx_position": row["approx_position"],
                })
        return pd.DataFrame(result_rows)

    def _compute_label(self, df: pd.DataFrame, session_id: str) -> pd.DataFrame:
        conn = duckdb.connect(str(self.db_path))
        pit_laps = conn.execute("""
            SELECT driver_ref, lap_number FROM fact_pit_stop WHERE session_id = ?
        """, [session_id]).fetchdf()
        conn.close()
        df["label"] = 0
        for _, pit_row in pit_laps.iterrows():
            mask = (
                (df["driver_ref"] == pit_row["driver_ref"]) &
                (df["lap_number"] >= pit_row["lap_number"] - 3) &
                (df["lap_number"] <= pit_row["lap_number"])
            )
            df.loc[mask, "label"] = 1
        return df

    def _add_weather(self, df: pd.DataFrame, session_id: str) -> pd.DataFrame:
        conn = duckdb.connect(str(self.db_path))
        lap_times = conn.execute("""
            SELECT lap_number, MIN(lap_start_time) AS start_time
            FROM fact_lap
            WHERE session_id = ? AND lap_start_time IS NOT NULL
            GROUP BY lap_number
        """, [session_id]).fetchdf()
        weather = conn.execute("""
            SELECT sample_time, air_temperature_c, track_temperature_c, rainfall_flag
            FROM fact_weather_sample
            WHERE session_id = ?
            ORDER BY sample_time
        """, [session_id]).fetchdf()
        conn.close()

        if weather.empty:
            df["rainfall_flag"] = 0
            df["air_temperature_c"] = None
            df["track_temperature_c"] = None
            return df

        lap_time_map = dict(zip(lap_times["lap_number"], lap_times["start_time"]))
        df["lap_time"] = pd.to_datetime(
            df["lap_number"].map(lambda n: lap_time_map.get(n, "2024-11-03T14:00:00")),
            format="ISO8601",
        )

        df["rainfall_flag"] = weather["rainfall_flag"].mode().iloc[0] if not weather["rainfall_flag"].empty else 0
        df["air_temperature_c"] = weather["air_temperature_c"].mean()
        df["track_temperature_c"] = weather["track_temperature_c"].mean()
        return df

    def _add_track_status(self, df: pd.DataFrame, session_id: str) -> pd.DataFrame:
        conn = duckdb.connect(str(self.db_path))
        events = conn.execute("""
            SELECT lap_number, flag FROM fact_race_control_event
            WHERE session_id = ? AND flag IN ('RED', 'YELLOW', 'SC', 'VSC')
            ORDER BY lap_number
        """, [session_id]).fetchdf()
        conn.close()

        red_laps = set()
        yellow_laps = set()
        if not events.empty:
            for _, ev in events.iterrows():
                if ev["flag"] == "RED":
                    red_laps.add(ev["lap_number"])
                elif ev["flag"] == "YELLOW":
                    yellow_laps.add(ev["lap_number"])

        df["red_flag"] = df["lap_number"].isin(red_laps).astype(int)
        df["yellow_flag"] = df["lap_number"].isin(yellow_laps).astype(int)
        return df

    def _add_session_info(self, df: pd.DataFrame, session_id: str) -> pd.DataFrame:
        conn = duckdb.connect(str(self.db_path))
        result = conn.execute("""
            SELECT MAX(laps_completed) FROM fact_session_result
            WHERE session_id = ?
        """, [session_id]).fetchone()
        total_laps = result[0] if result and result[0] else 69
        conn.close()
        df["laps_remaining"] = total_laps - df["lap_number"]
        return df
