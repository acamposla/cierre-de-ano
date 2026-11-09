"""Los gráficos del cierre, en matplotlib, con una sola paleta y sin ruido.

Una regla por tipo de gráfico, para no cansar al lector con barras:

- Cascada: solo para explicar una variación neta (de 2024 a 2025, qué suma y qué resta).
- Barras con etiqueta compuesta: variación por familia, con euros y clientes en la misma etiqueta
  y el cambio de margen en puntos junto al nombre.
- Treemap: el peso de cada familia (tamaño) y cómo ha cambiado su margen (color), sin ejes.
- Pesas: margen de 2024 frente a 2025 por familia.
- Paneles pequeños: la misma familia vista en cada canal, para ver dónde está el problema.
"""
from __future__ import annotations

import math
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

from cierre.metricas import etiqueta

TINTA, SUAVE, ACENTO, LINEA, FONDO = "#16161a", "#55555f", "#9a3412", "#dededa", "#fbfbf9"
VERDE = "#2f6f73"
plt.rcParams.update({
    "figure.facecolor": FONDO, "axes.facecolor": FONDO, "savefig.facecolor": FONDO,
    "axes.edgecolor": LINEA, "axes.labelcolor": SUAVE, "xtick.color": SUAVE,
    "ytick.color": SUAVE, "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
})


# Textos de los gráficos en los dos idiomas. Los nombres de familia y canal vienen en los datos.
TEXTOS = {
    "es": {
        "t_cascada": "De 2024 a 2025, por lo que hicieron los clientes",
        "t_familias": "Variación de ventas por familia",
        "t_treemap": "Peso de cada familia y cambio de su margen",
        "t_pesas": "Margen por familia, 2024 frente a 2025",
        "t_paneles": "Cada familia en cada canal: dónde está el problema",
        "t_canales": "Qué canal crece y a qué margen",
        "clientes": "clientes",
        "barra_color": "cambio del margen, en puntos",
        "x_pesas": "margen sobre ventas, % (gris: 2024 · color: 2025)",
        "margen": "margen",
        "x_canales": ("crecimiento de ventas 2025 frente a 2024, % (en color de alerta, los "
                      "canales por debajo del margen medio: {medio})"),
        "tramos": {},
    },
    "en": {
        "t_cascada": "From 2024 to 2025, by what customers did",
        "t_familias": "Change in sales by product family",
        "t_treemap": "Size of each family and change in its margin",
        "t_pesas": "Margin by family, 2024 against 2025",
        "t_paneles": "Each family in each channel: where the problem is",
        "t_canales": "Which channel grows, and at what margin",
        "clientes": "customers",
        "barra_color": "change in margin, percentage points",
        "x_pesas": "margin on sales, % (grey: 2024 · colour: 2025)",
        "margen": "margin",
        "x_canales": ("sales growth 2025 against 2024, % (in alert colour, channels below the "
                      "average margin: {medio})"),
        "tramos": {"Ventas 2024": "Sales 2024", "Clientes perdidos": "Lost customers",
                   "Siguen y compran menos": "Stay and buy less",
                   "Siguen y compran más": "Stay and buy more",
                   "Clientes nuevos": "New customers", "Ventas 2025": "Sales 2025"},
    },
}
_IDIOMA = "es"


def idioma(codigo: str) -> None:
    """Cambia el idioma de los textos de los gráficos ('es' o 'en')."""
    global _IDIOMA
    if codigo not in TEXTOS:
        raise ValueError(codigo)
    _IDIOMA = codigo


def _tx(clave: str):
    return TEXTOS[_IDIOMA][clave]


def _miles(x: float) -> str:
    s = f"{x / 1_000:,.0f}k€"
    return s.replace(",", ".") if _IDIOMA == "es" else s


def _num(x: float, fmt: str) -> str:
    s = format(x, fmt)
    return s.replace(".", ",") if _IDIOMA == "es" else s


def _pct(x: float) -> str:
    s = f"{x:.1%}"
    return s.replace(".", ",").replace("%", " %") if _IDIOMA == "es" else s


def _titulo(ax, texto: str) -> None:
    ax.set_title(texto, loc="left", fontsize=15, color=TINTA, weight="bold", pad=14)


def cascada(puente: pd.DataFrame, titulo: str | None = None):
    fig, ax = plt.subplots(figsize=(11, 5.2))
    acumulado = 0.0
    for i, fila in enumerate(puente.itertuples()):
        extremo = i in (0, len(puente) - 1)
        if extremo:
            base, alto, color = 0.0, fila.importe, SUAVE
            acumulado = fila.importe
        else:
            base = acumulado if fila.importe >= 0 else acumulado + fila.importe
            alto, color = abs(fila.importe), (VERDE if fila.importe >= 0 else ACENTO)
            acumulado += fila.importe
        ax.bar(i, alto, bottom=base, color=color, width=0.62)
        texto = _miles(fila.importe) if extremo else (
            f"{'+' if fila.importe >= 0 else ''}{_miles(fila.importe)}\n{int(fila.clientes)} {_tx('clientes')}")
        ax.text(i, base + alto + puente["importe"].abs().max() * 0.015, texto, ha="center",
                va="bottom", fontsize=10.5, color=TINTA)
    ax.set_xticks(range(len(puente)))
    nombres = [_tx("tramos").get(t, t) for t in puente["tramo"]]
    ax.set_xticklabels([t.replace(" y ", "\ny ").replace(" and ", "\nand ") for t in nombres],
                       fontsize=10.5)
    lo = puente["importe"].iloc[[0, -1]].min()
    ax.set_ylim(lo * 0.75, puente["importe"].max() * 1.12)
    ax.yaxis.set_major_formatter(lambda v, _: _miles(v))
    _titulo(ax, titulo or _tx("t_cascada"))
    fig.tight_layout()
    return fig


def barras_familia(var: pd.DataFrame, titulo: str | None = None):
    v = var.sort_values("var_ventas")
    fig, ax = plt.subplots(figsize=(11, 0.55 * len(v) + 1.5))
    colores = [VERDE if x >= 0 else ACENTO for x in v["var_ventas"]]
    ax.barh(range(len(v)), v["var_ventas"], color=colores, height=0.62)
    ax.axvline(0, color=LINEA, lw=1)
    rango = v["var_ventas"].abs().max()
    for i, f in enumerate(v.itertuples()):
        x = f.var_ventas + (rango * 0.02 if f.var_ventas >= 0 else -rango * 0.02)
        ax.text(x, i, etiqueta(f.var_ventas, f.var_clientes, _IDIOMA).replace("\n", " "),
                va="center", ha="left" if f.var_ventas >= 0 else "right", fontsize=9.5,
                color=TINTA)
    nombres = [f"{f.familia}  ({_num(f.var_pp, '+.1f')} pp)" for f in v.itertuples()]
    ax.set_yticks(range(len(v)))
    ax.set_yticklabels(nombres, fontsize=10.5)
    ax.set_xlim(-rango * 1.7, rango * 1.7)
    ax.xaxis.set_major_formatter(lambda x, _: _miles(x))
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    _titulo(ax, titulo or _tx("t_familias"))
    fig.tight_layout()
    return fig


# ---------- Treemap ----------

def _peor_ratio(fila: list[float], lado: float) -> float:
    s = sum(fila)
    return max(max(lado * lado * r / (s * s), (s * s) / (lado * lado * r)) for r in fila)


def squarify(valores: list[float], x: float, y: float, ancho: float, alto: float):
    """Rectángulos de área proporcional a cada valor (algoritmo squarified de Bruls et al.).

    Los valores deben venir de mayor a menor. Devuelve una lista de (x, y, ancho, alto).
    """
    total = sum(valores)
    areas = [v * ancho * alto / total for v in valores]
    rects: list[tuple[float, float, float, float]] = []
    while areas:
        lado = min(ancho, alto)
        fila = [areas.pop(0)]
        while areas and _peor_ratio(fila + [areas[0]], lado) <= _peor_ratio(fila, lado):
            fila.append(areas.pop(0))
        s = sum(fila)
        if ancho >= alto:  # columna a la izquierda
            w = s / alto
            yy = y
            for a in fila:
                rects.append((x, yy, w, a / w))
                yy += a / w
            x, ancho = x + w, ancho - w
        else:  # fila abajo
            h = s / ancho
            xx = x
            for a in fila:
                rects.append((xx, y, a / h, h))
                xx += a / h
            y, alto = y + h, alto - h
    return rects


def treemap(var: pd.DataFrame, titulo: str | None = None):
    v = var[var["ventas_2025"] > 0].sort_values("ventas_2025", ascending=False)
    rects = squarify(list(v["ventas_2025"]), 0, 0, 100, 60)
    lim = max(1.0, v["var_pp"].abs().max())
    norm = TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("m", [ACENTO, "#f3efe8", VERDE])
    fig, ax = plt.subplots(figsize=(11, 6.4))
    for (x, y, w, h), f in zip(rects, v.itertuples()):
        ax.add_patch(plt.Rectangle((x, y), w, h, fc=cmap(norm(f.var_pp)), ec=FONDO, lw=2))
        if w * h > 25:
            pp = f"{_num(f.var_pp, '+.1f')} pp"
            nombre = textwrap.fill(f.familia, width=max(8, int(w * 0.9)))
            oscuro = abs(norm(f.var_pp) - 0.5) > 0.3
            ax.text(x + 1, y + h - 1.2, f"{nombre}\n{_miles(f.ventas_2025)} · {pp}",
                    va="top", ha="left", fontsize=10 if w > 14 else 8.5,
                    color=FONDO if oscuro else TINTA)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    cb = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label(_tx("barra_color"), color=SUAVE)
    _titulo(ax, titulo or _tx("t_treemap"))
    fig.tight_layout()
    return fig


def pesas(var: pd.DataFrame, titulo: str | None = None):
    v = var.sort_values("pct_2025")
    fig, ax = plt.subplots(figsize=(11, 0.5 * len(v) + 1.5))
    for i, f in enumerate(v.itertuples()):
        color = VERDE if f.pct_2025 >= f.pct_2024 else ACENTO
        ax.plot([f.pct_2024 * 100, f.pct_2025 * 100], [i, i], color=color, lw=2.5)
        ax.scatter(f.pct_2024 * 100, i, color=LINEA, s=60, zorder=3, edgecolor=SUAVE)
        ax.scatter(f.pct_2025 * 100, i, color=color, s=70, zorder=3)
    ax.set_yticks(range(len(v)))
    ax.set_yticklabels(v["familia"], fontsize=10.5)
    ax.set_xlabel(_tx("x_pesas"))
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    _titulo(ax, titulo or _tx("t_pesas"))
    fig.tight_layout()
    return fig


def paneles(var_cruce: pd.DataFrame, familias: list[str], titulo: str | None = None):
    n = len(familias)
    cols = 2 if n > 1 else 1
    filas = math.ceil(n / cols)
    fig, axes = plt.subplots(filas, cols, figsize=(11, 3.1 * filas), squeeze=False)
    rango = var_cruce.loc[var_cruce["familia"].isin(familias), "var_ventas"].abs().max()
    for ax, fam in zip(axes.flat, familias):
        d = var_cruce[var_cruce["familia"] == fam].sort_values("var_ventas")
        y = np.arange(len(d))
        ax.barh(y, d["var_ventas"], color=[VERDE if x >= 0 else ACENTO for x in d["var_ventas"]],
                height=0.6)
        ax.axvline(0, color=LINEA, lw=1)
        for i, f in enumerate(d.itertuples()):
            off = rango * 0.03 * (1 if f.var_ventas >= 0 else -1)
            ax.text(f.var_ventas + off, i,
                    etiqueta(f.var_ventas, f.var_clientes, _IDIOMA).replace("\n", " "),
                    va="center", ha="left" if f.var_ventas >= 0 else "right", fontsize=8.5,
                    color=TINTA, clip_on=False)
        ax.set_yticks(y)
        ax.set_yticklabels(d["ramo"], fontsize=9.5)
        ax.set_xlim(-rango * 1.9, rango * 1.9)
        ax.xaxis.set_major_formatter(lambda x, _: _miles(x))
        ax.set_title(fam, loc="left", fontsize=12, color=TINTA, weight="bold")
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    fig.suptitle(titulo or _tx("t_paneles"), x=0.01, ha="left", fontsize=15, color=TINTA, weight="bold")
    fig.tight_layout()
    return fig


def canales(var_ramo: pd.DataFrame, titulo: str | None = None):
    v = var_ramo.assign(crec=var_ramo["ventas_2025"] / var_ramo["ventas_2024"] - 1)
    v = v.sort_values("crec")
    fig, ax = plt.subplots(figsize=(11, 0.75 * len(v) + 1.6))
    medio = v["margen_2025"].sum() / v["ventas_2025"].sum()
    colores = [ACENTO if p < medio else VERDE for p in v["pct_2025"]]
    ax.barh(range(len(v)), v["crec"] * 100, color=colores, height=0.6)
    for i, f in enumerate(v.itertuples()):
        crec = f"+{f.crec:.0%}".replace("%", " %") if _IDIOMA == "es" else f"+{f.crec:.0%}"
        txt = f"{crec} · {_tx('margen')} {_pct(f.pct_2025)} ({_num(f.var_pp, '+.1f')} pp)"
        ax.text(f.crec * 100 + 0.8, i, txt, va="center", fontsize=10, color=TINTA)
    ax.set_yticks(range(len(v)))
    ax.set_yticklabels(v["ramo"], fontsize=10.5)
    ax.set_xlim(0, v["crec"].max() * 100 * 1.6)
    ax.set_xlabel(_tx("x_canales").format(medio=_pct(medio)))
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    _titulo(ax, titulo or _tx("t_canales"))
    fig.tight_layout()
    return fig
