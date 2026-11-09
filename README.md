# Cierre de año: ¿crecemos sano y dónde se pierde el margen?

Un informe de cierre para dirección, rehecho sobre datos sintéticos. La pregunta es la que hace un
comité cuando las ventas suben: **¿estamos creciendo de forma sana? Y si no, ¿dónde se pierde el
margen: en el precio, en los clientes o en el canal?**

El caso contado, con el contexto:
[Dónde se pierde el margen cuando las ventas crecen](https://alejandrocamposlamas.com/portfolio/donde-se-pierde-el-margen/).
El informe completo, generado con este repo:
[cierre.html](https://alejandrocamposlamas.com/assets/docs/informe-cierre.html).
Sale del cierre de 2025 que preparé para el director general y el comité de Imprex sobre Garza,
la marca que dirigía. Aquel se hizo en R; este es el mismo método en Python, sin un solo dato
real.

> **English summary.** A year-end report for a leadership team, rebuilt on synthetic data. It
> answers "are we growing healthily, and if not, is the margin leaking through price, customers or
> channel?" with five charts: a customer bridge (lost, new, buying more, buying less), sales change
> by family with composite labels (euros and customers in one label, margin change in points next
> to the name), a treemap sized by sales and coloured by margin change, a margin dumbbell, and
> small multiples of each family by channel. Tables go to the appendix. Tests check the maths and
> that every claim in the report holds in the data. Code, report and docs are in Spanish; the
> charts can be exported in English.

## Los datos son sintéticos

`cierre/datos.py` genera con semilla fija las ventas y el coste de dos años de un distribuidor
ficticio que vende iluminación, material eléctrico, hogar conectado y herramienta a cinco canales.
Una fila por cliente y familia, que es la forma del fichero que sale de un ERP cuando se pide
"ventas y coste por cliente y familia, este año y el anterior".

Las cifras son inventadas. Las historias que esconden, no: son las que un cierre tiene que saber
encontrar. Las ventas crecen y el margen cae; una familia vende más y deja menos margen (precio);
otra pierde clientes en un canal (fuga); otra conserva a sus clientes, pero cada uno compra menos
(consumo); dos crecen con clientes nuevos; un canal crece deprisa con un margen bajo y arrastra el
total; y una familia residual factura tan poco que solo mete ruido.

## Cómo está hecho

| Pieza | Fichero | Qué hace |
|---|---|---|
| Datos | `cierre/datos.py` | Ventas y coste por cliente y familia, 2024 y 2025, con semilla fija |
| Métricas | `cierre/metricas.py` | Resumen, variación por cualquier agrupación con clientes y margen en puntos, puente por clientes, etiqueta compuesta |
| Gráficos | `cierre/graficos.py` | Cascada, barras con etiqueta compuesta, treemap, pesas, paneles por familia y canal; en español o en inglés |
| Informe | `informe/cierre.qmd` | Quarto: la historia en gráficos y las tablas al final, en anexos |
| Figuras | `scripts/figuras.py` | Exporta los gráficos como PNG en cualquiera de los dos idiomas |

Decisiones que atraviesan el informe:

- **Primero la historia, después la auditoría.** El cuerpo solo lleva gráficos, cada uno bajo una
  pregunta de negocio. Las tablas van en los anexos, enlazadas desde un botón bajo cada gráfico.
- **Cada variación de ventas va con su variación de clientes.** "-50k€ (-12 clientes)" es una
  fuga; "-50k€ (0 clientes)" es un problema de consumo. Los remedios son distintos.
- **El margen de un grupo se calcula sobre sus totales**, nunca como media de porcentajes: un
  cliente pequeño con un margen raro no puede mover una familia.
- **Lo que no llega a 1.000 € no se pinta.** Una familia residual no aporta nada a dirección y
  quita sitio a lo que importa. El anexo dice cuánto se ha dejado fuera.
- **Una forma de gráfico por pregunta.** La cascada solo explica una variación neta; el treemap
  muestra peso y salud sin ejes; los paneles pequeños ven la misma familia en cada canal.
- **El treemap no usa librerías.** `squarify` en `cierre/graficos.py` implementa el algoritmo de
  Bruls, Huizing y van Wijk, con su test.

## Ejecutarlo

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                                   # 15 comprobaciones, en un segundo
quarto render informe/cierre.qmd         # el informe, en informe/cierre.html
python scripts/figuras.py figuras en     # los gráficos en PNG, en inglés
python -m cierre.datos datos/            # las ventas sintéticas en CSV
```

Para el informe hace falta [Quarto](https://quarto.org) y un kernel de Jupyter en el mismo entorno.

Los tests comprueban el cálculo del margen sobre totales, el recuento de clientes por año, el
filtro de ruido, que el puente por clientes suma exactamente la variación total, la etiqueta
compuesta y que el treemap reparte el área en proporción. Y comprueban que lo que el informe
afirma se sostiene en los datos: que crece en ventas y cae en margen, los tres diagnósticos por
familia, el canal que crece con poco margen y dónde está la fuga.

## Diferencias con el informe real

- El original se hizo en R con Quarto, `ggplot2` y `kableExtra`. Este es Python con Quarto y
  matplotlib.
- El original tenía una sección por categoría de producto, con sus objetivos para el año
  siguiente. Aquí hay una sola historia y una lista corta de lo que llevaría al comité.
- Las familias, los canales y las cifras son inventados.

## Licencia

MIT. Ver `LICENSE`.
