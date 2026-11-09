import pandas as pd
import pytest

from cierre import metricas as m
from cierre.datos import generar
from cierre.graficos import squarify


@pytest.fixture(scope="module")
def ventas():
    return generar()


def fila(cliente, familia, v24, c24, v25, c25, ramo="Ferretería"):
    return {"cliente": cliente, "ramo": ramo, "categoria": "X", "familia": familia,
            "ventas_2024": v24, "coste_2024": c24, "ventas_2025": v25, "coste_2025": c25}


# ---------- Datos ----------

def test_generador_reproducible():
    pd.testing.assert_frame_equal(generar(), generar())


def test_cada_fila_es_cliente_y_familia(ventas):
    assert not ventas.duplicated(["cliente", "familia"]).any()


# ---------- Métricas ----------

def test_margen_sobre_totales_no_media_de_porcentajes():
    df = pd.DataFrame([fila("A", "F", 1_000, 500, 1_000, 500),     # 50 %
                       fila("B", "F", 10, 9, 10, 9)])              # 10 %, casi no pesa
    v = m.variacion(df, "familia", umbral=0)
    assert v.loc[0, "pct_2024"] == pytest.approx(501 / 1_010)


def test_clientes_por_año_cuentan_solo_si_compran():
    df = pd.DataFrame([fila("A", "F", 100, 50, 0, 0), fila("B", "F", 0, 0, 100, 50),
                       fila("C", "F", 100, 50, 100, 50)])
    v = m.variacion(df, "familia", umbral=0).iloc[0]
    assert (v["clientes_2024"], v["clientes_2025"], v["var_clientes"]) == (2, 2, 0)


def test_umbral_quita_el_ruido():
    df = pd.DataFrame([fila("A", "Grande", 5_000, 3_000, 6_000, 3_500),
                       fila("A", "Mínima", 300, 200, 400, 250)])
    v = m.variacion(df, "familia")
    assert list(v["familia"]) == ["Grande"] and v.attrs["ruido"] == 400


def test_puente_suma_la_variacion_total(ventas):
    p = m.puente_clientes(ventas).set_index("tramo")["importe"]
    tramos = p.drop(["Ventas 2024", "Ventas 2025"]).sum()
    assert p["Ventas 2024"] + tramos == pytest.approx(p["Ventas 2025"])


def test_puente_separa_perdidos_nuevos_y_los_que_siguen():
    df = pd.DataFrame([fila("A", "F", 100, 0, 0, 0), fila("B", "F", 0, 0, 80, 0),
                       fila("C", "F", 100, 0, 130, 0), fila("D", "F", 100, 0, 60, 0)])
    p = m.puente_clientes(df).set_index("tramo")
    assert p.loc["Clientes perdidos", "importe"] == -100
    assert p.loc["Clientes nuevos", "importe"] == 80
    assert p.loc["Siguen y compran más", "importe"] == 30
    assert p.loc["Siguen y compran menos", "importe"] == -40


@pytest.mark.parametrize("eur, clientes, esperado", [
    (-50_000, -12, "-50k€\n(-12 clientes)"),
    (1_234_000, 3, "+1.234k€\n(+3 clientes)"),
    (0, 0, "+0k€\n(0 clientes)"),
])
def test_etiqueta_compuesta(eur, clientes, esperado):
    assert m.etiqueta(eur, clientes) == esperado


# ---------- Treemap ----------

def test_squarify_reparte_el_area_entera_en_proporcion():
    valores = [50, 25, 15, 10]
    rects = squarify(valores, 0, 0, 100, 60)
    areas = [w * h for _, _, w, h in rects]
    assert sum(areas) == pytest.approx(6_000)
    for a, v in zip(areas, valores):
        assert a == pytest.approx(6_000 * v / 100)
    for x, y, w, h in rects:
        assert x >= -1e-9 and y >= -1e-9 and x + w <= 100 + 1e-9 and y + h <= 60 + 1e-9


# ---------- Lo que dice el informe se sostiene en los datos ----------

def test_crece_en_ventas_y_cae_en_margen(ventas):
    r = m.resumen(ventas)
    assert r["var_ventas"] > 0 and r["var_margen"] < 0 and r["pct_2025"] < r["pct_2024"]


def test_los_tres_diagnosticos_por_familia(ventas):
    f = m.variacion(ventas, "familia").set_index("familia")
    focos, cables, bombillas = f.loc["Focos de exterior"], f.loc["Cables"], f.loc["Bombillas"]
    # Fuga: pierde clientes y poco dinero
    assert focos["var_clientes"] <= -20 and abs(focos["var_ventas"]) < 50_000
    # Menor consumo: pierde dinero sin perder clientes
    assert cables["var_ventas"] < -100_000 and cables["var_clientes"] >= 0
    # Precio: crece en ventas y es la que más margen pierde
    assert bombillas["var_ventas"] > 0 and bombillas["var_pp"] == f["var_pp"].min()
    assert bombillas["ventas_2025"] == f["ventas_2025"].max()


def test_un_canal_crece_mucho_mas_con_menos_margen(ventas):
    r = m.variacion(ventas, "ramo").set_index("ramo")
    crec = r["ventas_2025"] / r["ventas_2024"] - 1
    assert crec.idxmax() == "Online" and r["pct_2025"].idxmin() == "Online"
    assert crec["Online"] > 2 * crec.drop("Online").max()


def test_la_fuga_esta_en_un_canal_y_lo_solar_crece_en_todos(ventas):
    c = m.variacion(ventas, ["familia", "ramo"]).set_index(["familia", "ramo"])
    focos = c.loc["Focos de exterior"]["var_clientes"]
    assert focos.idxmin() == "Ferretería" and focos.drop("Ferretería").min() > -10
    solar = c.loc["Iluminación solar"]
    assert (solar["var_ventas"] > 0).all() and (solar["var_clientes"] > 0).all()
    assert m.variacion(ventas, "familia").set_index("familia").loc["Iluminación solar",
                                                                   "var_pp"] > -1.5
