# Viñedos de la Villa — Caja, stock y pedidos

Sistema de punto de venta en un solo archivo (`public/index.html`) para **Viñedos de la Villa**,
vinoteca de Villa Allende (Av. del Niágara 635) — vinos, espirituosas y más.

Creada por **Catena Webs**.

## Cómo se usa
Abrir `public/index.html` con Chrome/Edge, o entrar a la versión publicada en Cloudflare Pages. No necesita internet salvo para las tipografías
(si no hay conexión usa fuentes del sistema). Los datos se guardan en el navegador con la clave
`vinedosDeLaVillaDB_v1` (independiente del kiosco original `kioscoDB_v1`).

## Publicación (Cloudflare Pages)
Repo conectado a Cloudflare Pages: rama `main`, sin comando de build, directorio de salida `public`.
Solo se publica la carpeta `public/` (las pruebas y el material del video no quedan en la web).
Cada `git push` a `main` actualiza la página.

## Pruebas
```
~/.venvs/playwright/bin/python -I tests/test_cobro.py    # cobro, stock, intentos de burlar la caja
~/.venvs/playwright/bin/python -I tests/test_medios.py   # medios de pago, mixto, venta suelta, Estadísticas
```

## Sectores
1. **Caja**: escáner, buscador, filtro por sector de la cava (Tintos, Blancos, Destilados…), ticket, medio de pago, cobro y vuelto.
2. **Cava · Productos**: alta/edición, lista de precios imprimible, cálculo de margen.
3. **Pedidos**: entrada de mercadería (suma stock).
4. **Depósito**: stock calculado, con alertas de reposición.
5. **Números**: vendido, comprado, ganancia bruta, ventas por sector, lo más vendido.
6. **Datos**: backup JSON, exportar CSV, datos de ejemplo, créditos.
7. **Estadísticas**: cómo te pagan. Período (Hoy / 7 días / 30 días / Todo), medio que más vendió, tarjeta por medio
   (total, cantidad de ventas, % y ticket promedio), barras comparativas y cierre de caja por día.

## Medios de pago
Efectivo (por defecto), Transferencia, Débito, Crédito, PedidosYa y **Mixto**.
- **Efectivo**: se anota con cuánto pagan y calcula el vuelto.
- **Transferencia / Débito / Crédito / PedidosYa**: se cobra el total justo, sin vuelto (se oculta "Paga con").
- **Mixto**: se anota cuánto entra por cada medio; lo que falta se cobra en efectivo (con vuelto sobre esa parte).
- La **calculadora** tiene los mismos botones, conectados con los de la Caja. "Usar en pago" pasa el monto.
- **Venta suelta** (desde la calculadora): registra una venta por un monto sin cargar productos, con un detalle opcional
  (por ejemplo un pedido de PedidosYa). No descuenta stock y no se cuenta en la ganancia bruta, porque no tiene costo.
  Pide un solo medio (no Mixto).
- Cada venta guarda `medio` (`efectivo`, `transferencia`, `debito`, `credito`, `pedidosya`, `mixto` o `sin`) y
  `pagos: [{medio, monto}]`, que suman el total (la parte en efectivo ya sin el vuelto).
- Las ventas registradas antes de esta función quedan como **Sin especificar**.
- "Últimas ventas" (Números) y el CSV de movimientos incluyen el medio y el detalle del pago.
- Colores fijos por medio (validados para daltonismo, siempre con el nombre al lado): efectivo verde, transferencia azul,
  débito naranja, crédito bordó, PedidosYa rosa.

## Lector de código de barras
Lectores USB en modo teclado. Sirve si terminan con Enter, con Tab o sin tecla final, y tolera lectores lentos (hasta 90 ms por tecla). Se detecta la ráfaga en cualquier sector:
- Caja (o cualquier sector que no sea Cava/Pedidos): suma al ticket.
- Cava: si el código existe abre el producto para editarlo.
- Pedidos: selecciona el producto.
- Código que no está cargado → abre directo el alta en Cava con el código puesto y busca nombre, sector y foto
  en Open Food Facts (base pública y gratuita, necesita internet). Al guardar vuelve a la Caja y lo suma al ticket
  (o vuelve a Pedidos y lo selecciona). Pitido opcional (Datos).

## Origen
Basado en `~/kiosco.html` (Kiosco POS), que queda sin tocar como plantilla.

## Pendiente
- Cargar productos reales (Datos → Importar productos desde Excel; hoy hay un catálogo simulado).
- Probar con el lector físico del local.
- Cierre de caja con arqueo (contar el efectivo y comparar con lo esperado). Hoy Estadísticas ya muestra el efectivo por día.
