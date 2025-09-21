"""Mapping helpers for Ageing Futures."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import pandas as pd
import pydeck as pdk

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_geojson(path: Path | None = None) -> Dict:
    geo_path = path or (CONFIG_DIR / "regions_uk.geojson")
    with geo_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def choropleth(df: pd.DataFrame, value_column: str, geojson: Dict | None = None) -> pdk.Deck:
    geojson = geojson or load_geojson()
    tooltip = {"html": "<b>{region}</b><br/>Value: {value}"}
    layer = pdk.Layer(
        "GeoJsonLayer",
        geojson,
        stroked=True,
        get_fill_color="[255 * value, 128, 160 - 120 * value]",
        get_line_color=[255, 255, 255],
        pickable=True,
    )
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=54.0, longitude=-2.0, zoom=4.5),
        tooltip=tooltip,
    )
    return deck


__all__ = ["load_geojson", "choropleth"]
