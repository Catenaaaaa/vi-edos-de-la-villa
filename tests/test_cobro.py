"""Batería de pruebas de Viñedos de la Villa (cobro, stock, intentos de "burlar" la caja).
Uso: ~/.venvs/playwright/bin/python -I tests/test_cobro.py
"""
import os, sys, json
from playwright.sync_api import sync_playwright

URL = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
OUT = os.environ.get('OUT', '/tmp')
RES = []

def check(nombre, ok, detalle=''):
    RES.append((nombre, bool(ok), detalle))
    print(('  OK   ' if ok else '  FALLA') + ' ' + nombre + (('  → ' + str(detalle)) if (detalle and not ok) else ''))

def nueva(ctx, errs, dialogs):
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: (dialogs.append(d.message), d.accept()))
    return pg

def reset(pg):
    pg.goto(URL)
    pg.evaluate("localStorage.clear()")
    pg.goto(URL)
    pg.evaluate("""()=>{
      const P=(id,codigo,nombre,cat,c,v,s,m)=>({id,codigo,nombre,categoria:cat,precioCosto:c,precioVenta:v,stockInicial:s,stockMinimo:m});
      DB={productos:[P('malbec','7790000000011','Malbec Reserva 750 ml','Tintos',6500,10900,5,2),
                     P('fernet','7790000000080','Fernet 750 ml','Destilados',9800,14500,3,1),
                     P('lata','7790000000110','Cerveza IPA lata','Cervezas',1700,2900.5,10,2),
                     P('centavos','7790000000999','Caramelo','Almacén',0.07,0.1,100,0)],movimientos:[]};
      save(); carrito=[]; renderAll();
    }""")

# Simula un lector USB real: teclas cada ~3 ms que se escriben en el campo con foco, y Enter al final
SCAN_JS = '''async (code)=>{
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  for(const ch of code+'\\n'){
    const key = ch==='\\n' ? 'Enter' : ch;
    const el=document.activeElement;
    const ev=new KeyboardEvent('keydown',{key,bubbles:true,cancelable:true});
    const ok=(el||document).dispatchEvent(ev);
    if(ok && key!=='Enter' && el && 'value' in el && el.type!=='checkbox'){
      try{ const p=el.selectionStart??el.value.length; el.value=el.value.slice(0,p)+ch+el.value.slice(el.selectionEnd??p); el.setSelectionRange&&el.setSelectionRange(p+1,p+1);}catch(e){ el.value+=ch; }
      el.dispatchEvent(new Event('input',{bubbles:true}));
    }
    await sleep(3);
  }
}'''
def scan(pg, code):
    pg.evaluate(SCAN_JS, code)
    pg.wait_for_timeout(30)

def ventas(pg): return pg.evaluate("DB.movimientos.filter(m=>m.tipo==='venta')")
def stock(pg, id): return pg.evaluate(f"stockDe('{id}')")
def guardado(pg): return pg.evaluate("JSON.parse(localStorage.getItem(KEY)||'{}')")

def cobrar(pg, pago=None, desc=None):
    if desc is not None: pg.fill('#descuento', str(desc))
    if pago is not None: pg.fill('#pago', str(pago))
    pg.click('#btnCobrar')
    return pg.inner_text('#msgVenta')

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1366, 'height': 900})   # mismo navegador = mismo almacenamiento
    errs, dialogs = [], []
    pg = nueva(ctx, errs, dialogs)

    print('\n== Cobro normal ==')
    reset(pg)
    scan(pg, '7790000000011'); scan(pg, '7790000000011'); scan(pg, '7790000000080')
    check('Total = 2×10.900 + 14.500', pg.inner_text('#granTotal') == '$36.300,00', pg.inner_text('#granTotal'))
    pg.fill('#pago', '40000'); check('Vuelto en pantalla', 'Vuelto $3.700,00' in pg.inner_text('#vuelto'), pg.inner_text('#vuelto'))
    m = cobrar(pg)
    v = ventas(pg)
    check('Se registra 1 venta', len(v) == 1 and abs(v[0]['total'] - 36300) < .001 and abs(v[0]['vuelto'] - 3700) < .001, v)
    check('Stock descuenta', stock(pg, 'malbec') == 3 and stock(pg, 'fernet') == 2)
    check('Venta guardada en el navegador', len(guardado(pg)['movimientos']) == 1)
    check('Ticket queda vacío', pg.evaluate('carrito.length') == 0)

    print('\n== Montos con formato argentino ==')
    reset(pg); scan(pg, '7790000000011')
    pg.fill('#pago', '20.000')
    check('"20.000" se entiende como veinte mil (vuelto 9.100)', 'Vuelto $9.100,00' in pg.inner_text('#vuelto'), pg.inner_text('#vuelto'))
    cobrar(pg); v = ventas(pg)
    check('Cobra con "20.000"', len(v) == 1 and abs(v[0]['pago'] - 20000) < .001, v and v[0]['pago'])
    reset(pg); scan(pg, '7790000000011')
    cobrar(pg, '$ 10.900,00'); v = ventas(pg)
    check('Acepta "$ 10.900,00"', len(v) == 1 and abs(v[0]['pago'] - 10900) < .001, v)
    reset(pg); scan(pg, '7790000000011')
    cobrar(pg, '10900,5'); v = ventas(pg)
    check('Acepta "10900,5"', len(v) == 1 and abs(v[0]['pago'] - 10900.5) < .001, v)

    print('\n== Pagos inválidos ==')
    for pago in ['5000', '-20000', '10.899', '0,5']:
        reset(pg); scan(pg, '7790000000011'); m = cobrar(pg, pago)
        check(f'Pago insuficiente "{pago}" se rechaza', len(ventas(pg)) == 0 and ('Falta' in m or 'válido' in m), m)
    for pago in ['abc', '12a', '1e9', '--', '9999999999999999999999']:
        reset(pg); scan(pg, '7790000000011'); m = cobrar(pg, pago)
        check(f'Pago basura "{pago}" no registra venta', len(ventas(pg)) == 0, (m, ventas(pg)[:1]))
    reset(pg); scan(pg, '7790000000011'); m = cobrar(pg, '')
    v = ventas(pg)
    check('Pago vacío = pago justo', len(v) == 1 and abs(v[0]['pago'] - 10900) < .001 and abs(v[0]['vuelto']) < .001, v)
    reset(pg); m = cobrar(pg, '1000')
    check('Ticket vacío no cobra', len(ventas(pg)) == 0 and 'vacío' in m, m)

    print('\n== Descuentos ==')
    reset(pg); scan(pg, '7790000000011'); m = cobrar(pg, '', '150')
    check('Descuento 150% no deja cobrar en $0', len(ventas(pg)) == 0, m)
    reset(pg); scan(pg, '7790000000011'); cobrar(pg, '', '-50'); v = ventas(pg)
    check('Descuento negativo no aumenta el precio ni se registra raro', len(v) == 0 or (abs(v[0]['total'] - 10900) < .001 and v[0]['descuento'] == 0), v)
    reset(pg); scan(pg, '7790000000011'); cobrar(pg, '', '10'); v = ventas(pg)
    check('Descuento 10% → total 9.810', len(v) == 1 and abs(v[0]['total'] - 9810) < .001, v)
    reset(pg); scan(pg, '7790000000011'); cobrar(pg, '', 'abc'); v = ventas(pg)
    check('Descuento "abc" → sin descuento', len(v) == 0 or abs(v[0]['total'] - 10900) < .001, v)
    reset(pg); scan(pg, '7790000000011'); cobrar(pg, '', '12,5'); v = ventas(pg)
    check('Descuento "12,5" → total 9.537,50', len(v) == 1 and abs(v[0]['total'] - 9537.5) < .001, v)

    print('\n== Centavos y redondeo ==')
    reset(pg)
    for _ in range(3): scan(pg, '7790000000999')
    cobrar(pg, '0,3'); v = ventas(pg)
    check('3 × $0,10 con pago $0,30 → sin "falta dinero"', len(v) == 1, (pg.inner_text('#msgVenta'), v))
    check('Total y vuelto redondeados a centavos', len(v) == 1 and v[0]['total'] == 0.3 and v[0]['vuelto'] == 0, v)
    reset(pg); scan(pg, '7790000000110'); scan(pg, '7790000000110'); scan(pg, '7790000000110'); cobrar(pg, '', '7'); v = ventas(pg)
    check('Total con descuento redondeado a 2 decimales', len(v) == 1 and round(v[0]['total'], 2) == v[0]['total'], v and v[0]['total'])

    print('\n== Cantidades y stock ==')
    reset(pg); scan(pg, '7790000000080')
    for val, esperado in [('0', 1), ('-3', 1), ('2.7', 2), ('', 1)]:
        pg.fill('#carrito .qty input', val); pg.dispatch_event('#carrito .qty input', 'change')
        check(f'Cantidad "{val}" queda en {esperado}', pg.evaluate('carrito[0].cantidad') == esperado, pg.evaluate('carrito[0].cantidad'))
    pg.fill('#carrito .qty input', '999'); pg.dispatch_event('#carrito .qty input', 'change')
    check('Cantidad mayor al stock se rechaza', pg.evaluate('carrito[0].cantidad') <= 3, pg.evaluate('carrito[0].cantidad'))
    pg.fill('#carrito .qty input', '1'); pg.dispatch_event('#carrito .qty input', 'change')
    for _ in range(6): pg.click('#carrito [data-mas]')
    check('Botón + no pasa el stock', pg.evaluate('carrito[0].cantidad') == 3, pg.evaluate('carrito[0].cantidad'))
    for _ in range(5): scan(pg, '7790000000080')
    check('Escanear de más no pasa el stock', pg.evaluate('carrito[0].cantidad') == 3)
    for _ in range(5): pg.click('#carrito [data-menos]')
    check('Botón − no baja de 1', pg.evaluate('carrito[0].cantidad') == 1)
    # stock que cambia con el producto ya en el ticket
    reset(pg); scan(pg, '7790000000080'); scan(pg, '7790000000080'); scan(pg, '7790000000080')
    pg.evaluate("getProducto('fernet').stockInicial=1; save()")
    m = cobrar(pg, '')
    check('Si el stock bajó mientras estaba en el ticket, no vende de más', stock(pg, 'fernet') >= 0, (m, stock(pg, 'fernet')))

    print('\n== Doble cobro / clics rápidos ==')
    reset(pg); scan(pg, '7790000000011')
    pg.fill('#pago', '20000')
    pg.evaluate("()=>{const b=document.getElementById('btnCobrar'); b.click(); b.click(); b.click();}")
    check('Triple clic en Cobrar = 1 sola venta', len(ventas(pg)) == 1, len(ventas(pg)))
    reset(pg); scan(pg, '7790000000011'); pg.dblclick('#btnCobrar')
    check('Doble clic en Cobrar = 1 sola venta', len(ventas(pg)) == 1, len(ventas(pg)))

    print('\n== Lector mientras se cobra ==')
    reset(pg); scan(pg, '7790000000011'); pg.click('#pago'); pg.keyboard.type('20000', delay=90); pg.wait_for_timeout(300)
    scan(pg, '7790000000080')
    check('Escanear con el foco en "Paga con" suma el producto', pg.evaluate('carrito.length') == 2)
    check('…y no ensucia el monto pagado', pg.input_value('#pago') == '20000', pg.input_value('#pago'))
    pg.click('#descuento'); scan(pg, '7790000000110')
    check('Escanear en "Descuento" no deja basura', pg.input_value('#descuento') in ('0', ''), pg.input_value('#descuento'))
    pg.click('#buscar'); pg.keyboard.type('mal', delay=120)
    check('Tipear a mano no se confunde con el lector', pg.input_value('#buscar') == 'mal' and pg.evaluate('carrito.length') == 3)

    print('\n== Productos: datos inválidos ==')
    reset(pg); pg.click('[data-tab="productos"]')
    def alta(nombre, costo='100', venta='200', st='5', cod=''):
        pg.click('#btnNuevoProd'); pg.fill('#p_codigo', cod); pg.fill('#p_nombre', nombre); pg.fill('#p_cat', 'Tintos')
        pg.fill('#p_costo', costo); pg.fill('#p_venta', venta); pg.fill('#p_stock', st); pg.click('#btnGuardarProd')
        return pg.inner_text('#msgProd')
    n0 = pg.evaluate('DB.productos.length')
    alta('Precio negativo', venta='-500')
    check('No acepta precio de venta negativo', pg.evaluate('DB.productos.length') == n0)
    alta('Costo negativo', costo='-5')
    check('No acepta costo negativo', pg.evaluate('DB.productos.length') == n0)
    alta('Stock negativo', st='-10')
    check('No acepta stock inicial negativo', pg.evaluate('DB.productos.length') == n0)
    alta('Precio con miles', venta='10.900', costo='6.500,50')
    pr = pg.evaluate("DB.productos.find(p=>p.nombre==='Precio con miles')")
    check('Precio "10.900" se guarda como 10900', pr and pr['precioVenta'] == 10900 and pr['precioCosto'] == 6500.5, pr)
    alta('Duplicado', cod='7790000000011')
    check('No acepta código repetido', pg.evaluate("DB.productos.filter(p=>p.codigo==='7790000000011').length") == 1)
    alta('   ')
    check('No acepta nombre vacío', pg.evaluate('DB.productos.length') == n0 + 1)

    print('\n== Inyección de código (nombres maliciosos) ==')
    reset(pg); dialogs.clear()
    pg.evaluate("""()=>{DB.productos.push({id:'x1',codigo:'111111',nombre:'<img src=x onerror=alert(1)>',categoria:'<script>alert(2)</scr'+'ipt>',precioCosto:1,precioVenta:2,stockInicial:5,stockMinimo:9,foto:'data:image/png" onerror="alert(3)'});save();renderAll();}""")
    scan(pg, '111111'); cobrar(pg, '')
    for t in ['productos', 'pedidos', 'stock', 'reportes', 'datos', 'ventas']:
        pg.click(f'[data-tab="{t}"]'); pg.wait_for_timeout(50)
    pg.click('[data-tab="productos"]'); pg.click('#tablaProductos tbody tr:has-text("img src") .btn.sec')
    pg.wait_for_timeout(200)
    check('Ningún nombre/sector/foto ejecuta código', not dialogs, dialogs)
    dialogs.clear()
    mal = {'productos': [{'id': "a');alert(4);('", 'codigo': '1', 'nombre': 'x', 'categoria': '', 'precioCosto': 1, 'precioVenta': 1, 'stockInicial': 1, 'stockMinimo': 0}], 'movimientos': []}
    path = os.path.join(OUT, 'backup-malicioso.json'); json.dump(mal, open(path, 'w'))
    pg.click('[data-tab="datos"]'); pg.set_input_files('#fileJson', path); pg.wait_for_timeout(200)
    dialogs[:] = [d for d in dialogs if 'reemplaza' not in d]
    pg.click('[data-tab="productos"]')
    try: pg.click('#tablaProductos tbody tr .btn.sec', timeout=1500)
    except Exception: pass
    try: pg.click('#tablaProductos tbody tr .btn.danger', timeout=1500)
    except Exception: pass
    pg.wait_for_timeout(200)
    check('Backup con id malicioso no ejecuta código', not [d for d in dialogs if d in ('4',)], dialogs)
    dialogs.clear()

    print('\n== Importador: filas tramposas ==')
    reset(pg)
    csv = 'codigo;nombre;sector;precio_costo;precio_venta;stock\n7795555555555;Negativo;Tintos;100;-900;5\n7796666666666;Stock negativo;Tintos;100;900;-5\n7797777777777;Bien;Tintos;100;900;5\n'
    path = os.path.join(OUT, 'tramposo.csv'); open(path, 'w', encoding='utf-8').write(csv)
    pg.click('[data-tab="datos"]'); pg.set_input_files('#fileImp', path); pg.wait_for_timeout(200)
    pg.click('#impConfirmar')
    nombres = pg.evaluate('DB.productos.map(p=>p.nombre)')
    check('Importador rechaza precio negativo', 'Negativo' not in nombres, nombres)
    check('Importador rechaza stock negativo', 'Stock negativo' not in nombres, nombres)
    check('Importador acepta la fila buena', 'Bien' in nombres, nombres)

    print('\n== Dos pestañas abiertas a la vez ==')
    reset(pg)
    pg2 = nueva(ctx, errs, dialogs); pg2.goto(URL)
    pg.click('[data-tab="ventas"]'); scan(pg, '7790000000011'); cobrar(pg, '')
    pg2.wait_for_timeout(200)
    pg2.click('[data-tab="ventas"]'); pg2.bring_to_front(); pg2.click('#codigo')
    scan(pg2, '7790000000080'); pg2.fill('#pago', ''); pg2.click('#btnCobrar')
    pg2.wait_for_timeout(200)
    total_guardado = len([m for m in guardado(pg2)['movimientos'] if m['tipo'] == 'venta'])
    check('Una venta en cada pestaña → se guardan las 2 (no se pisan)', total_guardado == 2,
          (total_guardado, pg.inner_text('#msgVenta'), pg2.inner_text('#msgVenta'), pg2.inner_text('#msgBuscar')))
    pg2.close()

    print('\n== Datos dañados / almacenamiento ==')
    pg.evaluate("localStorage.setItem(KEY,'{esto no es json')"); pg.goto(URL); pg.wait_for_timeout(100)
    check('Con datos dañados la app igual abre', pg.evaluate("typeof DB==='object' && Array.isArray(DB.productos)"))
    reset(pg); scan(pg, '7790000000011'); pg.fill('#pago', '')
    pg.evaluate("()=>{window.__set=Storage.prototype.setItem; Storage.prototype.setItem=function(){throw new Error('lleno')}; }")
    cobrar(pg)
    pg.evaluate("()=>{Storage.prototype.setItem=window.__set;}")
    en_memoria = len(ventas(pg)); en_disco = len([m for m in guardado(pg).get('movimientos', []) if m['tipo'] == 'venta'])
    check('Si no se puede guardar, la venta no queda "a medias"', en_memoria == en_disco, (en_memoria, en_disco))
    check('…y el ticket no se pierde', pg.evaluate('carrito.length') == 1)

    print('\n== Pedidos inválidos ==')
    reset(pg); pg.click('[data-tab="pedidos"]')
    pg.fill('#ped_cant', '-5'); pg.click('#btnPedido')
    check('Pedido con cantidad negativa se rechaza', pg.evaluate("DB.movimientos.length") == 0)
    pg.fill('#ped_cant', '5'); pg.fill('#ped_costo', '-100'); pg.click('#btnPedido')
    check('Pedido con costo negativo se rechaza', pg.evaluate("DB.movimientos.length") == 0)
    pg.fill('#ped_costo', '6.500'); pg.click('#btnPedido')
    mv = pg.evaluate("DB.movimientos[0]")
    check('Costo "6.500" en pedido = 6500', mv and mv['items'][0]['costo'] == 6500, mv)

    print('\n== Números ==')
    reset(pg); scan(pg, '7790000000011'); cobrar(pg, '', '10')
    pg.click('[data-tab="reportes"]')
    check('Ganancia = cobrado − costo (9.810 − 6.500 = 3.310)', pg.inner_text('#repGan') == '$3.310,00', pg.inner_text('#repGan'))

    check('Sin errores de JavaScript en toda la prueba', not errs, errs[:5])
    b.close()

ok = sum(1 for r in RES if r[1])
print(f'\nRESULTADO: {ok}/{len(RES)} pruebas OK')
sys.exit(0 if ok == len(RES) else 1)
