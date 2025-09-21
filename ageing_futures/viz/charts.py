"""Plotly chart helpers."""
from __future__ import annotations

from typing import Dict, Iterable, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def time_series_chart(df: pd.DataFrame, metric: str, title: str, yaxis_title: str) -> go.Figure:
    fig = px.line(df, x="month", y=metric, markers=True, title=title)
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), yaxis_title=yaxis_title)
    fig.update_traces(hovertemplate="Month %{x}<br>%{y:.2f}")
    return fig


def multi_metric_chart(df: pd.DataFrame, metrics: Dict[str, str], title: str) -> go.Figure:
    fig = go.Figure()
    for metric, label in metrics.items():
        fig.add_trace(
            go.Scatter(
                x=df["month"],
                y=df[metric],
                mode="lines+markers",
                name=label,
            )
        )
    fig.update_layout(title=title, xaxis_title="Month", yaxis_title="Value")
    return fig


def leaderboard_bar(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df,
        x="team",
        y="total_score",
        color="total_score",
        text="rank",
        color_continuous_scale="Blues",
        title="Leaderboard",
    )
    fig.update_traces(texttemplate="#%{text}", textposition="outside")
    fig.update_layout(margin=dict(l=40, r=40, t=40, b=40))
    return fig


__all__ = ["time_series_chart", "multi_metric_chart", "leaderboard_bar"]
