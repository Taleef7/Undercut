import pandas as pd


def validate_rows(df: pd.DataFrame, table_name: str) -> tuple[pd.DataFrame, list[str]]:
    warnings = []

    warnings.extend(check_not_null(df, ["source_system", "data_version"]))
    warnings.extend(check_record_hash_not_null(df))

    if table_name == "fact_lap":
        warnings.extend(check_not_null(df, ["session_id", "driver_ref", "lap_number"]))
        warnings.extend(check_lap_range(df, total_laps=100))
        warnings.extend(check_unique(df, ["session_id", "driver_ref", "lap_number"]))
    elif table_name == "fact_stint":
        warnings.extend(check_not_null(df, ["session_id", "driver_ref", "stint_number"]))
    elif table_name == "fact_pit_stop":
        warnings.extend(check_not_null(df, ["session_id", "driver_ref", "lap_number"]))
    elif "fact_weather" in table_name:
        warnings.extend(check_not_null(df, ["session_id", "sample_time"]))
    elif "fact_race_control" in table_name:
        warnings.extend(check_not_null(df, ["session_id", "event_time"]))
    elif "fact_session_result" in table_name:
        warnings.extend(check_not_null(df, ["session_id", "driver_ref", "position_order"]))

    bad_indices = set()
    for w in warnings:
        if "Row " in w:
            try:
                idx = int(w.split("Row ")[1].split(":")[0])
                bad_indices.add(idx)
            except (ValueError, IndexError):
                pass

    if bad_indices:
        clean = df.drop(index=[i for i in bad_indices if i < len(df)])
    else:
        clean = df
    return clean, warnings


def check_not_null(df: pd.DataFrame, columns: list[str]) -> list[str]:
    warnings = []
    for col in columns:
        if col not in df.columns:
            continue
        null_mask = df[col].isna()
        for idx in df.index[null_mask]:
            warnings.append(f"Row {idx}: {col} is null")
    return warnings


def check_unique(df: pd.DataFrame, columns: list[str]) -> list[str]:
    warnings = []
    existing_cols = [c for c in columns if c in df.columns]
    if not existing_cols:
        return warnings
    duplicates = df[df.duplicated(subset=existing_cols, keep="first")]
    for idx in duplicates.index:
        vals = ", ".join(f"{c}={df.loc[idx, c]}" for c in existing_cols)
        warnings.append(f"Row {idx}: duplicate ({vals})")
    return warnings


def check_lap_range(df: pd.DataFrame, total_laps: int = 71) -> list[str]:
    warnings = []
    if "lap_number" not in df.columns:
        return warnings
    for idx in df.index:
        lap = df.loc[idx, "lap_number"]
        if pd.isna(lap):
            continue
        lap = int(lap)
        if lap < 1 or lap > total_laps:
            warnings.append(f"Row {idx}: lap_number {lap} out of range [1, {total_laps}]")
    return warnings


def check_record_hash_not_null(df: pd.DataFrame) -> list[str]:
    if "record_hash" not in df.columns:
        return []
    return check_not_null(df, ["record_hash"])


def check_fk_exists(df: pd.DataFrame, col: str, fk_table: str,
                    fk_col: str, db_path) -> list[str]:
    import duckdb
    ALLOWED_TABLES = {
        "dim_driver", "dim_constructor", "dim_circuit", "dim_tyre_compound",
        "dim_season", "dim_meeting", "dim_session", "dim_track_status_code",
        "fact_lap", "fact_stint", "fact_pit_stop", "fact_session_result",
        "fact_driver_session_entry", "fact_weather_sample", "fact_race_control_event",
        "fact_interval_sample", "fact_position_sample",
        "race_state_driver_lap_fact", "race_state_field_lap",
    }
    ALLOWED_COLS = {
        "driver_id", "driver_ref", "constructor_id", "circuit_id",
        "tyre_compound_id", "session_id", "lap_number", "stint_number",
    }
    if fk_table not in ALLOWED_TABLES:
        raise ValueError(f"Table '{fk_table}' not in allowlist")
    if fk_col not in ALLOWED_COLS:
        raise ValueError(f"Column '{fk_col}' not in allowlist")

    warnings = []
    conn = duckdb.connect(str(db_path))
    valid_keys = set(
        row[0] for row in conn.execute(
            f'SELECT "{fk_col}" FROM "{fk_table}"'
        ).fetchall()
    )
    conn.close()
    for idx in df.index:
        val = df.loc[idx, col]
        if pd.notna(val) and val not in valid_keys:
            warnings.append(
                f"Row {idx}: {col}={val} not found in {fk_table}.{fk_col}"
            )
    return warnings