"""Renderiza stage.html cuadro por cuadro.
Uso:
  python render.py stills 3.5 9 15 ...      -> PNGs sueltos en stills/
  python render.py video [desde] [hasta]    -> video.mp4 (sin audio)
"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright

V = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(f"{V}/data.json", encoding="utf-8"))
FPS = DATA["fps"]

def abrir(p):
    b = p.chromium.launch(args=["--font-render-hinting=none"])
    pg = b.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
    pg.add_init_script(f"window.DATA = {json.dumps(DATA)};")
    pg.goto(f"file://{V}/stage.html")
    pg.evaluate("document.fonts.ready")
    pg.wait_for_function("[...document.images].every(i => i.complete && i.naturalWidth > 0)")
    pg.wait_for_timeout(300)
    return b, pg

modo = sys.argv[1]
with sync_playwright() as p:
    b, pg = abrir(p)
    if modo == "stills":
        os.makedirs(f"{V}/stills", exist_ok=True)
        for s in sys.argv[2:]:
            pg.evaluate(f"render({float(s)})")
            pg.screenshot(path=f"{V}/stills/t{float(s):05.1f}.png")
        print("ok")
    else:
        desde = float(sys.argv[2]) if len(sys.argv) > 2 else 0
        hasta = float(sys.argv[3]) if len(sys.argv) > 3 else DATA["total"]
        n0, n1 = int(desde * FPS), int(hasta * FPS)
        out = f"{V}/video.mp4" if len(sys.argv) <= 2 else f"{V}/parcial.mp4"
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), out],
                              stdin=subprocess.PIPE)
        t0 = time.time()
        for f in range(n0, n1):
            pg.evaluate(f"render({f / FPS})")
            ff.stdin.write(pg.screenshot(type="jpeg", quality=93))
            if f % 150 == 0:
                print(f"cuadro {f}/{n1}  {time.time() - t0:.0f}s", flush=True)
        ff.stdin.close(); ff.wait()
        print("listo", out, f"{time.time() - t0:.0f}s")
    b.close()
