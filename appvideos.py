# -*- coding: utf-8 -*-
"""
Appvideo — Criador de vídeos de publicidade
-------------------------------------------
• Entrada com a chave GRÁTIS da Groq (console.groq.com/keys)
• Vídeos grátis: roteiro por IA (Groq), imagens grátis, narração em português,
  música e animações montadas pelo próprio app — sem gastar nada.
• Vídeos profissionais: dentro do app a pessoa conecta a chave xAI e usa a
  Grok Imagine (avatar com a própria foto falando, vídeo realista, 720p).

Como rodar:
    pip install streamlit requests pillow numpy imageio-ffmpeg gTTS
    streamlit run app.py

Para o Streamlit Community Cloud, crie um requirements.txt com as linhas:
    streamlit
    requests
    pillow
    numpy
    imageio-ffmpeg
    gTTS

Opcional (Secrets) para cobrar pelos vídeos profissionais:
    PIX_CHAVE = "sua-chave-pix"
    LINK_PAGAMENTO = "https://seu-link-de-pagamento"
    PRECO_VIDEO_PRO = "9,90"

Opcional para imagens grátis mais estáveis (chave grátis em enter.pollinations.ai):
    POLLINATIONS_KEY = "sua-chave-pollinations"
"""

import base64
import io
import json
import math
import os
import random
import re
import subprocess
import tempfile
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import numpy as np
import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

def _instalar(pacote):
    """Instala um pacote na hora, caso o requirements.txt não tenha sido lido."""
    import sys
    for cmd in ([sys.executable, "-m", "pip", "install", "-q", pacote],
                [sys.executable, "-m", "pip", "install", "-q", "--user", pacote],
                ["uv", "pip", "install", "-q", "--python", sys.executable, pacote]):
        try:
            if subprocess.run(cmd, capture_output=True, timeout=240).returncode == 0:
                return True
        except Exception:
            pass
    return False


try:
    import imageio_ffmpeg
except Exception:  # pragma: no cover
    imageio_ffmpeg = None
    if _instalar("imageio-ffmpeg"):
        try:
            import importlib
            importlib.invalidate_caches()
            import imageio_ffmpeg
        except Exception:
            imageio_ffmpeg = None
try:
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe() if imageio_ffmpeg else None
except Exception:  # pragma: no cover
    FFMPEG = None

try:
    from gtts import gTTS
except Exception:  # pragma: no cover
    gTTS = None
    if _instalar("gTTS"):
        try:
            import importlib
            importlib.invalidate_caches()
            from gtts import gTTS
        except Exception:
            gTTS = None

# ============================================================================
# >>>>>>>>>>  COLE SUAS CHAVES AQUI (dono do app)  <<<<<<<<<<
# ============================================================================
# Chave GRÁTIS da Pexels para vídeos reais de fundo: crie em https://www.pexels.com/api/
# e cole entre as aspas. Exemplo: PEXELS_CHAVE = "abc123..."
PEXELS_CHAVE = ""
# Chave grátis opcional da Pollinations (imagens de IA mais estáveis): enter.pollinations.ai
POLLINATIONS_CHAVE = ""
# Cobrança dos vídeos profissionais (deixe vazio para não cobrar)
PIX = ""
LINK_DE_PAGAMENTO = ""
PRECO = "9,90"
# ============================================================================

NOME_APP = "Appvideo"
GROQ_BASE = "https://api.groq.com/openai/v1"
LINK_GROQ = "https://console.groq.com/keys"
XAI_BASE = "https://api.x.ai/v1"
LINK_XAI = "https://console.x.ai"
MODELO_VIDEO = "grok-imagine-video"
MODELO_IMAGEM = "grok-imagine-image"
MODELOS_GROQ_PREFERIDOS = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "moonshotai/kimi-k2-instruct",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
]
FPS = 24
SR = 44100


def config(nome, padrao=""):
    try:
        if nome in st.secrets:
            return str(st.secrets[nome])
    except Exception:
        pass
    return os.environ.get(nome, padrao)


PIX_CHAVE = PIX or config("PIX_CHAVE")
LINK_PAGAMENTO = LINK_DE_PAGAMENTO or config("LINK_PAGAMENTO")
PRECO_VIDEO_PRO = config("PRECO_VIDEO_PRO", PRECO or "9,90")
PEXELS_KEY = PEXELS_CHAVE.strip() or config("PEXELS_KEY")
COBRANCA_ATIVA = bool(PIX_CHAVE or LINK_PAGAMENTO)

# ============================================================================
# Chaves e APIs
# ============================================================================
def limpar_chave(chave):
    chave = (chave or "").strip().strip('"').strip("'").strip()
    if chave.lower().startswith("bearer "):
        chave = chave[7:]
    return "".join(chave.split())


def erro_api(resp):
    try:
        dados = resp.json()
        msg = dados.get("error") or dados.get("message") or dados
        if isinstance(msg, dict):
            msg = msg.get("message", msg)
    except Exception:
        msg = resp.text[:400]
    return f"Erro {resp.status_code}: {msg}"


# ---------------- Groq (grátis) ----------------
def validar_groq(chave):
    if not chave.startswith("gsk_"):
        return False, ("Essa não parece ser uma chave da Groq. A chave grátis da Groq começa "
                       f"com **gsk_**. Crie a sua em [console.groq.com/keys]({LINK_GROQ})."), []
    try:
        r = requests.get(f"{GROQ_BASE}/models",
                         headers={"Authorization": f"Bearer {chave}"}, timeout=20)
    except requests.RequestException as e:
        return False, f"Não foi possível conectar à Groq: {e}", []
    if r.status_code == 200:
        ids = [m.get("id", "") for m in r.json().get("data", [])]
        bloqueados = ("whisper", "tts", "guard", "playai", "orpheus", "distil")
        ids = [i for i in ids if i and not any(b in i.lower() for b in bloqueados)]
        ordem = [m for m in MODELOS_GROQ_PREFERIDOS if m in ids] + \
                sorted(i for i in ids if i not in MODELOS_GROQ_PREFERIDOS)
        return True, "ok", ordem or MODELOS_GROQ_PREFERIDOS
    if r.status_code in (400, 401, 403):
        return False, ("A Groq não reconheceu essa chave. Copie a chave inteira (começa com "
                       "**gsk_**) logo depois de criar. Se perdeu, crie outra."), []
    return False, erro_api(r), []


def chat_groq(mensagens, json_mode=False, temperatura=0.7, modelo=None):
    modelos = [modelo or st.session_state.modelo_chat] + \
              [m for m in st.session_state.modelos_groq if m != (modelo or st.session_state.modelo_chat)][:2]
    ultimo = ""
    for mod in modelos:
        corpo = {"model": mod, "messages": mensagens, "temperature": temperatura}
        if json_mode:
            corpo["response_format"] = {"type": "json_object"}
        r = requests.post(f"{GROQ_BASE}/chat/completions",
                          headers={"Authorization": f"Bearer {st.session_state.groq_key}",
                                   "Content-Type": "application/json"},
                          json=corpo, timeout=120)
        if r.status_code == 400 and json_mode:
            corpo.pop("response_format", None)
            r = requests.post(f"{GROQ_BASE}/chat/completions",
                              headers={"Authorization": f"Bearer {st.session_state.groq_key}",
                                       "Content-Type": "application/json"},
                              json=corpo, timeout=120)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        ultimo = erro_api(r)
        if r.status_code in (401, 403):
            break
    raise RuntimeError(ultimo)


# ---------------- xAI / Grok Imagine (profissional) ----------------
MSG_XAI_ERRADA = (
    "A xAI não reconheceu essa chave. Copie o valor secreto completo (começa com **xai-**), "
    "que aparece só uma vez ao criar. Se perdeu, apague a chave no console e crie outra. "
    "A assinatura do Grok/X Premium não é chave de API."
)


def validar_xai(chave):
    if not chave.startswith("xai-"):
        return False, "A chave da xAI começa com **xai-**. " + MSG_XAI_ERRADA
    try:
        for rota in ("api-key", "models"):
            r = requests.get(f"{XAI_BASE}/{rota}",
                             headers={"Authorization": f"Bearer {chave}"}, timeout=20)
            if r.status_code == 200:
                return True, "ok"
            if r.status_code in (400, 401) or "incorrect api key" in r.text.lower():
                return False, MSG_XAI_ERRADA
            if r.status_code == 403:
                return False, ("A chave existe, mas está sem permissão ou sem créditos. "
                               "Confira as permissões e o saldo em Billing no console da xAI.")
        return False, erro_api(r)
    except requests.RequestException as e:
        return False, f"Não foi possível conectar à xAI: {e}"


def xai_headers():
    return {"Authorization": f"Bearer {st.session_state.xai_key}",
            "Content-Type": "application/json"}


def gerar_imagem_xai(prompt, proporcao="9:16"):
    corpo = {"model": MODELO_IMAGEM, "prompt": prompt, "n": 1, "aspect_ratio": proporcao}
    r = requests.post(f"{XAI_BASE}/images/generations", headers=xai_headers(),
                      json=corpo, timeout=120)
    if r.status_code == 400:
        corpo.pop("aspect_ratio", None)
        r = requests.post(f"{XAI_BASE}/images/generations", headers=xai_headers(),
                          json=corpo, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(erro_api(r))
    item = r.json()["data"][0]
    return item.get("url") or "data:image/png;base64," + item["b64_json"]


def iniciar_video_xai(prompt, duracao, proporcao, resolucao, imagem=None):
    corpo = {"model": MODELO_VIDEO, "prompt": prompt, "duration": int(duracao),
             "aspect_ratio": proporcao, "resolution": resolucao}
    tentativas = [corpo] if not imagem else [dict(corpo, image={"url": imagem}),
                                             dict(corpo, image_url=imagem)]
    ultimo = ""
    for c in tentativas:
        r = requests.post(f"{XAI_BASE}/videos/generations", headers=xai_headers(),
                          json=c, timeout=120)
        if r.status_code in (200, 201, 202):
            dados = r.json()
            rid = dados.get("request_id") or dados.get("id")
            if rid:
                return rid
            ultimo = f"Resposta inesperada: {dados}"
        else:
            ultimo = erro_api(r)
    raise RuntimeError(ultimo)


def aguardar_video_xai(request_id, barra, limite=900):
    inicio = time.time()
    while time.time() - inicio < limite:
        r = requests.get(f"{XAI_BASE}/videos/{request_id}", headers=xai_headers(), timeout=60)
        if r.status_code not in (200, 202):
            raise RuntimeError(erro_api(r))
        dados = r.json()
        status = str(dados.get("status", "")).lower()
        video = dados.get("video") or {}
        url = (video.get("url") if isinstance(video, dict) else None) or dados.get("url")
        if url and status in ("", "done", "completed", "succeeded", "success"):
            barra.progress(100, text="Vídeo pronto!")
            return url
        if status in ("failed", "error", "expired", "cancelled"):
            raise RuntimeError(f"A geração falhou ({status}). {dados.get('error', '')}")
        seg = int(time.time() - inicio)
        barra.progress(min(95, 5 + seg // 3), text=f"Gerando na Grok Imagine… {seg}s")
        time.sleep(5)
    raise RuntimeError("Tempo esgotado esperando o vídeo. Tente novamente.")


def arquivo_para_data_uri(arquivo):
    tipo = arquivo.type or "image/jpeg"
    return f"data:{tipo};base64," + base64.b64encode(arquivo.getvalue()).decode()


def baixar_bytes(url):
    try:
        r = requests.get(url, timeout=120)
        if r.status_code == 200:
            return r.content
    except requests.RequestException:
        pass
    return None


# ============================================================================
# MOTOR DE VÍDEO GRÁTIS (montado pelo próprio app)
# ============================================================================
TEMAS = {
    "Neon roxo": dict(c1=(17, 24, 39), c2=(109, 40, 217), acc=(250, 204, 21),
                      txt=(255, 255, 255), caixa=(17, 24, 39), layout="caixa"),
    "Promoção fogo": dict(c1=(127, 29, 29), c2=(234, 88, 12), acc=(253, 224, 71),
                          txt=(255, 255, 255), caixa=(127, 29, 29), layout="centro"),
    "Luxo dourado": dict(c1=(12, 10, 8), c2=(70, 52, 22), acc=(212, 175, 55),
                         txt=(255, 255, 255), caixa=(12, 10, 8), layout="centro"),
    "Verde natural": dict(c1=(6, 78, 59), c2=(16, 185, 129), acc=(254, 240, 138),
                          txt=(255, 255, 255), caixa=(6, 64, 48), layout="caixa"),
    "Azul confiança": dict(c1=(12, 50, 90), c2=(14, 165, 233), acc=(255, 255, 255),
                           txt=(255, 255, 255), caixa=(12, 50, 90), layout="caixa"),
    "Rosa moderno": dict(c1=(112, 26, 117), c2=(236, 72, 153), acc=(255, 255, 255),
                         txt=(255, 255, 255), caixa=(112, 26, 117), layout="centro"),
    "Clean claro": dict(c1=(226, 232, 240), c2=(248, 250, 252), acc=(15, 23, 42),
                        txt=(15, 23, 42), caixa=(255, 255, 255), layout="caixa"),
}
FONTE_VIDEO = "Vídeos reais de fundo (grátis)"
ESTILOS_IMG = {
    "Foto publicitária realista": "professional advertising photography, photorealistic, sharp focus, studio lighting, high detail",
    "Cinematográfico": "cinematic film still, dramatic lighting, shallow depth of field, rich colors",
    "Ilustração 3D": "3D render, soft lighting, vibrant colors, Pixar-like style",
    "Flat minimalista": "flat vector illustration, minimalist, clean shapes, pastel colors",
    "Neon futurista": "futuristic neon aesthetic, glowing lights, dark background, cyberpunk",
    "Aquarela": "watercolor painting, soft artistic, delicate textures",
}
FORMATOS_GRATIS = {
    "Vertical 9:16 (Reels/TikTok/Shorts)": (720, 1280),
    "Horizontal 16:9 (YouTube)": (1280, 720),
    "Quadrado 1:1 (Feed)": (960, 960),
    "Retrato 4:5 (Feed)": (864, 1080),
}
MUSICAS = ["Animada", "Calma", "Épica", "Emocional", "Sem música"]
TONS = ["Inspirador", "Divertido", "Urgente (promoção)", "Luxuoso", "Emocional",
        "Profissional", "Jovem e descolado"]

FONTES_URL = {
    "bold": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-ExtraBold.ttf",
    "semi": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-SemiBold.ttf",
}
FONTES_SISTEMA = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


@st.cache_resource(show_spinner=False)
def caminhos_fontes():
    pasta = os.path.join(tempfile.gettempdir(), "appvideo_fontes")
    os.makedirs(pasta, exist_ok=True)
    caminhos = {}
    for tipo, url in FONTES_URL.items():
        destino = os.path.join(pasta, f"{tipo}.ttf")
        if not os.path.exists(destino):
            try:
                r = requests.get(url, timeout=20)
                if r.status_code == 200 and len(r.content) > 10000:
                    with open(destino, "wb") as f:
                        f.write(r.content)
            except requests.RequestException:
                pass
        if os.path.exists(destino):
            caminhos[tipo] = destino
    reserva = next((p for p in FONTES_SISTEMA if os.path.exists(p)), None)
    for tipo in FONTES_URL:
        caminhos.setdefault(tipo, reserva)
    return caminhos


def fonte(tipo, tamanho):
    caminho = caminhos_fontes().get(tipo)
    if caminho:
        try:
            return ImageFont.truetype(caminho, tamanho)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=tamanho)
    except Exception:
        return ImageFont.load_default()


def suave(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def quebrar_texto(draw, texto, fnt, largura_max, max_linhas=4):
    palavras, linhas, atual = texto.split(), [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if draw.textlength(teste, font=fnt) <= largura_max or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas[:max_linhas]


def cor_contraste(rgb):
    lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return (15, 23, 42) if lum > 150 else (255, 255, 255)


def para_arrays(camada):
    """Converte camada RGBA em (rgb, alfa, y0, y1) recortada na área usada."""
    arr = np.asarray(camada, dtype=np.float32)
    alfa = arr[..., 3:4] / 255.0
    linhas = np.where(alfa[..., 0].max(axis=1) > 0.003)[0]
    if len(linhas) == 0:
        return None
    y0, y1 = int(linhas[0]), int(linhas[-1]) + 1
    return arr[y0:y1, :, :3].copy(), alfa[y0:y1].copy(), y0, y1


def arte_fundo(W, H, tema, semente):
    """Fundo animável com as cores do tema (usado quando não há imagem)."""
    rnd = random.Random(semente)
    w, h = max(64, W // 4), max(64, H // 4)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ang = rnd.uniform(0, math.pi)
    t = (xx / w) * math.cos(ang) + (yy / h) * math.sin(ang)
    t = (t - t.min()) / (t.max() - t.min() + 1e-6)
    c1, c2 = np.array(tema["c1"], np.float32), np.array(tema["c2"], np.float32)
    img = c1 * (1 - t[..., None]) + c2 * t[..., None]
    base = Image.fromarray(img.clip(0, 255).astype(np.uint8))
    brilho = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(brilho)
    for _ in range(6):
        r = rnd.uniform(0.15, 0.45) * min(w, h)
        cx, cy = rnd.uniform(0, w), rnd.uniform(0, h)
        cor = tema["acc"] if rnd.random() < 0.4 else (255, 255, 255)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=cor + (rnd.randint(25, 60),))
    brilho = brilho.filter(ImageFilter.GaussianBlur(min(w, h) * 0.08))
    base = Image.alpha_composite(base.convert("RGBA"), brilho).convert("RGB")
    return base.resize((W, H), Image.BICUBIC)


POLLINATIONS_KEY = POLLINATIONS_CHAVE.strip() or config("POLLINATIONS_KEY")


# ---------------- vídeos reais de fundo (Pexels, grátis) ----------------
LINK_PEXELS = "https://www.pexels.com/api/"


def chave_pexels():
    """Usa a chave do usuário; se ele não colou, usa a do dono do app (se houver)."""
    try:
        return st.session_state.get("pexels_key") or PEXELS_KEY
    except Exception:
        return PEXELS_KEY


PEXELS_VIDEOS = ["https://api.pexels.com/v1/videos/search",  # endereço novo
                 "https://api.pexels.com/videos/search"]     # antigo (reserva)


def pexels_videos_get(params, chave):
    """Busca vídeos no endereço novo da Pexels; se falhar, tenta o antigo."""
    r = None
    for url in PEXELS_VIDEOS:
        r = requests.get(url, params=params, headers={"Authorization": chave}, timeout=20)
        if r.status_code in (200, 401, 403, 429):
            return r
    return r


def validar_pexels(chave):
    try:
        r = pexels_videos_get({"query": "nature", "per_page": 1}, chave)
    except requests.RequestException:
        return True, ""  # sem conexão para testar agora: aceita e tenta na hora do vídeo
    if r.status_code == 200:
        return True, ""
    if r.status_code in (401, 403):
        return False, (f"A Pexels não reconheceu essa chave. Copie a chave inteira em "
                       f"[pexels.com/api]({LINK_PEXELS}) ou deixe o campo vazio para entrar sem ela.")
    if r.status_code == 429:
        return True, ""
    return True, ""


def buscar_video_pexels(busca, W, H, usados):
    """Procura e baixa um vídeo grátis da Pexels. Retorna caminho do .mp4 ou None."""
    chave = chave_pexels()
    if not chave or not busca:
        return None
    orient = "portrait" if H > W * 1.1 else "landscape" if W > H * 1.1 else "square"
    for consulta, orientacao in ((busca, orient), (busca, None),
                                 (" ".join(busca.split()[:2]), None)):
        try:
            params = {"query": consulta, "per_page": 12, "size": "medium"}
            if orientacao:
                params["orientation"] = orientacao
            r = pexels_videos_get(params, chave)
            if r.status_code != 200:
                continue
            videos = [v for v in r.json().get("videos", [])
                      if v.get("id") not in usados and v.get("duration", 0) >= 3]
            for v in videos:
                arquivos = [f for f in v.get("video_files", [])
                            if f.get("link") and (f.get("file_type") or "").endswith("mp4")
                            and f.get("width") and f.get("height")]
                if not arquivos:
                    continue
                alvo = min(W, H)
                arquivos.sort(key=lambda f: (min(f["width"], f["height"]) < alvo * 0.9,
                                             abs(min(f["width"], f["height"]) - alvo)))
                escolhido = arquivos[0]
                destino = os.path.join(tempfile.mkdtemp(prefix="appvideo_pexels_"), "fundo.mp4")
                with requests.get(escolhido["link"], stream=True, timeout=60) as rv:
                    if rv.status_code != 200:
                        continue
                    total = 0
                    with open(destino, "wb") as f:
                        for parte in rv.iter_content(1 << 16):
                            total += len(parte)
                            if total > 60 * 1024 * 1024:
                                break
                            f.write(parte)
                usados.add(v.get("id"))
                return destino
        except Exception:
            continue
    return None


class FonteVideo:
    """Lê os quadros de um vídeo já recortado no tamanho do anúncio, sob demanda."""

    def __init__(self, caminho, W, H):
        self.W, self.H = W, H
        self.tam = W * H * 3
        self.proc = subprocess.Popen(
            [FFMPEG, "-loglevel", "error", "-stream_loop", "-1", "-i", caminho,
             "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
             "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.idx = -1
        self.atual = np.zeros((H, W, 3), np.float32)

    def quadro(self, k):
        while self.idx < k and self.proc:
            dados = self.proc.stdout.read(self.tam)
            if len(dados) < self.tam:
                self.fechar()
                break
            self.atual = np.frombuffer(dados, np.uint8).reshape(self.H, self.W, 3).astype(np.float32)
            self.idx += 1
        return self.atual.copy()

    def fechar(self):
        if self.proc:
            try:
                self.proc.stdout.close()
                self.proc.kill()
                self.proc.wait(timeout=5)
            except Exception:
                pass
            self.proc = None


def imagem_gratis_ia(prompt, W, H, semente, prazo=None):
    """Imagem grátis via Pollinations. Tenta vários endereços. Retorna PIL ou None."""
    p = quote(prompt[:400])
    params = f"width={W}&height={H}&nologo=true&seed={semente}&model=flux"
    if POLLINATIONS_KEY:
        params += f"&key={POLLINATIONS_KEY}"
    urls = [
        f"https://gen.pollinations.ai/image/{p}?{params}",
        f"https://image.pollinations.ai/prompt/{p}?{params}",
        f"https://pollinations.ai/p/{p}?{params}",
    ]
    prazo = prazo or (time.time() + 90)
    for tentativa in range(3):
        limitado = False
        for url in urls:
            resta = prazo - time.time()
            if resta < 5:
                return None
            try:
                r = requests.get(url, timeout=min(45, resta), headers={"User-Agent": "Appvideo/1.0"})
                if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                    return Image.open(io.BytesIO(r.content)).convert("RGB")
                if r.status_code == 429:
                    limitado = True
            except Exception:
                pass
        if not limitado:
            break
        espera = 6 + tentativa * 6  # o serviço grátis pediu para esperar
        if prazo - time.time() < espera + 10:
            return None
        time.sleep(espera)
    return None


def foto_pexels(busca, W, H, usadas):
    """Foto real grátis da Pexels (usa a chave Pexels do usuário). Retorna PIL ou None."""
    chave = chave_pexels()
    if not chave or not busca:
        return None
    orient = "portrait" if H > W * 1.1 else "landscape" if W > H * 1.1 else "square"
    for consulta in (busca, " ".join(busca.split()[:2])):
        try:
            r = requests.get("https://api.pexels.com/v1/search",
                             params={"query": consulta, "orientation": orient, "per_page": 15},
                             headers={"Authorization": chave}, timeout=20)
            if r.status_code != 200:
                continue
            for foto in r.json().get("photos", []):
                if foto.get("id") in usadas:
                    continue
                src = foto.get("src", {})
                url = src.get("large2x") or src.get("large") or src.get("original")
                dados = baixar_bytes(url) if url else None
                if dados:
                    usadas.add(foto.get("id"))
                    return Image.open(io.BytesIO(dados)).convert("RGB")
        except Exception:
            continue
    return None


def imagem_xai_pil(prompt, W, H):
    """Imagem pela Grok (chave xAI conectada) — custa centavos. Retorna PIL ou None."""
    try:
        prop = "9:16" if H > W * 1.2 else "16:9" if W > H * 1.2 else "1:1"
        ref = gerar_imagem_xai(prompt, prop)
        if ref.startswith("data:"):
            dados = base64.b64decode(ref.split(",", 1)[1])
        else:
            dados = baixar_bytes(ref)
        return Image.open(io.BytesIO(dados)).convert("RGB") if dados else None
    except Exception:
        return None


# ---------------- camadas de texto ----------------
def camada_marca(W, H, tema, marca):
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if not marca:
        return camada
    d = ImageDraw.Draw(camada)
    m = int(min(W, H) * 0.045)
    fnt = fonte("semi", max(16, int(min(W, H) * 0.032)))
    texto = marca.upper()[:28]
    tw = d.textlength(texto, font=fnt)
    alt = fnt.size * 1.9
    d.rounded_rectangle([m, m, m + tw + fnt.size * 1.4, m + alt],
                        radius=int(alt / 2), fill=tema["acc"] + (235,))
    d.text((m + fnt.size * 0.7, m + alt / 2), texto, font=fnt,
           fill=cor_contraste(tema["acc"]), anchor="lm")
    return camada


def camada_texto_cena(W, H, tema, texto):
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if not texto:
        return camada
    d = ImageDraw.Draw(camada)
    menor = min(W, H)
    if tema["layout"] == "centro":
        fnt = fonte("bold", int(menor * 0.088))
        linhas = quebrar_texto(d, texto.upper(), fnt, W * 0.84)
        alt_linha = fnt.size * 1.15
        y = H * 0.5 - alt_linha * len(linhas) / 2
        sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ds = ImageDraw.Draw(sombra)
        for i, ln in enumerate(linhas):
            ds.text((W / 2, y + i * alt_linha + 4), ln, font=fnt, fill=(0, 0, 0, 200), anchor="mt")
        sombra = sombra.filter(ImageFilter.GaussianBlur(menor * 0.012))
        camada = Image.alpha_composite(camada, sombra)
        d = ImageDraw.Draw(camada)
        for i, ln in enumerate(linhas):
            d.text((W / 2, y + i * alt_linha), ln, font=fnt, fill=tema["txt"] + (255,), anchor="mt")
        yb = y + alt_linha * len(linhas) + menor * 0.025
        d.rounded_rectangle([W / 2 - menor * 0.09, yb, W / 2 + menor * 0.09, yb + menor * 0.014],
                            radius=int(menor * 0.007), fill=tema["acc"] + (255,))
    else:
        fnt = fonte("bold", int(menor * 0.068))
        pad = menor * 0.045
        largura = W * 0.86
        linhas = quebrar_texto(d, texto, fnt, largura - 2 * pad)
        alt_linha = fnt.size * 1.22
        alt_caixa = alt_linha * len(linhas) + 2 * pad
        base_y = H * (0.86 if H > W else 0.9)
        x0, y0 = (W - largura) / 2, base_y - alt_caixa
        alfa_caixa = 230 if tema["caixa"] == (255, 255, 255) else 205
        d.rounded_rectangle([x0, y0, x0 + largura, base_y], radius=int(menor * 0.035),
                            fill=tema["caixa"] + (alfa_caixa,))
        d.rounded_rectangle([x0, y0, x0 + menor * 0.018, base_y], radius=int(menor * 0.009),
                            fill=tema["acc"] + (255,))
        for i, ln in enumerate(linhas):
            d.text((x0 + pad + menor * 0.01, y0 + pad + i * alt_linha), ln, font=fnt,
                   fill=tema["txt"] + (255,))
    return camada


def fundo_cta(W, H, tema, produto, cta, contato):
    fundo = arte_fundo(int(W * 1.15), int(H * 1.15), tema, 999)
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    menor = min(W, H)
    cor_txt = cor_contraste(tema["c1"]) if tema["caixa"] == (255, 255, 255) else (255, 255, 255)
    f1 = fonte("bold", int(menor * 0.095))
    linhas = quebrar_texto(d, (produto or "").upper(), f1, W * 0.86, 3)
    alt = f1.size * 1.12
    y = H * 0.40 - alt * len(linhas) / 2
    for i, ln in enumerate(linhas):
        d.text((W / 2, y + i * alt), ln, font=f1, fill=cor_txt + (255,), anchor="mt")
    y += alt * len(linhas) + menor * 0.06
    if cta:
        f2 = fonte("bold", int(menor * 0.058))
        lcta = quebrar_texto(d, cta, f2, W * 0.74, 2)
        alt2 = f2.size * 1.2
        bw = max(d.textlength(l, font=f2) for l in lcta) + menor * 0.12
        bh = alt2 * len(lcta) + menor * 0.06
        d.rounded_rectangle([W / 2 - bw / 2, y, W / 2 + bw / 2, y + bh], radius=int(bh / 2.2),
                            fill=tema["acc"] + (255,))
        for i, ln in enumerate(lcta):
            d.text((W / 2, y + menor * 0.03 + i * alt2), ln, font=f2,
                   fill=cor_contraste(tema["acc"]) + (255,), anchor="mt")
        y += bh + menor * 0.05
    if contato:
        f3 = fonte("semi", int(menor * 0.045))
        d.text((W / 2, y), contato, font=f3, fill=cor_txt + (240,), anchor="mt")
    return fundo, camada


# ---------------- áudio ----------------
def decodificar_audio(dados, acelerar=1.0):
    if not FFMPEG:
        return None
    filtro = ["-filter:a", f"atempo={acelerar}"] if abs(acelerar - 1) > 0.01 else []
    proc = subprocess.run([FFMPEG, "-loglevel", "error", "-i", "pipe:0", *filtro,
                           "-f", "s16le", "-ac", "1", "-ar", str(SR), "pipe:1"],
                          input=dados, capture_output=True, timeout=120)
    if proc.returncode != 0 or not proc.stdout:
        return None
    return np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def narrar(texto):
    if not gTTS or not texto.strip():
        return None
    buf = io.BytesIO()
    gTTS(texto, lang="pt", tld="com.br").write_to_fp(buf)
    return decodificar_audio(buf.getvalue(), acelerar=1.12)


def nota(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def sintetizar_musica(duracao, estilo, semente=7):
    """Trilha instrumental original gerada por código (sem direitos autorais)."""
    n = int(duracao * SR)
    if estilo == "Sem música" or n <= 0:
        return np.zeros(n, np.float32)
    rnd = np.random.default_rng(semente)
    maior = [[48, 52, 55], [43, 47, 50], [45, 48, 52], [41, 45, 48]]  # C G Am F
    menor = [[45, 48, 52], [41, 45, 48], [48, 52, 55], [43, 47, 50]]  # Am F C G
    cfg = {
        "Animada": dict(acordes=maior, bpm=116, bateria=True, arpejo=True, pad=0.18),
        "Calma": dict(acordes=maior, bpm=76, bateria=False, arpejo=True, pad=0.28),
        "Épica": dict(acordes=menor, bpm=90, bateria=True, arpejo=False, pad=0.34),
        "Emocional": dict(acordes=menor, bpm=72, bateria=False, arpejo=True, pad=0.26),
    }[estilo]
    batida = 60 / cfg["bpm"]
    compasso = batida * 4
    saida = np.zeros(n, np.float32)
    t_comp = np.arange(int(compasso * SR)) / SR
    env_pad = np.minimum(1, t_comp / 0.35) * np.minimum(1, (compasso - t_comp) / 0.3)
    k = 0
    pos = 0
    while pos < n:
        acorde = cfg["acordes"][k % 4]
        seg = np.zeros_like(t_comp)
        for m in acorde + [acorde[0] + 12]:
            f = nota(m + 12)
            seg += np.sin(2 * np.pi * f * t_comp) + 0.3 * np.sin(2 * np.pi * f * 2.003 * t_comp)
        seg *= env_pad * cfg["pad"] / 4
        seg += 0.22 * np.sin(2 * np.pi * nota(acorde[0] - 12) * t_comp) * env_pad
        if cfg["arpejo"]:
            passo = batida / 2
            notas = acorde + [acorde[1] + 12, acorde[2] + 12]
            for j in range(int(compasso / passo)):
                ini = int(j * passo * SR)
                tt = np.arange(int(passo * 1.8 * SR)) / SR
                f = nota(notas[j % len(notas)] + 24)
                som = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 6) * 0.12
                fim = min(len(seg), ini + len(som))
                seg[ini:fim] += som[:fim - ini]
        if cfg["bateria"]:
            for j in range(4):
                ini = int(j * batida * SR)
                tt = np.arange(int(0.3 * SR)) / SR
                freq = 45 + 90 * np.exp(-tt * 30)
                bumbo = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-tt * 9) * 0.55
                fim = min(len(seg), ini + len(bumbo))
                seg[ini:fim] += bumbo[:fim - ini]
                ini2 = int((j + 0.5) * batida * SR)
                tt2 = np.arange(int(0.06 * SR)) / SR
                ruido = np.diff(rnd.standard_normal(len(tt2) + 1)).astype(np.float32)
                chimbal = ruido * np.exp(-tt2 * 70) * 0.07
                fim2 = min(len(seg), ini2 + len(chimbal))
                if ini2 < len(seg):
                    seg[ini2:fim2] += chimbal[:fim2 - ini2]
        fim = min(n, pos + len(seg))
        saida[pos:fim] += seg[:fim - pos]
        pos += len(seg)
        k += 1
    fade_in, fade_out = int(0.8 * SR), int(1.6 * SR)
    saida[:fade_in] *= np.linspace(0, 1, min(fade_in, n))[:len(saida[:fade_in])]
    if n > fade_out:
        saida[-fade_out:] *= np.linspace(1, 0, fade_out)
    pico = np.abs(saida).max() or 1
    return saida / pico


def salvar_wav(caminho, audio):
    pico = np.abs(audio).max() if len(audio) else 0
    if pico > 0.95:
        audio = audio * (0.95 / pico)
    dados = (audio * 32767).astype(np.int16).tobytes()
    with wave.open(caminho, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(dados)


# ---------------- montagem ----------------
def criar_video_gratis(cenas, opc, fotos, progresso):
    """
    cenas: lista de dicts {texto_tela, narracao, imagem}
    opc: produto, cta, contato, formato, tema, estilo_img, fonte_img, musica, narracao(bool), dur_min
    fotos: lista de PIL (fotos do usuário)
    progresso(pct, texto)
    """
    if not imageio_ffmpeg:
        raise RuntimeError(
            "o servidor não instalou o imageio-ffmpeg. No GitHub, confira se o arquivo "
            "requirements.txt está na MESMA pasta do app.py, com esse nome exato, e depois "
            "clique em 'Reboot app' no Streamlit Cloud.")
    W, H = FORMATOS_GRATIS[opc["formato"]]
    tema = TEMAS[opc["tema"]]
    S = 1.15
    T = 0.5  # transição
    caminhos_fontes()

    # 1) narração
    narracoes = [None] * (len(cenas) + 1)
    if opc["narracao"]:
        if gTTS is None:
            st.warning("Narração indisponível (instale gTTS). O vídeo seguirá só com música.")
        else:
            progresso(4, "Gravando a narração em português…")
            textos = [c.get("narracao", "") for c in cenas] + [opc.get("cta", "")]
            try:
                with ThreadPoolExecutor(max_workers=4) as ex:
                    narracoes = list(ex.map(lambda t: narrar(t) if t else None, textos))
            except Exception as e:
                st.warning(f"Não foi possível gerar a narração agora ({e}). Seguindo sem voz.")
                narracoes = [None] * (len(cenas) + 1)

    # 2) durações
    duracoes = []
    for i in range(len(cenas) + 1):
        minimo = opc["dur_min"] if i < len(cenas) else 3.6
        voz = narracoes[i]
        duracoes.append(max(minimo, (len(voz) / SR + 0.9) if voz is not None else 0))

    # 3) vídeos de fundo / imagens
    imagens = [None] * len(cenas)
    videos = [None] * len(cenas)
    fotos = list(fotos or [])
    modo_video = opc["fonte_img"] == FONTE_VIDEO
    if modo_video:
        if not chave_pexels():
            st.info("Para vídeos reais de fundo, conecte sua chave Pexels grátis. "
                    "Usei imagens de IA no lugar.")
        else:
            usados = set()
            for i, cena in enumerate(cenas):
                progresso(10 + int(14 * i / len(cenas)),
                          f"Buscando vídeo de fundo {i + 1} de {len(cenas)}…")
                busca = (cena.get("busca_video") or cena.get("imagem") or opc["produto"])
                videos[i] = buscar_video_pexels(" ".join(str(busca).split()[:5]), W, H, usados)
            if not any(videos):
                st.info("Não encontrei vídeos de fundo agora; usei imagens no lugar.")
    else:
        for i in range(len(cenas)):
            if fotos and (opc["fonte_img"] == "Só minhas fotos" or i < len(fotos)):
                imagens[i] = fotos[i % len(fotos)]
    progresso(25, "Preparando as imagens…")
    if opc["fonte_img"] in ("Imagens geradas por IA (grátis)", FONTE_VIDEO):
        faltam = [i for i in range(len(cenas)) if imagens[i] is None and videos[i] is None]
        estilo = ESTILOS_IMG[opc["estilo_img"]]

        if faltam:
            # uma imagem de cada vez: o gerador grátis recusa pedidos simultâneos
            prazo_total = time.time() + 40 + 35 * len(faltam)
            for n, i in enumerate(faltam):
                if time.time() > prazo_total - 10:
                    break
                progresso(25 + int(10 * n / len(faltam)),
                          f"Criando imagem {n + 1} de {len(faltam)} com IA grátis…")
                p = f"{cenas[i].get('imagem') or opc['produto']}, {estilo}, no text, no letters, no watermark"
                imagens[i] = imagem_gratis_ia(p, W, H, 1000 + i * 17, min(prazo_total, time.time() + 75))
            ainda = [i for i in faltam if imagens[i] is None]
            if ainda and chave_pexels():
                progresso(35, "Buscando fotos reais grátis para as cenas que faltaram…")
                usadas = set()
                for i in ainda:
                    busca = cenas[i].get("busca_video") or cenas[i].get("imagem") or opc["produto"]
                    imagens[i] = foto_pexels(" ".join(str(busca).split()[:5]), W, H, usadas)
                ainda = [i for i in faltam if imagens[i] is None]
            if ainda and opc.get("usar_xai") and st.session_state.get("xai_key"):
                progresso(24, "Gerando as imagens que faltaram com a Grok…")
                for i in ainda:
                    p = f"{cenas[i].get('imagem') or opc['produto']}, {estilo}, no text"
                    imagens[i] = imagem_xai_pil(p, W, H)
                ainda = [i for i in faltam if imagens[i] is None]
            if ainda and fotos:
                for j, i in enumerate(ainda):
                    imagens[i] = fotos[j % len(fotos)]
                ainda = []
            if ainda:
                dica = ("conecte sua chave Pexels grátis para usar fotos e vídeos reais, "
                        "ou envie fotos do seu produto") if not chave_pexels() else \
                       "envie fotos do seu produto ou tente de novo em alguns minutos"
                st.info(f"O gerador de imagens grátis está sobrecarregado agora e não respondeu "
                        f"para {len(ainda)} de {len(faltam)} cenas; usei fundos do tema no lugar. "
                        f"Dica: {dica}.")

    # 4) cenas prontas
    progresso(30, "Montando as cenas…")
    marca = camada_marca(W, H, tema, opc["produto"])
    marca_arr = para_arrays(marca)
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    if tema["layout"] == "centro":
        sombra = (0.42 + 0.18 * np.abs(yy - 0.5) * 2).astype(np.float32)
    else:
        sombra = (np.clip((yy - 0.45) / 0.55, 0, 1) ** 1.3 * 0.62 + 0.06).astype(np.float32)
    sombra = np.broadcast_to(sombra, (H, 1, 1))

    blocos = []
    inicio = 0.0
    for i, cena in enumerate(cenas):
        if videos[i]:
            base = None
        else:
            img = imagens[i] if imagens[i] is not None else arte_fundo(W, H, tema, i * 31 + 5)
            base = ImageOps.fit(img.convert("RGB"), (int(W * S), int(H * S)), Image.LANCZOS)
        blocos.append(dict(base=base, video=videos[i], fonte=None,
                           dur=duracoes[i], inicio=inicio, zoom_in=(i % 2 == 0),
                           pan=((-1) ** i * 0.6, (-1) ** (i // 2) * 0.4),
                           texto=para_arrays(camada_texto_cena(W, H, tema, cena.get("texto_tela", ""))),
                           sombra=True, marca=True))
        inicio += duracoes[i] - T
    fundo, cam_cta = fundo_cta(W, H, tema, opc["produto"], opc.get("cta", ""), opc.get("contato", ""))
    blocos.append(dict(base=fundo, video=None, fonte=None,
                       dur=duracoes[-1], inicio=inicio, zoom_in=True, pan=(0, 0),
                       texto=para_arrays(cam_cta), sombra=False, marca=False))
    total = inicio + duracoes[-1]

    def quadro_cena(b, tl):
        p = max(0.0, min(1.0, tl / b["dur"]))
        if b["video"]:
            if b["fonte"] is None:
                b["fonte"] = FonteVideo(b["video"], W, H)
            arr = b["fonte"].quadro(max(0, int(tl * FPS)))
        else:
            BW, BH = b["base"].size
            z = 1 + (S - 1) * suave(p) if b["zoom_in"] else S - (S - 1) * suave(p)
            ww, wh = BW / z, BH / z
            mx, my = (BW - ww) / 2, (BH - wh) / 2
            cx = BW / 2 + b["pan"][0] * mx * (p * 2 - 1)
            cy = BH / 2 + b["pan"][1] * my * (p * 2 - 1)
            caixa = (cx - ww / 2, cy - wh / 2, cx + ww / 2, cy + wh / 2)
            arr = np.asarray(b["base"].resize((W, H), Image.BILINEAR, box=caixa), dtype=np.float32)
        if b["sombra"]:
            arr = arr * (1 - sombra)
        if b["marca"] and marca_arr:
            rgb, a, y0, y1 = marca_arr
            arr[y0:y1] = arr[y0:y1] * (1 - a) + rgb * a
        if b["texto"]:
            rgb, a, y0, y1 = b["texto"]
            f = suave((tl - 0.25) / 0.55)
            if f > 0:
                dy = int((1 - f) * H * 0.035)
                y0d, y1d = min(H, y0 + dy), min(H, y1 + dy)
                k = y1d - y0d
                if k > 0:
                    af = a[:k] * f
                    arr[y0d:y1d] = arr[y0d:y1d] * (1 - af) + rgb[:k] * af
        return arr

    # 5) áudio
    progresso(35, "Compondo a trilha sonora…")
    n_amostras = int(total * SR) + SR // 2
    musica = sintetizar_musica(n_amostras / SR, opc["musica"])
    tem_voz = any(v is not None for v in narracoes)
    mix = musica * (0.16 if tem_voz else 0.55)
    for i, v in enumerate(narracoes):
        if v is None:
            continue
        ini = int((blocos[i]["inicio"] + 0.3) * SR)
        fim = min(len(mix), ini + len(v))
        if fim > ini:
            mix[ini:fim] += v[:fim - ini] * 0.95
    tem_audio = tem_voz or opc["musica"] != "Sem música"

    pasta = tempfile.mkdtemp(prefix="appvideo_")
    caminho_wav = os.path.join(pasta, "audio.wav")
    caminho_mp4 = os.path.join(pasta, "video.mp4")
    if tem_audio:
        salvar_wav(caminho_wav, mix[:int(total * SR)])

    # 6) renderização
    n_quadros = int(total * FPS)
    gerador = imageio_ffmpeg.write_frames(
        caminho_mp4, (W, H), fps=FPS, codec="libx264", quality=None,
        macro_block_size=1, ffmpeg_log_level="error",
        output_params=["-preset", "veryfast", "-crf", "21", "-movflags", "+faststart"],
        audio_path=caminho_wav if tem_audio else None,
        audio_codec="aac" if tem_audio else None,
    )
    gerador.send(None)
    try:
        for q in range(n_quadros):
            t = q / FPS
            ativos = [b for b in blocos if b["inicio"] <= t < b["inicio"] + b["dur"]] or [blocos[-1]]
            quadro = quadro_cena(ativos[0], t - ativos[0]["inicio"])
            if len(ativos) > 1:
                prox = ativos[1]
                mistura = suave((t - prox["inicio"]) / T)
                quadro = quadro * (1 - mistura) + quadro_cena(prox, t - prox["inicio"]) * mistura
            gerador.send(np.ascontiguousarray(quadro.clip(0, 255).astype(np.uint8)))
            for b in blocos:
                if b["fonte"] is not None and t >= b["inicio"] + b["dur"]:
                    b["fonte"].fechar()
            if q % 12 == 0:
                progresso(40 + int(58 * q / n_quadros), f"Renderizando o vídeo… {int(100 * q / n_quadros)}%")
    finally:
        gerador.close()
        for b in blocos:
            if b["fonte"] is not None:
                b["fonte"].fechar()

    with open(caminho_mp4, "rb") as f:
        dados = f.read()
    progresso(100, "Vídeo pronto!")
    return dados


def extrair_json(texto):
    try:
        return json.loads(texto)
    except Exception:
        m = re.search(r"\{.*\}", texto, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def gerar_roteiro(produto, descricao, publico, tom, n, cta, contato):
    sistema = (
        "Você é redator publicitário brasileiro e diretor de arte. Crie um roteiro de anúncio em "
        f"vídeo curto com exatamente {n} cenas. Responda APENAS com JSON neste formato: "
        '{"cenas":[{"texto_tela":"frase de impacto com no máximo 7 palavras",'
        '"narracao":"1 ou 2 frases curtas para o locutor, em português do Brasil, no máximo 22 palavras",'
        '"imagem":"descrição em inglês de uma foto publicitária para esta cena, sem texto escrito",'
        '"busca_video":"2 a 4 palavras em inglês para buscar um vídeo de banco de imagens desta cena, ex.: burger grill closeup"}],'
        '"cta":"chamada final curta, no máximo 6 palavras"}. '
        "A primeira cena é um gancho que prende a atenção, as do meio mostram benefícios e a "
        "última reforça a oferta. Não invente preços nem promoções que não foram informados."
    )
    usuario = (f"Produto/serviço: {produto}\nDetalhes: {descricao or '-'}\nPúblico: {publico or '-'}\n"
               f"Tom: {tom}\nCTA desejado: {cta or 'crie um'}\nContato: {contato or '-'}")
    dados = extrair_json(chat_groq([{"role": "system", "content": sistema},
                                    {"role": "user", "content": usuario}],
                                   json_mode=True, temperatura=0.8))
    cenas = []
    for c in dados.get("cenas", [])[:n]:
        cenas.append({"texto_tela": str(c.get("texto_tela", ""))[:80],
                      "narracao": str(c.get("narracao", ""))[:220],
                      "imagem": str(c.get("imagem", ""))[:300],
                      "busca_video": str(c.get("busca_video", ""))[:60]})
    if not cenas:
        raise RuntimeError("A IA não devolveu o roteiro. Tente de novo.")
    return cenas, (cta or str(dados.get("cta", "")))[:60]


# ============================================================================
# Interface
# ============================================================================
st.set_page_config(page_title=NOME_APP, page_icon="🎬", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem; max-width: 1200px;}
    .hero {padding: 1.4rem 1.6rem; border-radius: 16px;
           background: linear-gradient(135deg,#111827 0%,#312e81 55%,#7c3aed 100%);
           color: #fff; margin-bottom: 1rem;}
    .hero h1 {margin: 0; font-size: 2rem; color:#fff;}
    .hero p {margin: .3rem 0 0; opacity: .85;}
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {display: none !important;}
    @media (max-width: 640px) {
      .block-container {padding: 1rem .8rem 2rem;}
      .hero {padding: 1rem 1.1rem;} .hero h1 {font-size: 1.5rem;}
      [data-baseweb="tab-list"] {overflow-x: auto; flex-wrap: nowrap;}
      [data-baseweb="tab"] {white-space: nowrap; font-size: .85rem;}
    }
    .nota {border-left: 4px solid #7c3aed; background: rgba(124,58,237,.08);
           padding: .8rem 1rem; border-radius: 8px; margin: .6rem 0 1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

for k, v in {"logado": False, "nome": "", "groq_key": "", "xai_key": "",
             "modelos_groq": MODELOS_GROQ_PREFERIDOS, "modelo_chat": MODELOS_GROQ_PREFERIDOS[0],
             "chat": [], "galeria": [], "cenas": [], "cta_gerado": "",
             "ultimo_gratis": None, "ultimo_pro": None, "pexels_key": ""}.items():
    st.session_state.setdefault(k, v)


def hero(sub):
    st.markdown(f'<div class="hero"><h1>🎬 {NOME_APP}</h1><p>{sub}</p></div>',
                unsafe_allow_html=True)


def tela_login():
    hero("Crie vídeos de publicidade grátis com Inteligência Artificial.")
    col1, col2 = st.columns([1.1, 1])
    with col1:
        st.subheader("Entrar")
        with st.form("login"):
            nome = st.text_input("Seu nome", placeholder="Ex.: Maria Silva")
            chave = st.text_input("1️⃣ Chave Groq (grátis) — para o roteiro e o assistente",
                                  type="password", placeholder="gsk_...")
            st.markdown(f"👉 **[Pegar minha chave Groq grátis]({LINK_GROQ})**")
            chave_px = st.text_input("2️⃣ Chave Pexels (grátis) — para os vídeos reais de fundo",
                                     type="password", placeholder="cole aqui sua chave Pexels")
            st.markdown(f"👉 **[Pegar minha chave Pexels grátis]({LINK_PEXELS})**")
            entrar = st.form_submit_button("Entrar no app", type="primary")
        st.caption("As duas chaves são grátis e não pedem cartão. Se você ainda não tem, "
                   "siga o passo a passo abaixo — leva uns 3 minutos.")
        with st.expander("🔑 Passo a passo: pegar a chave Groq e colar no campo 1️⃣", expanded=True):
            st.markdown(
                f"1. Toque aqui: **[abrir console.groq.com/keys]({LINK_GROQ})** (abre em outra aba).\n"
                "2. Entre com sua conta **Google** ou com seu **e-mail**.\n"
                "3. Toque no botão **Create API Key**.\n"
                "4. Em *Display name*, escreva **Appvideo** e toque em **Submit**.\n"
                "5. Vai aparecer uma chave comprida que começa com **gsk_**. Toque em **Copy** "
                "(ela só aparece uma vez — se fechar, crie outra).\n"
                "6. Volte para esta aba e **cole no campo 1️⃣ Chave Groq** acima."
            )
        with st.expander("🎥 Passo a passo: pegar a chave Pexels e colar no campo 2️⃣"):
            st.markdown(
                f"1. Toque aqui: **[abrir pexels.com/api]({LINK_PEXELS})** (abre em outra aba).\n"
                "2. Toque em **Join** e crie sua conta grátis (ou entre com Google).\n"
                "3. Volte em **pexels.com/api** e toque em **Your API Key** (ou *Get Started*).\n"
                "4. Preencha o formulário: em *project name*, escreva **Appvideo**; em *description*, "
                "escreva **criar vídeos de anúncio**. Aceite os termos e envie.\n"
                "5. A sua chave aparece na tela. Toque nela e **copie o texto inteiro**.\n"
                "6. Volte para esta aba e **cole no campo 2️⃣ Chave Pexels** acima.\n\n"
                "É opcional: sem ela o app funciona, mas o fundo dos vídeos usa imagens em vez de "
                "vídeos reais. Você também pode colar depois, dentro da aba **Criar vídeo grátis**."
            )
        st.caption("📱 No celular: depois de copiar, toque e segure no campo e escolha **Colar**.")
        if entrar:
            chave, chave_px = limpar_chave(chave), limpar_chave(chave_px)
            if not nome.strip() or not chave:
                st.error("Preencha seu nome e sua chave Groq.")
                return
            with st.spinner("Verificando suas chaves…"):
                ok, msg, modelos = validar_groq(chave)
                ok_px, msg_px = validar_pexels(chave_px) if chave_px else (True, "")
            if not ok:
                st.error(msg)
            elif not ok_px:
                st.error(msg_px)
            else:
                st.session_state.update(logado=True, nome=nome.strip(), groq_key=chave,
                                        pexels_key=chave_px, modelos_groq=modelos,
                                        modelo_chat=modelos[0])
                st.rerun()
    with col2:
        st.subheader("Como funciona")
        st.markdown(
            "1. Entre com seu nome e sua chave **Groq grátis**.\n"
            "2. Descreva seu produto — a IA escreve o roteiro.\n"
            "3. Escolha formato, tema, imagens, narração e música.\n"
            "4. Clique em **Criar vídeo grátis** e baixe o MP4.\n\n"
            "Quer vídeo **ultra profissional** com seu avatar falando? Dentro do app, em "
            "**Criar vídeos pagos**, você conecta sua chave xAI e usa a Grok Imagine."
        )
        st.caption("Suas chaves ficam só nesta sessão do navegador e não são salvas.")


def salvar_galeria(titulo, tipo, dados=None, url=None):
    st.session_state.galeria.insert(0, {"titulo": titulo, "tipo": tipo, "bytes": dados,
                                        "url": url, "hora": time.strftime("%d/%m %H:%M")})


# ---------------- aba grátis ----------------
def aba_gratis():
    st.subheader("🎁 Criar vídeo grátis")
    st.caption("Roteiro por IA, imagens, narração, música e animações — sem gastar nada.")

    c1, c2 = st.columns(2)
    with c1:
        produto = st.text_input("Produto / serviço / empresa *", key="g_prod",
                                placeholder="Ex.: Hamburgueria Brasa Viva")
        descricao = st.text_area("Detalhes do anúncio", key="g_desc", height=95,
                                 placeholder="Ex.: hambúrguer artesanal, entrega em 30 min, combo com batata")
        publico = st.text_input("Público-alvo", key="g_pub", placeholder="Ex.: jovens de 18 a 35 anos")
        cta = st.text_input("Chamada final (CTA)", key="g_cta", placeholder="Ex.: Peça já pelo WhatsApp!")
        contato = st.text_input("Contato no final do vídeo", key="g_contato",
                                placeholder="Ex.: (31) 99999-9999 · @brasaviva")
        tom = st.selectbox("Tom do anúncio", TONS, key="g_tom")
    with c2:
        formato = st.selectbox("Formato", list(FORMATOS_GRATIS), key="g_formato")
        tema = st.selectbox("Tema visual", list(TEMAS), key="g_tema")
        opcoes_fundo = ["Imagens geradas por IA (grátis)", "Só minhas fotos", "Fundos animados do tema"]
        if chave_pexels():
            opcoes_fundo.insert(0, FONTE_VIDEO)
        else:
            with st.expander("🎥 Quer vídeos reais no fundo? Conecte sua chave Pexels grátis"):
                nova_px = st.text_input("Chave Pexels", type="password", key="g_px_nova")
                st.markdown(f"👉 **[Pegar minha chave Pexels grátis]({LINK_PEXELS})**")
                if st.button("Conectar Pexels", key="g_px_btn"):
                    nova_px = limpar_chave(nova_px)
                    ok_px, msg_px = validar_pexels(nova_px) if nova_px else (False, "Cole a chave.")
                    if ok_px:
                        st.session_state.pexels_key = nova_px
                        st.rerun()
                    else:
                        st.error(msg_px)
        fonte_img = st.radio("Fundo das cenas", opcoes_fundo, key="g_fonte")
        if fonte_img == FONTE_VIDEO:
            st.caption("Vídeos reais e grátis do banco Pexels, escolhidos para cada cena. "
                       "Vídeos fornecidos por [Pexels](https://www.pexels.com).")
        estilo_img = st.selectbox("Estilo das imagens de IA", list(ESTILOS_IMG), key="g_estilo",
                                  disabled=fonte_img not in ("Imagens geradas por IA (grátis)", FONTE_VIDEO))
        usar_xai = False
        if st.session_state.xai_key and fonte_img in ("Imagens geradas por IA (grátis)", FONTE_VIDEO):
            usar_xai = st.checkbox("Se o gerador grátis falhar, usar a Grok (custa centavos na xAI)",
                                   value=True, key="g_usar_xai")
        fotos_up = st.file_uploader("Suas fotos (produto, loja, logo…) — usadas primeiro",
                                    type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True,
                                    key="g_fotos")
        cc1, cc2 = st.columns(2)
        n_cenas = cc1.slider("Cenas", 3, 6, 4, key="g_ncenas")
        dur_min = cc2.slider("Segundos por cena", 2.5, 6.0, 3.5, 0.5, key="g_dur")
        cc3, cc4 = st.columns(2)
        musica = cc3.selectbox("Música", MUSICAS, key="g_musica")
        narracao = cc4.toggle("Narração em português", value=True, key="g_narr")

    if st.button("📝 1. Gerar roteiro com IA", key="g_roteiro"):
        if not produto.strip():
            st.warning("Informe o produto ou serviço.")
        else:
            with st.spinner("A IA está escrevendo o roteiro…"):
                try:
                    cenas, cta_ia = gerar_roteiro(produto, descricao, publico, tom, n_cenas, cta, contato)
                    st.session_state.cenas = cenas
                    st.session_state.cta_gerado = cta_ia
                except Exception as e:
                    st.error(str(e))

    if st.session_state.cenas:
        st.markdown("**Roteiro** — edite à vontade antes de criar o vídeo:")
        editado = st.data_editor(
            st.session_state.cenas, key="g_editor", num_rows="dynamic",
            column_config={
                "texto_tela": st.column_config.TextColumn("Texto na tela", width="medium"),
                "narracao": st.column_config.TextColumn("Narração", width="large"),
                "imagem": st.column_config.TextColumn("Imagem (descrição para a IA)", width="medium"),
                "busca_video": st.column_config.TextColumn("Vídeo de fundo (busca em inglês)", width="small"),
            },
        )
        cenas_finais = [dict(c) for c in editado if any(str(v or "").strip() for v in dict(c).values())]
        cta_final = st.text_input("CTA final do vídeo", value=cta or st.session_state.cta_gerado,
                                  key="g_cta_final")
    else:
        cenas_finais, cta_final = [], cta

    if st.button("🎬 2. Criar vídeo grátis", type="primary", key="g_criar"):
        if not produto.strip():
            st.warning("Informe o produto ou serviço.")
            return
        if fonte_img == "Só minhas fotos" and not fotos_up:
            st.warning("Envie pelo menos uma foto ou escolha outra opção de imagens.")
            return
        barra = st.progress(1, text="Começando…")
        try:
            if not cenas_finais:
                barra.progress(2, text="Escrevendo o roteiro com IA…")
                cenas_finais, cta_ia = gerar_roteiro(produto, descricao, publico, tom, n_cenas, cta, contato)
                st.session_state.cenas = cenas_finais
                cta_final = cta or cta_ia
            fotos = [Image.open(f).convert("RGB") for f in (fotos_up or [])]
            opc = dict(produto=produto.strip(), cta=cta_final, contato=contato, formato=formato,
                       tema=tema, estilo_img=estilo_img, fonte_img=fonte_img, musica=musica,
                       narracao=narracao, dur_min=dur_min, usar_xai=usar_xai)
            dados = criar_video_gratis(cenas_finais, opc, fotos,
                                       lambda p, t: barra.progress(min(100, p), text=t))
            st.session_state.ultimo_gratis = {"bytes": dados, "titulo": produto.strip()}
            salvar_galeria(produto.strip(), "Grátis", dados=dados)
        except Exception as e:
            barra.empty()
            st.error(f"Não foi possível criar o vídeo: {e}")

    if st.session_state.ultimo_gratis:
        st.success("Seu vídeo está pronto!")
        st.video(st.session_state.ultimo_gratis["bytes"])
        st.download_button("⬇️ Baixar vídeo (MP4)", st.session_state.ultimo_gratis["bytes"],
                           file_name=f"appvideo_{int(time.time())}.mp4", mime="video/mp4")


# ---------------- aba profissional ----------------
AVATARES = {
    "Mulher executiva": "professional Brazilian businesswoman in her 30s, blazer, modern office background, friendly smile, looking at camera",
    "Homem executivo": "professional Brazilian businessman in his 40s, navy suit, office background, confident, looking at camera",
    "Jovem influencer": "young Brazilian influencer, colorful casual outfit, ring light, home studio, energetic, looking at camera",
    "Médica": "female doctor in white coat, clinic background, warm and trustworthy, looking at camera",
    "Chef de cozinha": "male chef with white uniform, restaurant kitchen background, smiling, looking at camera",
    "Personal trainer": "fit personal trainer in sportswear, gym background, motivating, looking at camera",
    "Vendedor simpático": "friendly salesman in polo shirt, store background, welcoming smile, looking at camera",
    "Mascote 3D": "cute 3D cartoon mascot presenter, Pixar style, bright studio background, looking at camera",
}
ESTILOS_PRO = {
    "Depoimento / apresentador": "testimonial style, person speaking to camera, friendly and trustworthy",
    "Cinematográfico": "cinematic commercial, dramatic lighting, smooth dolly moves, premium color grading",
    "Produto em destaque": "hero product shot, rotating turntable, studio lighting, macro details",
    "UGC / Influencer": "user-generated content, handheld smartphone footage, natural light, authentic",
    "Animação 3D": "high quality 3D animation, soft lighting, vibrant colors",
    "Lifestyle": "lifestyle commercial, real people enjoying the product, warm golden hour light",
    "Tech / Futurista": "futuristic tech ad, neon accents, holographic UI, sleek dark environment",
    "Comida": "food commercial, steam and sizzling, close-up slow motion, appetizing warm tones",
    "Imobiliário": "real estate showcase, smooth drone and gimbal shots, bright interiors",
    "Moda": "fashion campaign, editorial lighting, dynamic cuts",
}
PROPORCOES_PRO = {"Vertical 9:16": "9:16", "Horizontal 16:9": "16:9", "Quadrado 1:1": "1:1",
                  "Retrato 3:4": "3:4", "Paisagem 4:3": "4:3"}
AUDIO_PRO = {"Música calma": "soft calm background music", "Música animada": "upbeat background music",
             "Música épica": "epic orchestral music", "Sons ambientes": "natural ambient sound",
             "Sem música": "no music, subtle ambient sound"}


def conectar_xai():
    st.info("Para vídeos ultra profissionais, conecte sua chave da xAI (Grok Imagine). "
            "Ela é diferente da chave Groq: é paga por uso, direto na xAI.")
    with st.form("form_xai"):
        chave = st.text_input("Cole sua chave xAI", type="password", placeholder="xai-...")
        st.markdown(f"👉 **[Pegar minha chave xAI]({LINK_XAI})**")
        ok_btn = st.form_submit_button("Conectar chave xAI", type="primary")
    with st.expander("🔑 Passo a passo: pegar a chave xAI e colar aqui", expanded=True):
        st.markdown(
            f"1. Toque aqui: **[abrir console.x.ai]({LINK_XAI})** (abre em outra aba).\n"
            "2. Entre com sua conta **X**, **Google** ou **e-mail**. Não precisa de Premium.\n"
            "3. Se pedir, crie um **Team** (só escreva um nome, ex.: Appvideo).\n"
            "4. No menu, abra **Billing** e adicione créditos com cartão (ex.: US$ 5). "
            "Sem saldo, a chave não gera vídeo.\n"
            "5. No menu, abra **API Keys** e toque em **Create API Key**.\n"
            "6. Dê o nome **Appvideo**, deixe **todas as permissões liberadas** e confirme.\n"
            "7. Copie a chave que começa com **xai-** (ela só aparece uma vez).\n"
            "8. Volte para esta aba, **cole no campo acima** e toque em **Conectar chave xAI**."
        )
    if ok_btn:
        chave = limpar_chave(chave)
        with st.spinner("Verificando…"):
            ok, msg = validar_xai(chave)
        if ok:
            st.session_state.xai_key = chave
            st.rerun()
        else:
            st.error(msg)


def aba_pago():
    st.subheader("💎 Criar vídeos pagos")
    st.markdown(
        '<div class="nota"><b>Nota:</b> Este app cria vídeos gratuitos e serve de ponte para '
        "vídeos ultra profissionais. Você não precisa de assinaturas, basta criar seu vídeo e "
        "pagar poucos reais por ele.</div>", unsafe_allow_html=True)

    if not st.session_state.xai_key:
        conectar_xai()
        return

    cx1, cx2 = st.columns([4, 1])
    cx1.success("Chave xAI conectada ✅")
    if cx2.button("Trocar chave", key="p_trocar"):
        st.session_state.xai_key = ""
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**1. Apresentador**")
        modo = st.radio("Avatar", ["📷 Meu avatar (minha foto)", "🧑‍💼 Avatar pronto",
                                   "🚫 Sem apresentador"], key="p_modo", label_visibility="collapsed")
        foto, avatar = None, None
        if modo.startswith("📷"):
            foto = st.file_uploader("Sua foto (rosto de frente, boa luz)",
                                    type=["png", "jpg", "jpeg", "webp"], key="p_foto")
            if foto:
                st.image(foto, width=170)
        elif modo.startswith("🧑"):
            avatar = st.selectbox("Escolha o avatar", list(AVATARES), key="p_avatar")
            custom = st.text_input("…ou descreva seu avatar", key="p_avatar_custom",
                                   placeholder="Ex.: senhora simpática de óculos, padaria ao fundo")
            if custom:
                avatar = custom
        st.markdown("**2. Fala do apresentador**")
        fala = st.text_area("Texto da fala (português)", key="p_fala", height=100,
                            placeholder="Ex.: Olá! Aqui na Brasa Viva o hambúrguer é artesanal. Peça já!")
        if st.button("✍️ Escrever fala com IA", key="p_fala_ia"):
            with st.spinner("Escrevendo…"):
                try:
                    st.session_state.p_sugestao = chat_groq([
                        {"role": "system", "content": "Escreva uma fala curta (máx. 35 palavras) "
                         "em português do Brasil para um apresentador de comercial, com chamada "
                         "final. Responda só com a fala."},
                        {"role": "user", "content": f"Negócio: {st.session_state.get('p_prod') or 'meu negócio'}"}])
                except Exception as e:
                    st.error(str(e))
        if st.session_state.get("p_sugestao"):
            st.info(st.session_state.p_sugestao)
    with c2:
        st.markdown("**3. Configurações**")
        produto = st.text_input("Produto / empresa *", key="p_prod")
        estilo = st.selectbox("Estilo", list(ESTILOS_PRO), key="p_estilo")
        tom = st.selectbox("Tom", TONS, index=5, key="p_tom")
        cenario = st.text_input("Cenário", key="p_cen", placeholder="Ex.: loja moderna, ao ar livre")
        audio = st.selectbox("Áudio de fundo", list(AUDIO_PRO), key="p_audio")
        prop = st.selectbox("Formato", list(PROPORCOES_PRO), key="p_prop")
        resolucao = st.radio("Qualidade", ["720p", "480p"], horizontal=True, key="p_res")
        duracao = st.slider("Duração (segundos)", 5, 15, 10, key="p_dur")
        cta = st.text_input("Chamada final (CTA)", key="p_cta")

    confirmou = True
    if COBRANCA_ATIVA:
        st.markdown("---")
        st.markdown(f"**4. Pagamento — R$ {PRECO_VIDEO_PRO}**")
        if LINK_PAGAMENTO:
            st.link_button(f"💳 Pagar R$ {PRECO_VIDEO_PRO}", LINK_PAGAMENTO)
        if PIX_CHAVE:
            st.code(f"PIX: {PIX_CHAVE}", language=None)
        confirmou = st.checkbox("Já realizei o pagamento", key="p_pago")

    if st.button("🚀 Criar vídeo profissional", type="primary", key="p_criar"):
        if not produto.strip():
            st.warning("Informe o produto / empresa.")
            return
        if not confirmou:
            st.warning("Confirme o pagamento para gerar o vídeo profissional.")
            return
        if modo.startswith("📷") and not foto:
            st.warning("Envie sua foto para criar seu avatar.")
            return
        barra = st.progress(2, text="Preparando…")
        try:
            imagem = None
            if foto:
                imagem = arquivo_para_data_uri(foto)
            elif avatar:
                barra.progress(5, text="Criando o avatar…")
                imagem = gerar_imagem_xai(
                    f"Photorealistic portrait of a {AVATARES.get(avatar, avatar)}. "
                    f"Setting: {cenario or 'professional studio'}.", PROPORCOES_PRO[prop])
                st.image(imagem, caption="Avatar gerado", width=170)
            partes = [f"Professional advertising video for {produto}."]
            if imagem and fala:
                partes.append("The person in the image looks at the camera and speaks naturally in "
                              f"Brazilian Portuguese with accurate lip-sync, saying: \"{fala}\".")
            elif fala:
                partes.append(f"Brazilian Portuguese voice-over says: \"{fala}\".")
            partes += [f"Setting: {cenario}." if cenario else "", f"Style: {ESTILOS_PRO[estilo]}.",
                       f"Tone: {tom}.", f"Background audio: {AUDIO_PRO[audio]}.",
                       f"Final on-screen call to action: '{cta}'." if cta else "",
                       "Ultra professional, broadcast quality, natural facial expressions."]
            rid = iniciar_video_xai(" ".join(p for p in partes if p), duracao,
                                    PROPORCOES_PRO[prop], resolucao, imagem)
            url = aguardar_video_xai(rid, barra)
            st.session_state.ultimo_pro = {"url": url, "bytes": baixar_bytes(url)}
            salvar_galeria(produto.strip(), "Profissional", dados=st.session_state.ultimo_pro["bytes"], url=url)
        except Exception as e:
            barra.empty()
            st.error(str(e))

    if st.session_state.ultimo_pro:
        st.success("Seu vídeo profissional está pronto!")
        v = st.session_state.ultimo_pro
        st.video(v["bytes"] or v["url"])
        if v["bytes"]:
            st.download_button("⬇️ Baixar vídeo (MP4)", v["bytes"],
                               file_name=f"appvideo_pro_{int(time.time())}.mp4", mime="video/mp4")
        else:
            st.markdown(f"[⬇️ Abrir / baixar vídeo]({v['url']})")


# ---------------- outras abas ----------------
def aba_galeria():
    st.subheader("📁 Meus vídeos")
    if not st.session_state.galeria:
        st.info("Os vídeos que você criar nesta sessão aparecem aqui.")
        return
    st.caption("Os vídeos ficam aqui só enquanto a página estiver aberta — baixe os que quiser guardar.")
    cols = st.columns(3)
    for i, item in enumerate(st.session_state.galeria):
        with cols[i % 3]:
            st.markdown(f"**{item['titulo']}** · {item['tipo']} · {item['hora']}")
            st.video(item["bytes"] or item["url"])
            if item["bytes"]:
                st.download_button("⬇️ Baixar", item["bytes"], file_name=f"appvideo_{i}.mp4",
                                   mime="video/mp4", key=f"gal_{i}")
            elif item["url"]:
                st.markdown(f"[⬇️ Baixar]({item['url']})")


def aba_assistente():
    st.subheader("🤖 Assistente IA")
    c1, c2 = st.columns([3, 1])
    with c2:
        modelos = st.session_state.modelos_groq
        atual = st.session_state.modelo_chat if st.session_state.modelo_chat in modelos else modelos[0]
        st.session_state.modelo_chat = st.selectbox("Modelo", modelos, index=modelos.index(atual))
        if st.button("🗑️ Nova conversa"):
            st.session_state.chat = []
            st.rerun()
    with c1:
        st.caption("Converse à vontade — o assistente lembra de toda a conversa. Peça roteiros, "
                   "ideias de campanha, legendas, hashtags ou ajuda com o app.")
    sistema = {"role": "system", "content": (
        f"Você é o assistente do {NOME_APP}, app que cria vídeos de publicidade. O usuário se "
        f"chama {st.session_state.nome}. Responda em português do Brasil, de forma clara e "
        "prática. O app tem: (1) Criar vídeo grátis — usa a chave Groq grátis; a IA escreve o "
        "roteiro, cria imagens grátis, narração em português, música e animações; (2) Criar "
        "vídeos pagos — a pessoa conecta a chave xAI (console.x.ai, paga por uso, sem precisar "
        "de Premium) e usa a Grok Imagine com avatar da própria foto falando, até 15s em 720p. "
        "Para vídeos reais no fundo, a pessoa cola a chave grátis da Pexels (pexels.com/api) na entrada ou na aba grátis. Ajude com roteiros, textos de tela, CTAs, legendas, hashtags e estratégias de anúncio.")}
    for m in st.session_state.chat:
        with st.chat_message(m["role"], avatar="🧑" if m["role"] == "user" else "🤖"):
            st.markdown(m["content"])
    pergunta = st.chat_input("Digite sua mensagem…")
    if pergunta:
        st.session_state.chat.append({"role": "user", "content": pergunta})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(pergunta)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Pensando…"):
                try:
                    resposta = chat_groq([sistema] + st.session_state.chat[-30:])
                except Exception as e:
                    resposta = f"⚠️ {e}"
            st.markdown(resposta)
        st.session_state.chat.append({"role": "assistant", "content": resposta})


def aba_tutorial():
    st.subheader("📚 Tutorial completo")
    with st.expander("1. Como criar sua chave Groq grátis (para entrar)", expanded=True):
        st.markdown(
            f"1. Acesse **[console.groq.com/keys]({LINK_GROQ})**.\n"
            "2. Entre com sua conta Google ou e-mail. Não precisa de cartão.\n"
            "3. Clique em **Create API Key**, dê um nome (ex.: Appvideo) e confirme.\n"
            "4. Copie a chave na hora (começa com **gsk_**). Ela aparece só uma vez.\n"
            "5. Cole na tela de entrada do Appvideo junto com seu nome."
        )
    with st.expander("1b. Como criar sua chave Pexels grátis (vídeos reais de fundo)"):
        st.markdown(
            f"1. Acesse **[pexels.com/api]({LINK_PEXELS})** e crie uma conta grátis.\n"
            "2. Clique em **Your API Key** (ou *Get Started*).\n"
            "3. Preencha o nome do projeto (ex.: Appvideo) e o motivo (ex.: criar vídeos de anúncio).\n"
            "4. Copie a chave que aparece na tela.\n"
            "5. Cole no campo **Chave Pexels** da tela de entrada — ou depois, dentro da aba "
            "**Criar vídeo grátis**.\n\n"
            "Com ela, cada cena do seu anúncio ganha um vídeo real em movimento no fundo."
        )
    with st.expander("2. Criando um vídeo grátis"):
        st.markdown(
            "1. Abra **Criar vídeo grátis** e escreva o produto e os detalhes.\n"
            "2. Escolha o **formato** (9:16 para Reels/TikTok), o **tema visual** e o **fundo das "
            "cenas**: vídeos reais (com chave Pexels), imagens de IA, suas fotos ou fundos animados.\n"
            "3. Envie fotos do seu produto ou loja, se tiver — elas entram primeiro.\n"
            "4. Clique em **Gerar roteiro com IA** e ajuste os textos na tabela.\n"
            "5. Escolha a música e se quer narração em português.\n"
            "6. Clique em **Criar vídeo grátis**. Leva de 1 a 3 minutos.\n"
            "7. Assista e clique em **Baixar vídeo (MP4)**."
        )
    with st.expander("3. Vídeo profissional com seu avatar falando"):
        st.markdown(
            f"1. Crie uma conta em **[console.x.ai]({LINK_XAI})** — não precisa de Premium.\n"
            "2. Em **Billing**, adicione créditos (a xAI cobra por segundo de vídeo).\n"
            "3. Em **API Keys → Create API Key**, libere todas as permissões e copie o valor "
            "(começa com **xai-**).\n"
            "4. No Appvideo, abra **Criar vídeos pagos** e cole a chave.\n"
            "5. Envie sua foto (ou escolha um avatar), escreva a fala e ajuste o estilo.\n"
            "6. Clique em **Criar vídeo profissional** e aguarde de 1 a 4 minutos."
        )
    with st.expander("4. Dicas para vídeos que vendem"):
        st.markdown(
            "- Comece com um gancho forte na primeira cena.\n"
            "- Textos de tela curtos: até 7 palavras.\n"
            "- Use fotos reais do seu produto — passam mais confiança.\n"
            "- Termine sempre com CTA e contato (WhatsApp, @, site).\n"
            "- Vertical 9:16 funciona melhor em Reels, TikTok e Status.\n"
            "- Peça ideias ao **Assistente IA**."
        )
    with st.expander("5. Problemas comuns"):
        st.markdown(
            "- **Chave Groq inválida:** copie a chave inteira (gsk_…). Se perdeu, crie outra.\n"
            "- **Limite da Groq:** a chave grátis tem limite por minuto; espere um pouco.\n"
            "- **Imagens de IA não vieram:** o serviço grátis às vezes demora; o app usa fundos "
            "do tema no lugar. Tente de novo ou envie suas fotos.\n"
            "- **Chave xAI recusada:** confira se é chave de API (xai-…) e se há créditos.\n"
            "- **Vídeo profissional recusado:** a xAI bloqueia conteúdo impróprio, marcas de "
            "terceiros e pessoas famosas."
        )


def app():
    hero("Vídeos de publicidade grátis e ponte para vídeos ultra profissionais com a Grok Imagine.")
    c1, c2 = st.columns([5, 1], vertical_alignment="center")
    c1.markdown(f"👋 Olá, **{st.session_state.nome}**!")
    if c2.button("Sair", key="sair"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    abas = st.tabs(["🎁 Criar vídeo grátis", "💎 Criar vídeos pagos", "📁 Meus vídeos",
                    "🤖 Assistente IA", "📚 Tutorial"])
    with abas[0]:
        aba_gratis()
    with abas[1]:
        aba_pago()
    with abas[2]:
        aba_galeria()
    with abas[3]:
        aba_assistente()
    with abas[4]:
        aba_tutorial()


if os.environ.get("APPVIDEO_TESTE") != "1":
    if st.session_state.logado:
        app()
    else:
        tela_login()
