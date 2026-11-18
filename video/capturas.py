"""Saca las capturas de la app que usa el video (img/*.png)."""
import os
from playwright.sync_api import sync_playwright
V=os.path.dirname(os.path.abspath(__file__)); I=V+'/img'
URL='file://'+os.path.abspath(V+'/../public/index.html')
SCAN_JS='''async (code)=>{const sleep=ms=>new Promise(r=>setTimeout(r,ms));
 for(const ch of code+'\\n'){const key=ch==='\\n'?'Enter':ch;const el=document.activeElement;
  const ok=(el||document).dispatchEvent(new KeyboardEvent('keydown',{key,bubbles:true,cancelable:true}));
  if(ok&&key!=='Enter'&&el&&'value' in el){el.value+=ch;el.dispatchEvent(new Event('input',{bubbles:true}));}
  await sleep(3);}}'''
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1280,'height':800},device_scale_factor=2)
    pg=ctx.new_page(); pg.on('dialog',lambda d:d.accept())
    pg.goto(URL); pg.evaluate("localStorage.clear()"); pg.goto(URL)
    pg.evaluate("Math.random=(()=>{let s=7;return()=>(s=(s*16807)%2147483647)/2147483647})()")  # datos repetibles
    pg.click('#resultados .btn.gold'); pg.wait_for_timeout(300)
    pg.evaluate("OPT.beep=false")
    shot=lambda sel,name: pg.locator(sel).screenshot(path=f'{I}/{name}.png')
    pg.add_style_tag(content='.vk-toggle{display:none!important} .topbar{position:static!important} *{transition:none!important;animation:none!important}')
    # ticket armándose
    shot('.ticket','ticket0')
    for i,c in enumerate(['7790000000011','7790000000080','7790000000110']):
        pg.evaluate(SCAN_JS,c); pg.wait_for_timeout(150); shot('.ticket',f'ticket{i+1}')
    pg.evaluate(SCAN_JS,'7790000000110'); pg.wait_for_timeout(150)
    pg.screenshot(path=f'{I}/caja.png')
    shot('#scanbox','scanbox')
    # sectores
    pg.click('#sectoresBar .sector:has-text("Tintos")'); pg.wait_for_timeout(150)
    pg.evaluate("document.getElementById('resultados').style.maxHeight='none'")
    pg.locator('#tab-ventas .card').first.screenshot(path=f'{I}/sectores.png')
    pg.click('#sectoresBar .sector:has-text("Todo")')
    # cobro
    pg.fill('#pago','40.000'); pg.wait_for_timeout(100); shot('.pay','pago')
    pg.click('#btnCobrar'); pg.wait_for_timeout(150); shot('.pay','cobrado')
    # cava: editar un producto
    pg.click('[data-tab="productos"]'); pg.wait_for_timeout(100)
    pg.click('#tablaProductos tbody tr:has-text("Malbec Reserva") [data-editar]'); pg.wait_for_timeout(150)
    pg.screenshot(path=f'{I}/cava.png')
    pg.click('#btnNuevoProd'); pg.evaluate(SCAN_JS,'7798888888888'); pg.wait_for_timeout(150)
    pg.fill('#p_nombre','Malbec Rosé 750 ml'); pg.fill('#p_cat','Rosados'); pg.fill('#p_venta','9.800'); pg.fill('#p_costo','5.900')
    pg.dispatch_event('#p_nombre','input'); pg.wait_for_timeout(100)
    shot('#tab-productos .card >> nth=0','alta')
    # importador
    csv=V+'/lista-ejemplo.csv'
    open(csv,'w',encoding='utf-8').write('Código;Producto;Rubro;Precio costo;Precio venta;Stock\n'
      '7790000000011;Malbec Reserva 750 ml;Tintos;6.900;11.500;24\n7790000000080;Fernet 750 ml;Destilados;10.200;15.200;30\n'
      '7791234500017;Petit Verdot 750 ml;Tintos;8.100;13.400;6\n7791234500024;Moscato dulce 750 ml;Blancos;4.900;8.200;12\n'
      '7791234500031;Sidra 750 ml;Espumantes;2.600;4.500;18\n7791234500048;Licor de café 700 ml;Destilados;6.300;9.900;5\n')
    pg.click('[data-tab="datos"]'); pg.set_input_files('#fileImp',csv); pg.wait_for_timeout(300)
    shot('.modal-box','import')
    pg.click('#impConfirmar'); pg.wait_for_timeout(150)
    # depósito y números
    pg.click('[data-tab="stock"]'); pg.wait_for_timeout(150); pg.screenshot(path=f'{I}/deposito.png')
    pg.click('[data-tab="reportes"]'); pg.wait_for_timeout(200)
    pg.screenshot(path=f'{I}/numeros.png')
    shot('#tab-reportes .grid.g3','kpis'); shot('#tab-reportes .grid.g2 .card >> nth=0','barras')
    pg.click('[data-tab="ventas"]'); pg.wait_for_timeout(150); pg.screenshot(path=f'{I}/caja-limpia.png')
    b.close()
print('ok', sorted(os.listdir(I)))
