"""Las cuentas del cierre: qué crece, qué deja margen y por qué cambia cada cosa.

Todas las funciones reciben la tabla de `cierre.datos` (una fila por cliente y familia, con ventas
y coste de los dos años) y devuelven tablas pequeñas, listas para un gráfico o un anexo.

Dos decisiones que atraviesan todo el informe:

- El margen en porcentaje de un grupo se calcula sobre sus totales (margen total / ventas
  totales), nunca como media de porcentajes de cliente: un cliente pequeño con un margen raro no
  puede mover la cifra de una familia.
- Cada variación de ventas va con su variación de clientes. Una familia que pierde 50.000 € y 12
  clientes tiene una fuga; una que pierde 50.000 € con los mismos clientes, un problema de
  consumo. El remedio es distinto, así que la etiqueta lleva las dos cifras.
"""
from __future__ import annotations

import pandas as pd

UMBRAL_RUIDO = 1_000.0  # euros: por debajo, una familia o un cruce no se pinta


def _con_margen(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["margen_2024"] = out["ventas_2024"] - out["coste_2024"]
    out["margen_2025"] = out["ventas_2025"] - out["coste_2025"]
    return out


def _pct(margen: pd.Series | float, ventas: pd.Series | float):
    if isinstance(ventas, pd.Series):
        return (margen / ventas).where(ventas != 0, 0.0)
    return margen / ventas if ventas else 0.0


def resumen(df: pd.DataFrame) -> dict:
    """Las cifras de la portada: ventas, margen, margen en % y clientes, de los dos años."""
    d = _con_margen(df)
    t = d[["ventas_2024", "ventas_2025", "margen_2024", "margen_2025"]].sum()
    c24 = d.loc[d["ventas_2024"] > 0.01, "cliente"].nunique()
    c25 = d.loc[d["ventas_2025"] > 0.01, "cliente"].nunique()
    return {
        "ventas_2024": t["ventas_2024"], "ventas_2025": t["ventas_2025"],
        "margen_2024": t["margen_2024"], "margen_2025": t["margen_2025"],
        "pct_2024": _pct(t["margen_2024"], t["ventas_2024"]),
        "pct_2025": _pct(t["margen_2025"], t["ventas_2025"]),
        "var_ventas": t["ventas_2025"] / t["ventas_2024"] - 1,
        "var_margen": t["margen_2025"] / t["margen_2024"] - 1,
        "clientes_2024": c24, "clientes_2025": c25,
    }


def variacion(df: pd.DataFrame, por: list[str] | str,
              umbral: float = UMBRAL_RUIDO) -> pd.DataFrame:
    """Variación de ventas, margen y clientes por grupo, con el margen en puntos.

    Los grupos cuyas ventas no llegan al umbral en ninguno de los dos años se quitan: en un
    informe para dirección solo meten ruido. `ruido` dice cuánto se ha quitado.
    """
    por = [por] if isinstance(por, str) else list(por)
    d = _con_margen(df)
    g = d.groupby(por).agg(
        ventas_2024=("ventas_2024", "sum"), ventas_2025=("ventas_2025", "sum"),
        margen_2024=("margen_2024", "sum"), margen_2025=("margen_2025", "sum"),
    )
    g["clientes_2024"] = d[d["ventas_2024"] > 0.01].groupby(por)["cliente"].nunique()
    g["clientes_2025"] = d[d["ventas_2025"] > 0.01].groupby(por)["cliente"].nunique()
    g[["clientes_2024", "clientes_2025"]] = g[["clientes_2024", "clientes_2025"]].fillna(0)
    g = g.astype({"clientes_2024": int, "clientes_2025": int})
    g["var_ventas"] = g["ventas_2025"] - g["ventas_2024"]
    g["var_margen"] = g["margen_2025"] - g["margen_2024"]
    g["var_clientes"] = g["clientes_2025"] - g["clientes_2024"]
    g["pct_2024"] = _pct(g["margen_2024"], g["ventas_2024"])
    g["pct_2025"] = _pct(g["margen_2025"], g["ventas_2025"])
    g["var_pp"] = (g["pct_2025"] - g["pct_2024"]) * 100
    relevante = (g["ventas_2024"] >= umbral) | (g["ventas_2025"] >= umbral)
    g.attrs["ruido"] = g.loc[~relevante, "ventas_2025"].sum()
    return g[relevante].reset_index()


def puente_clientes(df: pd.DataFrame) -> pd.DataFrame:
    """De las ventas de 2024 a las de 2025, por lo que hicieron los clientes.

    Cuatro tramos, que suman exactamente la variación total:
    clientes perdidos (compraron en 2024 y no en 2025), clientes nuevos (al revés), y los que
    siguen, separados entre los que compran más y los que compran menos.
    """
    c = df.groupby("cliente")[["ventas_2024", "ventas_2025"]].sum()
    perdidos = c["ventas_2024"].where((c["ventas_2025"] <= 0.01) & (c["ventas_2024"] > 0.01), 0)
    nuevos = c["ventas_2025"].where((c["ventas_2024"] <= 0.01) & (c["ventas_2025"] > 0.01), 0)
    siguen = (c["ventas_2024"] > 0.01) & (c["ventas_2025"] > 0.01)
    delta = (c["ventas_2025"] - c["ventas_2024"]).where(siguen, 0)
    tramos = [
        ("Ventas 2024", c["ventas_2024"].sum(), None),
        ("Clientes perdidos", -perdidos.sum(), int((perdidos > 0).sum())),
        ("Siguen y compran menos", delta[delta < 0].sum(), int((delta < 0).sum())),
        ("Siguen y compran más", delta[delta > 0].sum(), int((delta > 0).sum())),
        ("Clientes nuevos", nuevos.sum(), int((nuevos > 0).sum())),
        ("Ventas 2025", c["ventas_2025"].sum(), None),
    ]
    return pd.DataFrame(tramos, columns=["tramo", "importe", "clientes"])


def etiqueta(var_eur: float, var_clientes: int, idioma: str = "es") -> str:
    """'-50k€\\n(-12 clientes)': la variación en euros y en clientes, en una sola etiqueta."""
    signo = "+" if var_eur >= 0 else "-"
    miles = f"{abs(var_eur) / 1_000:,.0f}"
    importe = f"{signo}{miles.replace(',', '.') if idioma == 'es' else miles}k€"
    sc = "+" if var_clientes > 0 else ""
    palabra = "clientes" if idioma == "es" else "customers"
    return f"{importe}\n({sc}{var_clientes} {palabra})"


def tabla_markdown(df: pd.DataFrame) -> str:
    """Una tabla Markdown sin dependencias, para los anexos del informe."""
    cab = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    filas = ["| " + " | ".join(map(str, fila)) + " |" for fila in df.itertuples(index=False)]
    return "\n".join([cab, sep, *filas])
