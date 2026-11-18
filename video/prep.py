"""Arma la línea de tiempo del reel: escenas, envolvente de voz (para la boca de Cate),
subtítulos sincronizados con las pausas, marcas por palabra clave, pista de voz,
música original y efectos. Python puro (sin numpy)."""
import json, math, random, re, struct, wave, os

V = os.path.dirname(os.path.abspath(__file__))
FPS = 30
SR = 22050
VOICE_IN = 0.35      # la voz arranca 0,35 s después de que entra la escena
TAIL = 0.55          # aire al final de cada escena
EXTRA = {"s1": 0.25, "s8": 2.6}   # más aire al principio (s1) o al final (s8)
LEAD = {"s1": 0.9}   # en s1 primero aparece el título y después habla

guion = json.load(open(f"{V}/guion.json", encoding="utf-8"))

def leer_wav(p):
    with wave.open(p) as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2
        sr = w.getframerate(); n = w.getnframes()
        data = struct.unpack(f"<{n}h", w.readframes(n))
    return sr, [x / 32768 for x in data]

def envolvente(x, sr):
    hop = sr // FPS
    rms = []
    for i in range(0, len(x), hop):
        seg = x[i:i + hop]
        rms.append(math.sqrt(sum(v * v for v in seg) / max(1, len(seg))))
    return rms

def pausas(rms, thr):
    """Tramos en silencio de al menos 0,1 s -> lista de (inicio, fin) en segundos."""
    out, start = [], None
    for i, r in enumerate(rms + [0]):
        if r < thr and start is None: start = i
        if (r >= thr or i == len(rms)) and start is not None:
            if (i - start) / FPS >= 0.1: out.append((start / FPS, i / FPS))
            start = None
    return out

PALABRAS = {
    "s1": {"hola": "¡Hola", "vinedos": "Viñedos"},
    "s2": {"lector": "lector", "ticket": "ticket", "tipear": "Sin tipear"},
    "s3": {"tintos": "tintos", "blancos": "blancos", "destilados": "destilados", "cervezas": "cervezas", "toque": "toque"},
    "s4": {"vuelto": "vuelto", "menos": "cobrar de menos", "hay": "vender lo que"},
    "s5": {"foto": "foto", "precio": "precio", "nuevo": "escaneás"},
    "s6": {"excel": "Excel", "segundos": "segundos", "vista": "vista previa"},
    "s7": {"reponer": "reponer", "numeros": "Números", "vendiste": "vendiste", "sale": "más sale"},
    "s8": {"medida": "a medida", "catena": "Catena Webs", "juntos": "probamos"},
}

def alinear(texto, dur, silencios):
    """Devuelve f(char_index) -> segundos, alineando la puntuación con las pausas reales."""
    # tramos de habla = entre silencios (ignorando el silencio inicial/final)
    hablas, t0 = [], 0.0
    for a, b in silencios:
        if a <= 0.05: t0 = b; continue
        if b >= dur - 0.05: break
        hablas.append((t0, a)); t0 = b
    fin = silencios[-1][0] if silencios and silencios[-1][1] >= dur - 0.05 else dur
    hablas.append((t0, fin))
    # tramos de texto separados por puntuación fuerte
    cortes = [m.end() for m in re.finditer(r"[,.;:?!]+\s*", texto)]
    cortes = [c for c in cortes if c < len(texto)]
    frases = [0] + cortes + [len(texto)]
    nf = len(frases) - 1
    # si hay tantos tramos de voz como de texto, se alinean 1 a 1; si no, se reparte proporcional
    if len(hablas) == nf:
        tramos = hablas
    else:
        total = sum(b - a for a, b in hablas)
        largo = len(texto)
        tramos, acc = [], 0
        for i in range(nf):
            a = frases[i] / largo * total; b = frases[i + 1] / largo * total
            tramos.append((hablas[0][0] + a, hablas[0][0] + b))
    def f(ci):
        for i in range(nf):
            if frases[i] <= ci <= frases[i + 1]:
                a, b = tramos[i]
                return a + (ci - frases[i]) / max(1, frases[i + 1] - frases[i]) * (b - a)
        return tramos[-1][1]
    return f, frases

def trozos(texto, frases, maxc=28):
    """Subtítulos cortos: junta frases chicas y parte las largas en pedazos parejos."""
    fr = [(frases[i], frases[i + 1]) for i in range(len(frases) - 1)]
    def largo(a, b): return len(texto[a:b].strip())
    # 1) juntar frases consecutivas mientras entren
    junt = []
    for a, b in fr:
        if junt and largo(junt[-1][0], b) <= maxc and largo(a, b) <= 14:
            junt[-1] = (junt[-1][0], b)
        else: junt.append((a, b))
    # 2) partir las largas en partes parejas por palabras
    out = []
    for a, b in junt:
        L = largo(a, b)
        if L <= maxc: out.append((a, b)); continue
        n = math.ceil(L / maxc)
        ws = [(m.start() + a, m.end() + a) for m in re.finditer(r"\S+", texto[a:b])]
        objetivo = L / n; cur = [ws[0]]
        for w in ws[1:]:
            if (w[1] - cur[0][0]) > objetivo + 4 and len(out) < 999:
                out.append((cur[0][0], cur[-1][1])); cur = [w]
            else: cur.append(w)
        out.append((cur[0][0], cur[-1][1]))
    return [(a, b) for a, b in out if texto[a:b].strip()]

escenas, caps, env_total, voz_eventos = [], [], [], []
t = 0.0
for g in guion:
    sid = g["id"]
    sr, x = leer_wav(f"{V}/voz/{sid}.wav")
    assert sr == SR, sr
    vd = len(x) / sr
    rms = envolvente(x, sr)
    pico = sorted(rms)[int(len(rms) * 0.95)] or 1
    sil = pausas(rms, pico * 0.08)
    lead = LEAD.get(sid, 0) + EXTRA.get(sid, 0) * (sid == "s1")
    vstart = VOICE_IN + lead
    dur = vstart + vd + TAIL + (EXTRA.get(sid, 0) if sid != "s1" else 0)
    f, frases = alinear(g["cap"], vd, sil)
    marks = {}
    for k, w in PALABRAS.get(sid, {}).items():
        i = g["cap"].find(w)
        if i >= 0: marks[k] = round(vstart + f(i), 3)
    for a, b in trozos(g["cap"], frases):
        caps.append({"a": round(t + vstart + f(a), 3), "b": round(t + vstart + f(b) + 0.12, 3), "text": g["cap"][a:b]})
    escenas.append({"id": sid, "start": round(t, 3), "dur": round(dur, 3), "marks": marks})
    voz_eventos.append((t + vstart, x))
    # envolvente normalizada y suavizada para la boca
    n0 = int(round((t + vstart) * FPS))
    while len(env_total) < n0: env_total.append(0)
    prev = 0
    for r in rms:
        v = min(1, max(0, (r / pico - 0.06) * 1.25)) ** 0.8
        prev = prev * 0.35 + v * 0.65
        env_total.append(round(prev, 3))
    t += dur

# los subtítulos no se pisan: cada uno termina cuando empieza el siguiente
for i in range(len(caps) - 1):
    caps[i]["b"] = min(caps[i]["b"], caps[i + 1]["a"])
TOTAL = round(t, 3)
nfr = int(math.ceil(TOTAL * FPS))
while len(env_total) < nfr: env_total.append(0)
json.dump({"fps": FPS, "total": TOTAL, "scenes": escenas, "caps": caps, "env": env_total[:nfr]},
          open(f"{V}/data.json", "w", encoding="utf-8"), ensure_ascii=False)
print("TOTAL", TOTAL, "s |", len(caps), "subtítulos")
for s in escenas: print(s["id"], s["start"], s["dur"], s["marks"])

def guardar(nombre, buf, sr=SR, norm=None):
    pk = max(1e-9, max(abs(v) for v in buf))
    if norm: buf = [v * norm / pk for v in buf]
    with wave.open(f"{V}/{nombre}", "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(struct.pack(f"<{len(buf)}h", *[int(max(-1, min(1, v)) * 32000) for v in buf]))

# ---------- pista de voz ----------
N = int(TOTAL * SR) + SR
voz = [0.0] * N
for t0, x in voz_eventos:
    o = int(t0 * SR)
    for i, v in enumerate(x): voz[o + i] += v
guardar("voz.wav", voz)

# ---------- música original (pop suave, 112 bpm, C - G - Am - F) ----------
random.seed(7)
BPM = 112; beat = 60 / BPM
mus = [0.0] * N
def nota(midi): return 440 * 2 ** ((midi - 69) / 12)
def pluck(t0, f, dur, amp):
    """Karplus-Strong: cuerda pulsada."""
    o = int(t0 * SR); n = int(dur * SR); L = max(2, int(SR / f))
    buf = [random.uniform(-1, 1) for _ in range(L)]
    for i in range(n):
        if o + i >= N: break
        j = i % L; v = buf[j]
        buf[j] = 0.996 * 0.5 * (v + buf[(j + 1) % L])
        mus[o + i] += v * amp * (1 - i / n)
def seno(t0, f, dur, amp, decay=3.0, sweep=None):
    o = int(t0 * SR); n = int(dur * SR); ph = 0
    for i in range(n):
        if o + i >= N: break
        tt = i / SR
        ff = f if sweep is None else sweep[1] + (sweep[0] - sweep[1]) * math.exp(-tt * 28)
        ph += 2 * math.pi * ff / SR
        a = min(1, i / 60) * math.exp(-tt * decay)
        mus[o + i] += math.sin(ph) * amp * a
def ruido(t0, dur, amp, decay, hp=True):
    o = int(t0 * SR); n = int(dur * SR); prev = 0
    for i in range(n):
        if o + i >= N: break
        r = random.uniform(-1, 1); v = r - prev if hp else (prev * 0.7 + r * 0.3); prev = r
        mus[o + i] += v * amp * math.exp(-(i / SR) * decay)

acordes = [[60, 64, 67, 72], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]]
bajos = [36, 31, 33, 29]
arpegio = [0, 1, 2, 3, 2, 1, 2, 3]
compases = int(TOTAL / (4 * beat)) + 1
for c in range(compases):
    t0 = c * 4 * beat; k = c % 4
    intro = c < 1   # primer compás sin batería
    for e in range(8):
        tt = t0 + e * beat / 2
        pluck(tt, nota(acordes[k][arpegio[e]] + 12), 0.9, 0.22)
        if not intro: ruido(tt + (beat / 4 if e % 2 else 0), 0.05, 0.05, 90)          # hi-hat
    for b in (0, 2, 2.5):
        seno(t0 + b * beat, nota(bajos[k]), beat * 0.95, 0.32, decay=2.2)            # bajo
    if not intro:
        for b in (0, 2):
            seno(t0 + b * beat, 50, 0.35, 0.75, decay=9, sweep=(140, 48))             # bombo
        for b in (1, 3):
            ruido(t0 + b * beat, 0.18, 0.18, 22, hp=False)                           # chasquido
    for m in acordes[k][:3]:
        seno(t0, nota(m), 4 * beat, 0.035, decay=0.35)                               # colchón
# fade in/out
fi, fo = int(0.6 * SR), int(2.2 * SR)
for i in range(fi): mus[i] *= i / fi
end = int(TOTAL * SR)
for i in range(fo):
    j = end - fo + i
    if 0 <= j < N: mus[j] *= 1 - i / fo
for j in range(end, N): mus[j] = 0
guardar("musica.wav", mus, norm=0.9)

# ---------- efectos: whoosh en cada cambio de escena + pop cuando aparece Cate ----------
fx = [0.0] * N
def whoosh(tc):
    dur = 0.55; o = int((tc - dur * 0.6) * SR); n = int(dur * SR); lp = 0
    for i in range(n):
        if not 0 <= o + i < N: continue
        p = i / n; cut = 0.03 + 0.5 * p
        lp += cut * (random.uniform(-1, 1) - lp)
        fx[o + i] += lp * math.sin(math.pi * p) ** 2 * 0.9
def blip(tc, f0=520, f1=1100):
    o = int(tc * SR); n = int(0.16 * SR); ph = 0
    for i in range(n):
        if o + i >= N: break
        p = i / n; ph += 2 * math.pi * (f0 + (f1 - f0) * p) / SR
        fx[o + i] += math.sin(ph) * 0.35 * math.exp(-p * 4)
for s in escenas[1:]: whoosh(s["start"])
hola = escenas[0]["marks"].get("hola", 2.4)
blip(escenas[0]["start"] + hola - 0.05)
guardar("fx.wav", fx, norm=0.9)
print("audio ok")
