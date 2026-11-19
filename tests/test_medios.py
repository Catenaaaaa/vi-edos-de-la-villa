"""Pruebas de medios de pago, pago mixto, venta suelta y Estadísticas.
Uso: ~/.venvs/playwright/bin/python -I tests/test_medios.py
"""
import os, sys, json
from playwright.sync_api import sync_playwright

URL = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'public', 'index.html'))
OUT = os.environ.get('OUT', '/tmp')
RES = []

def check(nombre, ok, detalle=''):
    RES.append((nombre, bool(ok), detalle))
    print(('  OK   ' if ok else '  FALLA') + ' ' + nombre + (('  → ' + str(detalle)) if (detalle and not ok) else ''))

def reset(pg, movimientos='[]'):
    pg.goto(URL)
    pg.evaluate("localStorage.clear()")
    pg.goto(URL)
    pg.evaluate("""(mov)=>{
      const P=(id,codigo,nombre,cat,c,v,s)=>({id,codigo,nombre,categoria:cat,precioCosto:c,precioVenta:v,stockInicial:s,stockMinimo:0});
      DB={productos:[P('malbec','7790000000011','Malbec Reserva 750 ml','Tintos',6500,10000,20),
                     P('fernet','7790000000080','Fernet 750 ml','Destilados',9800,15000,20)],movimientos:JSON.parse(mov)};
      save(); DB=load(); carrito=[]; setMedio('efectivo'); renderAll();
    }""", movimientos)

def agregar(pg, *ids):
    for i in ids: pg.evaluate(f"agregarAlCarrito('{i}',1)")

def ventas(pg): return pg.evaluate("DB.movimientos.filter(m=>m.tipo==='venta')")
def ultima(pg): v = ventas(pg); return v[-1] if v else None
def guardado(pg): return pg.evaluate("JSON.parse(localStorage.getItem(KEY)||'{}')")
def medio(pg, m, donde='#mediosCaja'): pg.click(f'{donde} [data-medio="{m}"]')
def cobrar(pg):
    pg.click('#btnCobrar'); pg.wait_for_timeout(750)  # pasa la protección contra doble clic
    return pg.inner_text('#msgVenta')
def calc(pg, teclas):
    for t in teclas: pg.click(f'.keys [data-c="{t}"]')

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1366, 'height': 900})
    errs, dialogs = [], []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: (dialogs.append(d.message), d.accept()))

    print('\n== Botones de medio ==')
    reset(pg)
    check('Hay 6 opciones en la Caja (5 medios + Mixto)', pg.locator('#mediosCaja [data-medio]').count() == 6)
    check('Efectivo marcado por defecto', pg.get_attribute('#mediosCaja [data-medio="efectivo"]', 'class').endswith('on'))
    pg.click('details.calcwrap summary')
    medio(pg, 'transferencia', '#mediosCalc')
    check('Elegir en la calculadora cambia la Caja', 'on' in pg.get_attribute('#mediosCaja [data-medio="transferencia"]', 'class'))
    medio(pg, 'debito')
    check('Elegir en la Caja cambia la calculadora', 'on' in pg.get_attribute('#mediosCalc [data-medio="debito"]', 'class'))
    check('Con Débito se oculta "Paga con"', not pg.is_visible('#pago'))
    medio(pg, 'efectivo')
    check('Con Efectivo vuelve "Paga con"', pg.is_visible('#pago'))

    print('\n== Cobro por cada medio ==')
    for m in ['transferencia', 'debito', 'credito', 'pedidosya']:
        reset(pg); agregar(pg, 'malbec'); medio(pg, m)
        pg.evaluate("document.getElementById('pago').value='999999'")  # basura oculta no debe influir
        cobrar(pg); v = ultima(pg)
        check(f'{m}: total justo, sin vuelto, medio guardado',
              v and v['medio'] == m and v['pago'] == 10000 and v['vuelto'] == 0 and v['pagos'] == [{'medio': m, 'monto': 10000}], v)
    reset(pg); agregar(pg, 'malbec'); pg.fill('#pago', '20.000'); cobrar(pg); v = ultima(pg)
    check('Efectivo: vuelto 10.000 y medio efectivo', v and v['medio'] == 'efectivo' and v['vuelto'] == 10000 and v['pagos'][0]['monto'] == 10000, v)
    check('Después de cobrar vuelve a Efectivo', pg.evaluate('medioSel') == 'efectivo')
    check('El medio queda guardado en el navegador', guardado(pg)['movimientos'][-1]['medio'] == 'efectivo')

    print('\n== Pago mixto ==')
    reset(pg); agregar(pg, 'malbec', 'fernet')   # total 25.000
    medio(pg, 'mixto')
    check('Mixto muestra los campos por medio', pg.is_visible('#mx_transferencia') and pg.is_visible('#mx_pedidosya'))
    pg.fill('#mx_transferencia', '15.000')
    check('Calcula lo que falta en efectivo', 'Efectivo a cobrar: $10.000,00' in pg.inner_text('#mixtoEfectivo'), pg.inner_text('#mixtoEfectivo'))
    pg.fill('#pago', '20000')
    check('Vuelto sobre la parte en efectivo', 'Vuelto $10.000,00' in pg.inner_text('#vuelto'), pg.inner_text('#vuelto'))
    cobrar(pg); v = ultima(pg)
    check('Guarda mixto: efectivo 10.000 + transferencia 15.000',
          v and v['medio'] == 'mixto' and sorted((x['medio'], x['monto']) for x in v['pagos']) == [('efectivo', 10000), ('transferencia', 15000)] and v['vuelto'] == 10000, v)
    reset(pg); agregar(pg, 'malbec', 'fernet'); medio(pg, 'mixto')
    pg.fill('#mx_debito', '5000'); pg.fill('#mx_credito', '8000'); pg.fill('#mx_pedidosya', '12000'); cobrar(pg); v = ultima(pg)
    check('Mixto sin efectivo (débito+crédito+PedidosYa = total)', v and v['medio'] == 'mixto' and len(v['pagos']) == 3 and v['vuelto'] == 0, v)
    reset(pg); agregar(pg, 'malbec'); medio(pg, 'mixto'); pg.fill('#mx_transferencia', '10000'); cobrar(pg); v = ultima(pg)
    check('Mixto que en realidad es un solo medio se guarda como ese medio', v and v['medio'] == 'transferencia', v)
    reset(pg); agregar(pg, 'malbec'); medio(pg, 'mixto'); pg.fill('#mx_transferencia', '12000'); m = cobrar(pg)
    check('Mixto que supera el total se rechaza', not ventas(pg) and 'superan' in m, m)
    reset(pg); agregar(pg, 'malbec'); medio(pg, 'mixto'); m = cobrar(pg)
    check('Mixto sin montos se rechaza', not ventas(pg) and 'mixto' in m, m)
    reset(pg); agregar(pg, 'malbec'); medio(pg, 'mixto'); pg.fill('#mx_debito', 'abc'); m = cobrar(pg)
    check('Mixto con basura se rechaza', not ventas(pg) and 'válido' in m, m)
    reset(pg); agregar(pg, 'malbec'); medio(pg, 'mixto'); pg.fill('#mx_debito', '-500'); m = cobrar(pg)
    check('Mixto con negativo se rechaza', not ventas(pg), m)
    reset(pg); agregar(pg, 'malbec'); medio(pg, 'mixto'); pg.fill('#mx_debito', '4000'); pg.fill('#pago', '5000'); m = cobrar(pg)
    check('Mixto con efectivo insuficiente se rechaza', not ventas(pg) and 'Falta' in m, m)

    print('\n== Calculadora ==')
    reset(pg); agregar(pg, 'malbec'); pg.click('details.calcwrap summary')
    calc(pg, ['1', '5', '0', '0', '0', 'usar'])
    check('"Usar en pago" con efectivo pasa el monto', pg.input_value('#pago') == '15000' and 'Vuelto $5.000,00' in pg.inner_text('#vuelto'), pg.input_value('#pago'))
    medio(pg, 'credito', '#mediosCalc'); calc(pg, ['usar'])
    check('"Usar en pago" con crédito avisa total justo', 'Crédito' in pg.inner_text('#msgVenta'))
    cobrar(pg); v = ultima(pg)
    check('…y cobra por crédito', v and v['medio'] == 'credito' and v['pago'] == 10000, v)

    print('\n== Venta suelta ==')
    reset(pg); pg.click('details.calcwrap summary'); medio(pg, 'pedidosya', '#mediosCalc')
    calc(pg, ['C', '1', '2', '5', '0', '0']); pg.fill('#calcDetalle', 'Pedido #4567'); dialogs.clear()
    pg.click('#btnSuelta'); pg.wait_for_timeout(100); v = ultima(pg)
    check('Registra venta suelta por PedidosYa', v and v['items'] == [] and v['total'] == 12500 and v['medio'] == 'pedidosya' and v['suelta'] and v['detalle'] == 'Pedido #4567', v)
    check('Pide confirmación antes', any('venta suelta' in d for d in dialogs), dialogs)
    check('No toca el stock', pg.evaluate("stockDe('malbec')") == 20)
    check('Se guarda en el navegador', guardado(pg)['movimientos'][-1].get('suelta') is True)
    check('Calculadora queda en 0', pg.inner_text('#calcDisp') == '0')
    pg.wait_for_timeout(750); pg.click('#btnSuelta'); pg.wait_for_timeout(100)
    check('Con monto 0 no registra', len(ventas(pg)) == 1)
    pg.wait_for_timeout(750); medio(pg, 'mixto', '#mediosCalc'); calc(pg, ['5', '0', '0']); pg.click('#btnSuelta'); pg.wait_for_timeout(100)
    check('Con Mixto no registra venta suelta', len(ventas(pg)) == 1 and 'un solo medio' in pg.inner_text('#msgVenta'))
    medio(pg, 'efectivo', '#mediosCalc'); pg.wait_for_timeout(750)
    pg.evaluate("()=>{const b=document.getElementById('btnSuelta'); b.click(); b.click(); b.click();}")
    check('Triple clic en venta suelta = 1 sola', len(ventas(pg)) == 2, len(ventas(pg)))
    pg.click('[data-tab="reportes"]')
    check('Últimas ventas muestra "Venta suelta" y el medio', 'Venta suelta: Pedido #4567' in pg.inner_text('#tablaVentas') and 'PedidosYa' in pg.inner_text('#tablaVentas'))
    check('Ganancia no cuenta las sueltas (no tienen costo)', pg.inner_text('#repGan') == '$0,00' and 'sueltas' in pg.inner_text('#repGanHint'), pg.inner_text('#repGan'))

    print('\n== Ventas viejas sin medio ==')
    viejas = json.dumps([{'id': 'v1', 'tipo': 'venta', 'fecha': '2026-11-10T15:00:00.000Z', 'items': [{'productoId': 'malbec', 'cantidad': 1, 'precio': 10000, 'costo': 6500}], 'total': 10000, 'pago': 10000, 'vuelto': 0, 'descuento': 0},
                         {'id': 'v2', 'tipo': 'venta', 'fecha': '2026-11-10T16:00:00.000Z', 'items': [], 'total': 500, 'medio': '<img src=x onerror=alert(9)>', 'pagos': [{'medio': 'hack', 'monto': 500}]}])
    reset(pg, viejas); dialogs.clear()
    v = ventas(pg)
    check('Venta sin medio queda "Sin especificar"', v[0]['medio'] == 'sin' and v[0]['pagos'] == [{'medio': 'sin', 'monto': 10000}], v[0])
    check('Medio inventado/malicioso queda "Sin especificar"', v[1]['medio'] == 'sin', v[1])
    pg.click('[data-tab="estadisticas"]'); pg.click('#periodos [data-p="todo"]')
    check('Estadísticas muestra la tarjeta "Sin especificar"', pg.locator('#estTarjetas [data-medio="sin"]').count() == 1)
    check('Nada ejecuta código', not dialogs, dialogs)

    print('\n== Estadísticas ==')
    reset(pg)
    for m, extra in [('efectivo', None), ('transferencia', None), ('transferencia', None), ('pedidosya', None)]:
        agregar(pg, 'malbec'); medio(pg, m); cobrar(pg)
    agregar(pg, 'fernet'); medio(pg, 'mixto'); pg.fill('#mx_debito', '5000'); cobrar(pg)   # 10.000 efectivo + 5.000 débito
    pg.click('[data-tab="estadisticas"]'); pg.click('#periodos [data-p="hoy"]')
    dest = pg.inner_text('#estDestacado')
    check('Destacado: Efectivo (20.000) es el que más vendió', 'Efectivo' in dest and '$20.000,00' in dest, dest)
    tarj = {m: pg.inner_text(f'#estTarjetas [data-medio="{m}"]') for m in ['efectivo', 'transferencia', 'debito', 'credito', 'pedidosya']}
    check('Tarjeta transferencia: $20.000, 2 ventas, 36,4%', '$20.000,00' in tarj['transferencia'] and '2 ventas' in tarj['transferencia'] and '36,4%' in tarj['transferencia'], tarj['transferencia'])
    check('Tarjeta efectivo cuenta la parte del mixto (2 ventas, ticket $10.000)', '2 ventas' in tarj['efectivo'] and 'Ticket promedio $10.000,00' in tarj['efectivo'], tarj['efectivo'])
    check('Tarjeta crédito en cero', '$0,00' in tarj['credito'] and '0 ventas' in tarj['credito'], tarj['credito'])
    check('Sin "Sin especificar" si no hay ventas viejas', pg.locator('#estTarjetas [data-medio="sin"]').count() == 0)
    check('Aviso de pago mixto', '1 venta con pago mixto' in pg.inner_text('#estMixto'))
    check('5 barras de comparación', pg.locator('#estBarras .bar').count() == 5)
    tabla = pg.inner_text('#tablaEstDias')
    check('Tabla por día con total del día $55.000', '$55.000,00' in tabla, tabla)
    # venta de hace 20 días: entra en 30 días y Todo, no en 7 días ni Hoy
    pg.evaluate("()=>{const f=new Date(); f.setDate(f.getDate()-20); DB.movimientos.push({id:'vieja',tipo:'venta',fecha:f.toISOString(),items:[],total:99000,pago:99000,vuelto:0,medio:'credito',pagos:[{medio:'credito',monto:99000}],suelta:true}); save(); renderAll();}")
    pg.click('#periodos [data-p="7"]')
    check('7 días no incluye la venta de hace 20 días', '$99.000' not in pg.inner_text('#estTarjetas'))
    pg.click('#periodos [data-p="30"]')
    check('30 días sí la incluye (Crédito pasa a ser el destacado)', 'Crédito' in pg.inner_text('#estDestacado') and '$99.000,00' in pg.inner_text('#estDestacado'))
    check('La tabla de 30 días tiene fila de totales', 'Total' in pg.inner_text('#tablaEstDias tbody'))

    print('\n== Datos simulados, CSV y backup ==')
    reset(pg); pg.click('[data-tab="datos"]'); pg.click('#btnEjemplo'); pg.wait_for_timeout(200)
    meds = set(pg.evaluate("DB.movimientos.filter(m=>m.tipo==='venta').map(m=>m.medio)"))
    check('Datos simulados con medios variados', len(meds) >= 4 and 'sin' not in meds, meds)
    check('Datos simulados incluyen ventas sueltas de PedidosYa', pg.evaluate("DB.movimientos.some(m=>m.suelta && m.medio==='pedidosya')"))
    check('Pagos de cada venta suman el total', pg.evaluate("DB.movimientos.filter(m=>m.tipo==='venta').every(m=>Math.abs(m.pagos.reduce((a,p)=>a+p.monto,0)-m.total)<0.01)"))
    with pg.expect_download() as d: pg.click('#btnExportMov')
    csv = open(d.value.path(), encoding='utf-8-sig').read()
    check('CSV de movimientos trae medio_pago y detalle_pago', 'medio_pago' in csv.splitlines()[0] and 'detalle_pago' in csv.splitlines()[0])
    check('CSV incluye las ventas sueltas', 'Venta suelta' in csv)
    with pg.expect_download() as d: pg.click('#btnExportJson')
    bk = json.load(open(d.value.path()))
    n = len(bk['movimientos'])
    pg.evaluate("DB={productos:[],movimientos:[]}; save(); renderAll();")
    pg.set_input_files('#fileJson', d.value.path()); pg.wait_for_timeout(200)
    check('Backup ida y vuelta conserva medios y ventas sueltas',
          pg.evaluate("DB.movimientos.length") == n and pg.evaluate("DB.movimientos.some(m=>m.suelta)") and pg.evaluate("DB.movimientos.some(m=>m.medio==='mixto')"))

    check('Sin errores de JavaScript', not errs, errs[:5])
    b.close()

ok = sum(1 for r in RES if r[1])
print(f'\nRESULTADO: {ok}/{len(RES)} pruebas OK')
sys.exit(0 if ok == len(RES) else 1)
