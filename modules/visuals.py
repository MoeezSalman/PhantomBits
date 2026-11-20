"""
Visual helpers for the Image Analysis and Performance Evaluation pages.

  lsb_planes(img)              -> {"Red","Green","Blue","All channels"} LSB images
  hidden_region_info(size, n)  -> where the hidden bytes sit (rows / % of image)
  plane_view(plane, length)    -> big, framed picture with a red circle on the data
  results_table(rows)          -> tidy DataFrame for "Results by fill level"
  rs_chart / chi_square_chart / psnr_chart / fill_chart -> Altair charts, axes labelled
"""

from __future__ import annotations
import math
import numpy as np
import pandas as pd
import altair as alt
from PIL import Image, ImageDraw, ImageFont

from utils.image_utils import image_to_array

HEADER_BYTES = 4          # 32-bit length header written before the payload


# --------------------------------------------------------------------------
# LSB planes (all channels)
# --------------------------------------------------------------------------
def lsb_planes(img: Image.Image) -> dict[str, Image.Image]:
    """One black/white picture per colour channel + a combined colour picture."""
    arr = image_to_array(img)
    bits = (arr & 1).astype(np.uint8) * 255
    planes = {}
    for i, name in enumerate(("Red", "Green", "Blue")):
        planes[name] = Image.fromarray(bits[:, :, i], mode="L").convert("RGB")
    planes["All channels"] = Image.fromarray(bits, mode="RGB")   # R,G,B bits as colour
    return planes


def hidden_region_info(size: tuple[int, int], length: int) -> dict:
    """Where PhantomBits wrote `length` payload bytes (3 bits per pixel, from pixel 0)."""
    w, h = size
    bits = (length + HEADER_BYTES) * 8
    pixels = math.ceil(bits / 3)
    return {
        "pixels": pixels,
        "full_rows": pixels // w,
        "last_row_pixels": pixels % w,
        "image_pct": 100.0 * pixels / (w * h),
        "bits": bits,
    }


# --------------------------------------------------------------------------
# Framed, readable picture with a circle on the hidden data
# --------------------------------------------------------------------------
def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def plane_view(plane: Image.Image, length: int | None = None,
               colour=(255, 60, 60), min_width: int = 900,
               min_aspect: float = 0.28, max_stretch: float = 8.0) -> Image.Image:
    """
    * enlarges small images with sharp pixels
    * stretches very wide, short banners so they look like a proper picture
    * draws a complete box (frame) around the whole image
    * draws a red circle (oval for long messages) on the rows holding the hidden data
    """
    base = plane.convert("RGB")
    w, h = base.size
    sx = max(1, min(6, min_width // w)) if w < min_width else 1
    sy = sx * min(max_stretch, max(1.0, min_aspect * w / h))
    nw, nh = w * sx, max(1, int(round(h * sy)))
    disp = base.resize((nw, nh), Image.NEAREST)

    line = max(4, nw // 150)
    margin = line * 3 + 8
    circle, short = None, False
    if length is not None:
        info = hidden_region_info((w, h), length)
        rows = info["full_rows"] + (1 if info["last_row_pixels"] else 0)
        band_w = w if info["full_rows"] > 0 else max(info["last_row_pixels"], 1)
        bw, bh = band_w * sx, max(rows, 1) * sy
        cx, cy = bw / 2, bh / 2
        short = bw < 0.35 * nw
        if short:                                   # short message -> true circle
            r = max(max(bw, bh) / 2 * 1.25, nw * 0.05)
            ax = ay = r
        else:                                       # long message -> oval round the strip
            ax, ay = bw / 2 * 1.05, max(bh / 2 * 3.4, nw * 0.06)
        circle = (cx - ax, cy - ay, cx + ax, cy + ay)

    x0, y0, x1, y1 = circle if circle else (0, 0, nw, nh)
    pl, pt = int(max(0, -x0)) + margin, int(max(0, -y0)) + margin
    pr, pb = int(max(0, x1 - nw)) + margin, int(max(0, y1 - nh)) + margin
    bg = (32, 36, 40)
    canvas = Image.new("RGB", (nw + pl + pr, nh + pt + pb), bg)
    canvas.paste(disp, (pl, pt))
    d = ImageDraw.Draw(canvas)

    f = max(2, nw // 400)
    d.rectangle([pl - f, pt - f, pl + nw + f - 1, pt + nh + f - 1],
                outline=(235, 240, 238), width=f)                 # the complete box

    if circle:
        d.ellipse([x0 + pl, y0 + pt, x1 + pl, y1 + pt], outline=colour, width=line)
        text = "Hidden data starts here" if short else "Hidden data (top rows)"
        font = _font(max(14, nw // 45))
        tb = d.textbbox((0, 0), text, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        tx, ty = x1 + pl + line * 2, (y0 + y1) / 2 + pt - th / 2
        if tx + tw + 10 > canvas.width:
            tx, ty = max(6, (x0 + x1) / 2 + pl - tw / 2), y1 + pt + line * 2
        if ty + th + 8 > canvas.height:
            tx, ty = 8, 6
        d.rectangle([tx - 5, ty - 3, tx + tw + 5, ty + th + 5], fill=bg)
        d.text((tx, ty), text, fill=colour, font=font)
    return canvas


# --------------------------------------------------------------------------
# Performance table
# --------------------------------------------------------------------------
def results_table(rows: list[dict]) -> pd.DataFrame:
    """Short column names + Yes/No so every column fits without sideways scrolling."""
    return pd.DataFrame({
        "Fill %": [round(r["fill_pct"]) for r in rows],
        "Payload (B)": [r["payload_bytes"] for r in rows],
        "PSNR (dB)": [round(r["psnr"], 2) for r in rows],
        "MSE": [round(r["mse"], 4) for r in rows],
        "SSIM": [round(r["ssim"], 4) for r in rows],
        "RS max %": [round(r["rs_rate_pct"], 1) for r in rows],
        "RS": ["Yes" if r["rs_detected"] else "No" for r in rows],
        "Header": ["Yes" if r["header_detected"] else "No" for r in rows],
    })


# --------------------------------------------------------------------------
# Charts (every axis labelled)
# --------------------------------------------------------------------------
def _base(df, x, y, xt, yt, title, **kw):
    return (alt.Chart(df)
            .mark_line(point=alt.OverlayMarkDef(filled=True, size=70), color="#0f766e", strokeWidth=3, **kw)
            .encode(x=alt.X(x, title=xt), y=alt.Y(y, title=yt),
                    tooltip=[alt.Tooltip(x, title=xt), alt.Tooltip(y, title=yt, format=".4f")])
            .properties(height=300).configure_view(strokeWidth=0))


RS_THRESHOLD = 0.30
_CHAN_COLOURS = {"Average": "#0f766e", "Red": "#dc2626", "Green": "#16a34a", "Blue": "#2563eb"}


def rs_chart(rs: dict, log_x: bool = False, threshold: float | None = RS_THRESHOLD) -> alt.Chart:
    """RS estimate vs how much of the image has been scanned (average + R,G,B),
    with the detection threshold drawn as a dashed amber line."""
    frac = [f * 100 for f in rs["fractions"]]
    df = pd.DataFrame({"Image scanned (%)": frac, "Average": rs["rates"]})
    for k, v in rs.get("channel_rates", {}).items():
        df[k] = v
    long = df.melt("Image scanned (%)", var_name="Channel", value_name="Rate")
    names = [c for c in _CHAN_COLOURS if c in long["Channel"].unique()]
    xs = alt.X("Image scanned (%):Q", title="Image scanned (%)",
               scale=alt.Scale(type="log" if log_x else "linear"))
    top = max(0.4, float(long["Rate"].max()) * 1.1)
    ys = alt.Y("Rate:Q", title="Estimated embedding rate (0 – 1)", scale=alt.Scale(domain=[0, min(top, 1.0)]))
    lines = (alt.Chart(long).mark_line(point=True)
             .encode(x=xs, y=ys,
                     color=alt.Color("Channel:N", title="Channel",
                                     scale=alt.Scale(domain=names, range=[_CHAN_COLOURS[n] for n in names]),
                                     legend=alt.Legend(orient="bottom", direction="horizontal")),
                     size=alt.condition(alt.datum.Channel == "Average", alt.value(3.5), alt.value(1.5)),
                     tooltip=["Channel", alt.Tooltip("Image scanned (%):Q", format=".2f"),
                              alt.Tooltip("Rate:Q", format=".4f")]))
    layers = [lines]
    if threshold is not None:
        rule_df = pd.DataFrame({"y": [threshold], "label": [f"Detection threshold ({threshold:.2f})"]})
        rule = alt.Chart(rule_df).mark_rule(color="#f59e0b", strokeDash=[6, 4], strokeWidth=2).encode(y="y:Q")
        layers.append(rule)
    return alt.layer(*layers).properties(height=340).configure_view(strokeWidth=0)


def chi_square_chart(chi: dict) -> alt.Chart:
    df = pd.DataFrame({"Image data scanned (%)": [f * 100 for f in chi["fractions"]],
                       "Chi-square p-value (1 = looks embedded)": chi["p_values"]})
    return _base(df, "Image data scanned (%):Q",
                 "Chi-square p-value (1 = looks embedded):Q",
                 "Image data scanned (%)", "Chi-square p-value (1 = looks embedded)",
                 "Chi-square attack")


def fill_chart(rows: list[dict], key: str = "psnr") -> alt.Chart:
    labels = {"psnr": "PSNR (dB)", "mse": "MSE", "ssim": "SSIM",
              "changed_pct": "Changed values (%)", "rs_rate_pct": "RS max rate (%)"}
    ylab = labels[key]
    df = pd.DataFrame({"Fill level (% of capacity)": [r["fill_pct"] for r in rows],
                       ylab: [r[key] for r in rows]})
    return _base(df, "Fill level (% of capacity):Q", f"{ylab}:Q",
                 "Fill level (% of capacity)", ylab, f"{ylab} vs fill level")


def psnr_chart(rows: list[dict]) -> alt.Chart:
    return fill_chart(rows, "psnr")