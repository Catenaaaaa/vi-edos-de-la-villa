# Viñedos de la Villa — Caja, stock y pedidos

Sistema de punto de venta en un solo archivo (`index.html`) para **Viñedos de la Villa**,
vinoteca de Villa Allende (Av. del Niágara 635) — vinos, espirituosas y más.

Creada por **Catena Webs**.

## Cómo se usa
Abrir `index.html` con Chrome/Edge. No necesita internet salvo para las tipografías
(si no hay conexión usa fuentes del sistema). Los datos se guardan en el navegador con la clave
`vinedosDeLaVillaDB_v1` (independiente del kiosco original `kioscoDB_v1`).

## Sectores
1. **Caja**: escáner, buscador, filtro por sector de la cava (Tintos, Blancos, Destilados…), ticket, cobro y vuelto.
2. **Cava · Productos**: alta/edición, lista de precios imprimible, cálculo de margen.
3. **Pedidos**: entrada de mercadería (suma stock).
4. **Depósito**: stock calculado, con alertas de reposición.
5. **Números**: vendido, comprado, ganancia bruta, ventas por sector, lo más vendido.
6. **Datos**: backup JSON, exportar CSV, datos de ejemplo, créditos.

## Lector de código de barras
Lectores USB en modo teclado (escriben el código + Enter). Se detecta la ráfaga en cualquier sector:
- Caja (o cualquier sector que no sea Cava/Pedidos): suma al ticket.
- Cava: si el código existe abre el producto; si no, lo precarga para darlo de alta.
- Pedidos: selecciona el producto.
- Código desconocido → botón "Darlo de alta". Pitido opcional (Datos).

## Origen
Basado en `~/kiosco.html` (Kiosco POS), que queda sin tocar como plantilla.

## Pendiente
- Cargar productos reales y precios de la vinoteca.
- Probar con el lector físico del local.
- Definir si se quieren medios de pago (efectivo / transferencia / tarjeta) y cierre de caja diario.
