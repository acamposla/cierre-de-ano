"""Ventas sintéticas de dos años de un distribuidor ficticio, con semilla fija.

Una fila por cliente y familia, con ventas netas y coste de cada año: la forma del fichero que
sale de un ERP cuando se pide "ventas y coste por cliente y familia, este año y el anterior".

El distribuidor vende iluminación, material eléctrico, hogar conectado y herramienta a cinco
canales (ramos). Las cifras son inventadas. Lo que no es casual es el tipo de historia que
esconden, porque es la que un cierre de año tiene que saber encontrar:

- La facturación crece, pero el margen cae: crecer no es crecer sano.
- Una familia vende lo mismo y deja menos margen: erosión de precio.
- Otra pierde clientes en un canal: fuga.
- Otra conserva a sus clientes, pero cada uno compra menos: menor consumo.
- Dos familias crecen con clientes nuevos y buen margen.
- Un canal crece deprisa con un margen más bajo y arrastra el porcentaje total.
- Una familia residual factura tan poco que solo mete ruido en los gráficos.

Uso: python -m cierre.datos <carpeta_salida>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SEMILLA = 2025
RAMOS = ("Ferretería", "Bricolaje", "Gran distribución", "Material eléctrico", "Online")
CLIENTES_POR_RAMO = {"Ferretería": 260, "Bricolaje": 40, "Gran distribución": 12,
                     "Material eléctrico": 140, "Online": 25}
# Tamaño medio de compra anual de un cliente por familia, en euros, según el ramo
ESCALA_RAMO = {"Ferretería": 1.0, "Bricolaje": 6.0, "Gran distribución": 14.0,
               "Material eléctrico": 1.6, "Online": 4.0}

# familia: (categoría, compra media, margen 2024, prob. de que un cliente la compre)
FAMILIAS = {
    "Bombillas": ("Iluminación", 2_400, 0.34, 0.85),
    "Tiras LED": ("Iluminación", 900, 0.38, 0.40),
    "Focos de exterior": ("Iluminación", 1_300, 0.36, 0.45),
    "Iluminación solar": ("Iluminación", 1_100, 0.40, 0.35),
    "Cables": ("Material eléctrico", 1_800, 0.24, 0.70),
    "Enchufes y regletas": ("Material eléctrico", 1_000, 0.30, 0.60),
    "Pilas": ("Material eléctrico", 1_400, 0.22, 0.75),
    "Cámaras": ("Hogar conectado", 1_200, 0.31, 0.30),
    "Sensores y enchufes inteligentes": ("Hogar conectado", 600, 0.35, 0.25),
    "Herramienta manual": ("Herramienta", 900, 0.33, 0.45),
    "Herramienta eléctrica": ("Herramienta", 1_600, 0.27, 0.30),
    "Varios": ("Herramienta", 2, 0.20, 0.25),
}

# Lo que pasa en 2025, por familia: (crecimiento de los que siguen, cambio de margen en puntos,
# probabilidad de que un cliente deje la familia, probabilidad de que un cliente que no la
# compraba la empiece)
CAMBIO_2025 = {
    "Bombillas": (1.02, -0.08, 0.04, 0.04),           # erosión de precio
    "Tiras LED": (1.04, -0.01, 0.06, 0.08),
    "Focos de exterior": (1.00, -0.01, 0.06, 0.04),   # fuga en Ferretería (ver abajo)
    "Iluminación solar": (1.12, 0.01, 0.04, 0.15),    # crece con clientes nuevos
    "Cables": (0.80, -0.01, 0.03, 0.02),              # menor consumo
    "Enchufes y regletas": (1.02, 0.00, 0.05, 0.06),
    "Pilas": (1.01, -0.02, 0.05, 0.05),
    "Cámaras": (1.15, 0.00, 0.05, 0.15),              # crece con clientes nuevos
    "Sensores y enchufes inteligentes": (1.08, 0.01, 0.06, 0.08),
    "Herramienta manual": (1.00, -0.01, 0.07, 0.05),
    "Herramienta eléctrica": (1.03, -0.02, 0.06, 0.06),
    "Varios": (1.00, 0.00, 0.10, 0.00),
}
FUGA = {("Focos de exterior", "Ferretería"): 0.45}  # prob. de que el cliente deje la familia
ONLINE = {"crecimiento": 1.15, "margen": -0.10, "nuevos": 0.35}
BAJA_CLIENTE = 0.06   # clientes de 2024 que no compran nada en 2025
ALTA_CLIENTE = 0.05   # clientes nuevos sobre los de 2024, fuera de Online
ATRACCION = {"Cámaras": 2.2, "Iluminación solar": 2.2, "Sensores y enchufes inteligentes": 2.0}


def generar(semilla: int = SEMILLA) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    filas = []
    n = 0

    def cliente_nuevo() -> str:
        nonlocal n
        n += 1
        return f"C{n:04d}"

    def margen(m24: float, dm: float, ramo: str) -> tuple[float, float]:
        ajuste = ONLINE["margen"] if ramo == "Online" else 0.0
        r24 = float(np.clip(m24 + rng.normal(0, 0.03), 0.05, 0.6))
        r25 = float(np.clip(r24 + dm + ajuste + rng.normal(0, 0.01), 0.02, 0.6))
        return r24, r25

    # Clientes de 2024. Algunos se pierden enteros; los que siguen pueden dejar una familia
    # (o, en el cruce de la fuga, dejarla con mucha más probabilidad) o empezar otra.
    for ramo in RAMOS:
        for _ in range(CLIENTES_POR_RAMO[ramo]):
            cliente = cliente_nuevo()
            tam = rng.lognormal(0, 0.6) * ESCALA_RAMO[ramo]
            se_va = rng.random() < BAJA_CLIENTE
            for familia, (cat, media, m24, p) in FAMILIAS.items():
                crec, dm, p_deja, p_empieza = CAMBIO_2025[familia]
                r24, r25 = margen(m24, dm, ramo)
                g = crec * (ONLINE["crecimiento"] if ramo == "Online" else 1.0)
                if rng.random() < p:
                    v24 = media * tam * rng.lognormal(0, 0.5)
                    deja = se_va or rng.random() < FUGA.get((familia, ramo), p_deja)
                    v25 = 0.0 if deja else v24 * g * rng.lognormal(0, 0.15)
                elif not se_va and rng.random() < p_empieza:
                    v24, v25 = 0.0, media * tam * rng.lognormal(0, 0.5) * g
                else:
                    continue
                filas.append((cliente, ramo, cat, familia, v24, v24 * (1 - r24),
                              v25, v25 * (1 - r25)))

    # Clientes nuevos en 2025: no compraron nada en 2024. Entran sobre todo por Online y por
    # las familias que crecen.
    for ramo in RAMOS:
        tasa = ONLINE["nuevos"] if ramo == "Online" else ALTA_CLIENTE
        for _ in range(round(CLIENTES_POR_RAMO[ramo] * tasa)):
            cliente = cliente_nuevo()
            tam = rng.lognormal(0, 0.6) * ESCALA_RAMO[ramo]
            for familia, (cat, media, m24, p) in FAMILIAS.items():
                if rng.random() > min(1.0, p * ATRACCION.get(familia, 1.0)):
                    continue
                _, dm, _, _ = CAMBIO_2025[familia]
                _, r25 = margen(m24, dm, ramo)
                v25 = media * tam * rng.lognormal(0, 0.5)
                filas.append((cliente, ramo, cat, familia, 0.0, 0.0, v25, v25 * (1 - r25)))

    df = pd.DataFrame(filas, columns=["cliente", "ramo", "categoria", "familia",
                                      "ventas_2024", "coste_2024", "ventas_2025", "coste_2025"])
    num = ["ventas_2024", "coste_2024", "ventas_2025", "coste_2025"]
    df[num] = df[num].round(2)
    return df


if __name__ == "__main__":
    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("datos")
    salida.mkdir(parents=True, exist_ok=True)
    df = generar()
    df.to_csv(salida / "ventas.csv", index=False)
    print(f"{salida / 'ventas.csv'}: {len(df):,} filas")
