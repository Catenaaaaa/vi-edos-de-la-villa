"""Capturas de presentación (fotos/NN-*.png) para mandar al cliente."""
import os
from playwright.sync_api import sync_playwright
V=os.path.dirname(os.path.abspath(__file__)); F=V+'/fotos'
URL='file://'+os.path.abspath(V+'/../public/index.html')
SCAN='''async (code)=>{const s=ms=>new Promise(r=>setTimeout(r,ms));for(const ch of code+'\\n'){const key=ch==='\\n'?'Enter':ch;const el=document.activeElement;
 const ok=(el||document).dispatchEvent(new KeyboardEvent('keydown',{key,bubbles:true,cancelable:true}));
 if(ok&&key!=='Enter'&&el&&'value' in el){el.value+=ch;el.dispatchEvent(new Event('input',{bubbles:true}));}await s(3);}}'''
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1440,'height':900},device_scale_factor=2)
    pg=ctx.new_page(); pg.on('dialog',lambda d:d.accept())
    pg.goto(URL); pg.evaluate("localStorage.clear()"); pg.goto(URL)
    pg.evaluate("Math.random=(()=>{let s=11;return()=>(s=(s*16807)%2147483647)/2147483647})()")
    pg.add_style_tag(content='*{transition:none!important;animation:none!important}')
    pg.click('#resultados .btn.gold'); pg.wait_for_timeout(300); pg.evaluate("OPT.beep=false")
    for c in ['7790000000011','7790000000011','7790000000080','7790000000110']: pg.evaluate(SCAN,c); pg.wait_for_timeout(80)
    pg.fill('#pago','45.000'); pg.wait_for_timeout(100)
    pg.screenshot(path=f'{F}/01-caja-venta-en-curso.png')
    pg.click('#btnCobrar'); pg.wait_for_timeout(150)
    pg.click('#sectoresBar .sector:has-text("Tintos")'); pg.wait_for_timeout(100)
    pg.screenshot(path=f'{F}/02-caja-sector-tintos.png')
    pg.click('#sectoresBar .sector:has-text("Todo")')
    pg.click('[data-tab="productos"]'); pg.click('#tablaProductos tbody tr:has-text("Espumante Extra") [data-editar]'); pg.wait_for_timeout(150)
    pg.screenshot(path=f'{F}/03-cava-productos-y-precios.png')
    pg.click('[data-tab="pedidos"]'); pg.wait_for_timeout(100); pg.screenshot(path=f'{F}/04-pedidos-entrada-de-mercaderia.png')
    pg.click('[data-tab="stock"]'); pg.wait_for_timeout(100); pg.screenshot(path=f'{F}/05-deposito-stock.png')
    pg.click('[data-tab="reportes"]'); pg.wait_for_timeout(200); pg.screenshot(path=f'{F}/06-numeros.png', full_page=True)
    pg.click('[data-tab="datos"]'); pg.set_input_files('#fileImp', V+'/lista-ejemplo.csv'); pg.wait_for_timeout(300)
    pg.screenshot(path=f'{F}/07-importar-desde-excel.png'); pg.click('#impCancelar')
    pg.wait_for_timeout(100); pg.screenshot(path=f'{F}/08-datos-backup-y-creditos.png', full_page=True)
    m=ctx.new_page(); m.set_viewport_size({'width':390,'height':844}); m.goto(URL); m.add_style_tag(content='*{transition:none!important;animation:none!important}')
    m.wait_for_timeout(200); m.screenshot(path=f'{F}/09-vista-celular.png', full_page=False)
    b.close()
print(sorted(os.listdir(F)))
