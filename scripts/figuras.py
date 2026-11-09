"""Exporta los gráficos del informe como PNG, en español o en inglés.

Uso: python scripts/figuras.py <carpeta_salida> [es|en]
"""
from __future__ import annotations

import sys
from pathlib import Path

from cierre import graficos as g
from cierre import metricas as m
from cierre.datos import generar

NOMBRES_EN = {
    "Bombillas": "Bulbs", "Tiras LED": "LED strips", "Focos de exterior": "Outdoor floodlights",
    "Iluminación solar": "Solar lighting", "Cables": "Cables",
    "Enchufes y regletas": "Sockets and power strips", "Pilas": "Batteries",
    "Cámaras": "Cameras", "Sensores y enchufes inteligentes": "Sensors and smart plugs",
    "Herramienta manual": "Hand tools", "Herramienta eléctrica": "Power tools", "Varios": "Other",
    "Ferretería": "Hardware stores", "Bricolaje": "DIY chains", "Gran distribución": "Hypermarkets",
    "Material eléctrico": "Electrical wholesalers", "Online": "Online",
}
PANELES = ["Bombillas", "Focos de exterior", "Cables", "Iluminación solar"]


def main(salida: Path, idioma: str = "es") -> None:
    salida.mkdir(parents=True, exist_ok=True)
    g.idioma(idioma)
    ventas = generar()
    paneles = PANELES
    if idioma == "en":
        ventas = ventas.replace({"familia": NOMBRES_EN, "ramo": NOMBRES_EN})
        paneles = [NOMBRES_EN[p] for p in PANELES]
    fam = m.variacion(ventas, "familia")
    figuras = {
        "cascada": g.cascada(m.puente_clientes(ventas)),
        "familias": g.barras_familia(fam),
        "treemap": g.treemap(fam),
        "pesas": g.pesas(fam),
        "canales": g.canales(m.variacion(ventas, "ramo")),
        "paneles": g.paneles(m.variacion(ventas, ["familia", "ramo"]), paneles),
    }
    for nombre, fig in figuras.items():
        fig.savefig(salida / f"{nombre}.png", dpi=110)
    # Portada para tarjetas y redes: 1200 x 630
    portada = g.treemap(fam)
    portada.set_size_inches(12, 6.3)
    portada.savefig(salida / "portada.png", dpi=100)
    print(f"{len(figuras) + 1} figuras en {salida} ({idioma})")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("figuras"),
         sys.argv[2] if len(sys.argv) > 2 else "es")
