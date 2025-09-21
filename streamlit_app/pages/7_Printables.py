"""Generate printable policy and shock cards."""
from __future__ import annotations

import io
from typing import Iterable

import qrcode
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

from ageing_futures.sim.shocks import PREDEFINED_SHOCKS
from ageing_futures.sim.utils import load_config_bundle

st.set_page_config(page_title="Printables", layout="wide")

st.title("🖨️ Printables")
st.write("Download ready-to-print policy and shock cards with QR codes back to the app.")

bundle = load_config_bundle()
FONT = ImageFont.load_default()


def render_card(title: str, subtitle: str, body: str, url: str) -> bytes:
    width, height = 800, 480
    image = Image.new("RGB", (width, height), color=(240, 245, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width, 80], fill=(0, 79, 159))
    draw.text((30, 20), title, fill="white", font=FONT)
    draw.text((30, 100), subtitle, fill=(15, 23, 42), font=FONT)
    draw.multiline_text((30, 140), body, fill=(15, 23, 42), font=FONT, spacing=4)
    qr = qrcode.make(url).resize((160, 160))
    image.paste(qr, (width - 180, height - 200))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


st.subheader("Policy cards")
for policy in bundle.policies.policies:
    body = f"Cost per capita: £{policy.cost_per_capita:,.0f}\nEffects: " + ", ".join(
        f"{k}: {v:+.2f}" for k, v in policy.effects.items()
    )
    png_bytes = render_card(
        policy.name,
        "Policy lever",
        body,
        url="https://ageing-futures.streamlit.app/policies",
    )
    st.download_button(
        label=f"Download {policy.name}",
        data=png_bytes,
        file_name=f"policy_{policy.id}.png",
        mime="image/png",
    )

st.subheader("Shock cards")
for shock in PREDEFINED_SHOCKS.values():
    body = shock.description + "\nModifiers: " + ", ".join(
        f"{k}: {v:+.2f}" for k, v in shock.modifiers.items()
    )
    png_bytes = render_card(
        shock.name.title(),
        "Shock card",
        body,
        url="https://ageing-futures.streamlit.app/lecturer",
    )
    st.download_button(
        label=f"Download {shock.name.title()}",
        data=png_bytes,
        file_name=f"shock_{shock.name}.png",
        mime="image/png",
    )

st.caption("Cards use a simple palette optimised for quick tabletop printing.")
