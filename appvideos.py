# -*- coding: utf-8 -*-
"""
VideoPub IA — Criador de vídeos de publicidade com Grok Imagine (xAI)
---------------------------------------------------------------------
Como rodar:
    pip install streamlit requests
    streamlit run app.py

Para publicar no Streamlit Community Cloud, crie também um arquivo
requirements.txt com duas linhas:  streamlit   e   requests

Opcional (st.secrets ou variáveis de ambiente) para a área de pagamento:
    PIX_CHAVE = "sua-chave-pix"
    LINK_PAGAMENTO = "https://seu-link-mercadopago-ou-stripe"
    PRECO_VIDEO_PRO = "9,90"
"""

import base64
import os
import time

import requests
import streamlit as st

# ----------------------------------------------------------------------------
# Configuração
# ----------------------------------------------------------------------------
API_BASE = "https://api.x.ai/v1"
LINK_CHAVE = "https://console.x.ai"
MODELO_VIDEO = "grok-imagine-video"
MODELO_IMAGEM = "grok-imagine-image"
MODELOS_CHAT = ["grok-4.3", "grok-4", "grok-4-fast", "grok-3-mini"]


def config(nome, padrao=""):
    try:
        if nome in st.secrets:
            return str(st.secrets[nome])
    except Exception:
        pass
    return os.environ.get(nome, padrao)


PIX_CHAVE = config("PIX_CHAVE", "")
LINK_PAGAMENTO = config("LINK_PAGAMENTO", "")
PRECO_VIDEO_PRO = config("PRECO_VIDEO_PRO", "9,90")

st.set_page_config(page_title="VideoPub IA", page_icon="🎬", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem; max-width: 1200px;}
    .hero {padding: 1.4rem 1.6rem; border-radius: 16px;
           background: linear-gradient(135deg,#111827 0%,#312e81 55%,#7c3aed 100%);
           color: #fff; margin-bottom: 1rem;}
    .hero h1 {margin: 0; font-size: 2rem;}
    .hero p {margin: .3rem 0 0; opacity: .85;}
    .nota {border-left: 4px solid #7c3aed; background: rgba(124,58,237,.08);
           padding: .8rem 1rem; border-radius: 8px; margin: .6rem 0 1rem;}
    .card {border: 1px solid rgba(128,128,128,.25); border-radius: 12px;
           padding: 1rem; margin-bottom: .8rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Estado
# ----------------------------------------------------------------------------
for chave, valor in {
    "logado": False,
    "nome": "",
    "api_key": "",
    "chat": [],
    "galeria": [],
    "modelo_chat": MODELOS_CHAT[0],
    "roteiro": "",
}.items():
    st.session_state.setdefault(chave, valor)


# ----------------------------------------------------------------------------
# Cliente xAI
# ----------------------------------------------------------------------------
def headers():
    return {
        "Authorization": f"Bearer {st.session_state.api_key}",
        "Content-Type": "application/json",
    }


def erro_api(resp):
    try:
        dados = resp.json()
        msg = dados.get("error") or dados.get("message") or dados
        if isinstance(msg, dict):
            msg = msg.get("message", msg)
    except Exception:
        msg = resp.text[:400]
    return f"Erro {resp.status_code}: {msg}"


def validar_chave(chave):
    """Confere se a chave funciona. Retorna (ok, mensagem)."""
    try:
        r = requests.get(f"{API_BASE}/api-key",
                         headers={"Authorization": f"Bearer {chave}"}, timeout=20)
        if r.status_code == 200:
            return True, "Chave válida."
        if r.status_code in (401, 403):
            return False, "Chave inválida ou sem permissão."
        # Se o endpoint mudar, testa com a lista de modelos
        r2 = requests.get(f"{API_BASE}/models",
                          headers={"Authorization": f"Bearer {chave}"}, timeout=20)
        if r2.status_code == 200:
            return True, "Chave válida."
        return False, erro_api(r2)
    except requests.RequestException as e:
        return False, f"Não foi possível conectar à xAI: {e}"


def chat_grok(mensagens, modelo=None, temperatura=0.7):
    r = requests.post(
        f"{API_BASE}/chat/completions",
        headers=headers(),
        json={"model": modelo or st.session_state.modelo_chat,
              "messages": mensagens, "temperature": temperatura},
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(erro_api(r))
    return r.json()["choices"][0]["message"]["content"]


def gerar_imagem(prompt, proporcao="9:16"):
    """Gera uma imagem (usada para avatares prontos). Retorna URL ou data URI."""
    corpo = {"model": MODELO_IMAGEM, "prompt": prompt, "n": 1,
             "aspect_ratio": proporcao}
    r = requests.post(f"{API_BASE}/images/generations", headers=headers(),
                      json=corpo, timeout=120)
    if r.status_code == 400:  # alguns modelos não aceitam aspect_ratio
        corpo.pop("aspect_ratio", None)
        r = requests.post(f"{API_BASE}/images/generations", headers=headers(),
                          json=corpo, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(erro_api(r))
    item = r.json()["data"][0]
    if item.get("url"):
        return item["url"]
    return "data:image/png;base64," + item["b64_json"]


def iniciar_video(prompt, duracao, proporcao, resolucao, imagem=None):
    """Envia o pedido de vídeo e devolve o request_id."""
    corpo = {"model": MODELO_VIDEO, "prompt": prompt, "duration": int(duracao),
             "aspect_ratio": proporcao, "resolution": resolucao}
    tentativas = [corpo]
    if imagem:
        tentativas = [dict(corpo, image={"url": imagem}),
                      dict(corpo, image_url=imagem)]
    ultimo_erro = ""
    for c in tentativas:
        r = requests.post(f"{API_BASE}/videos/generations", headers=headers(),
                          json=c, timeout=120)
        if r.status_code in (200, 201, 202):
            dados = r.json()
            rid = dados.get("request_id") or dados.get("id")
            if rid:
                return rid
            ultimo_erro = f"Resposta inesperada: {dados}"
        else:
            ultimo_erro = erro_api(r)
    raise RuntimeError(ultimo_erro)


def aguardar_video(request_id, barra, limite_seg=900):
    """Consulta o status até o vídeo ficar pronto. Retorna a URL do vídeo."""
    inicio = time.time()
    while time.time() - inicio < limite_seg:
        r = requests.get(f"{API_BASE}/videos/{request_id}", headers=headers(),
                         timeout=60)
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
            raise RuntimeError(f"A geração falhou (status: {status}). "
                               f"{dados.get('error', '')}")
        passado = int(time.time() - inicio)
        barra.progress(min(95, 5 + passado // 3),
                       text=f"Gerando seu vídeo na Grok Imagine… {passado}s")
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


# ----------------------------------------------------------------------------
# Opções de criação
# ----------------------------------------------------------------------------
ESTILOS = {
    "Cinematográfico": "cinematic commercial, dramatic lighting, smooth dolly camera moves, shallow depth of field, premium color grading",
    "Produto em destaque": "hero product shot, rotating turntable, studio lighting, clean reflections, macro details",
    "UGC / Influencer": "user-generated content style, handheld smartphone footage, natural light, authentic and casual",
    "Animação 3D": "high quality 3D animation, Pixar-like soft lighting, vibrant colors, playful motion",
    "Minimalista": "minimalist aesthetic, solid pastel background, elegant slow motion, lots of negative space",
    "Lifestyle": "lifestyle commercial, real people enjoying the product, warm golden hour light",
    "Tech / Futurista": "futuristic tech ad, neon accents, holographic UI elements, sleek dark environment",
    "Comida / Gastronomia": "food commercial, steam and sizzling, close-up slow motion, appetizing warm tones",
    "Imobiliário": "real estate showcase, smooth drone and gimbal shots, bright interiors, luxurious feel",
    "Moda": "fashion campaign, runway energy, editorial lighting, dynamic cuts",
    "Depoimento": "testimonial style, person speaking to camera, friendly and trustworthy",
    "Anime": "anime style animation, expressive, bold colors",
}
TONS = ["Inspirador", "Divertido", "Urgente (promoção)", "Luxuoso", "Emocional",
        "Profissional", "Jovem e descolado"]
AUDIOS = {
    "Música animada": "upbeat energetic background music",
    "Música calma": "soft calm background music",
    "Música épica": "epic orchestral music",
    "Sons ambientes": "natural ambient sound effects",
    "Narração em português": "a Brazilian Portuguese voice-over narrating the ad",
    "Sem música": "no music, only subtle ambient sound",
}
PROPORCOES = {"Vertical 9:16 (Reels/TikTok/Shorts)": "9:16",
              "Horizontal 16:9 (YouTube)": "16:9",
              "Quadrado 1:1 (Feed)": "1:1",
              "Retrato 3:4": "3:4",
              "Paisagem 4:3": "4:3"}
AVATARES = {
    "Mulher executiva": "professional Brazilian businesswoman in her 30s, blazer, modern office background, friendly smile, looking at camera, portrait",
    "Homem executivo": "professional Brazilian businessman in his 40s, navy suit, office background, confident, looking at camera, portrait",
    "Jovem influencer": "young Brazilian influencer, colorful casual outfit, ring light, bedroom studio, energetic, looking at camera",
    "Médica": "female doctor in white coat, clinic background, warm and trustworthy, looking at camera",
    "Chef de cozinha": "male chef with white uniform and hat, restaurant kitchen background, smiling, looking at camera",
    "Personal trainer": "fit personal trainer in sportswear, gym background, motivating expression, looking at camera",
    "Vendedor simpático": "friendly salesman in polo shirt, store background, welcoming smile, looking at camera",
    "Avatar 3D cartoon": "cute 3D cartoon mascot presenter character, Pixar style, bright studio background, looking at camera",
}


def montar_prompt(produto, descricao, publico, estilo, tom, audio, cta, extra):
    partes = [
        f"Advertising video for: {produto}.",
        f"Details: {descricao}." if descricao else "",
        f"Target audience: {publico}." if publico else "",
        f"Visual style: {ESTILOS[estilo]}.",
        f"Mood/tone: {tom}.",
        f"Audio: {AUDIOS[audio]}.",
        f"End with the call to action on screen: '{cta}'." if cta else "",
        extra,
        "High quality, professional advertising, coherent motion.",
    ]
    return " ".join(p for p in partes if p)


# ----------------------------------------------------------------------------
# Tela de entrada
# ----------------------------------------------------------------------------
def tela_login():
    st.markdown(
        '<div class="hero"><h1>🎬 VideoPub IA</h1>'
        "<p>Crie vídeos de publicidade com Inteligência Artificial usando a Grok Imagine.</p></div>",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([1.1, 1])
    with col1:
        st.subheader("Entrar")
        with st.form("login"):
            nome = st.text_input("Seu nome", placeholder="Ex.: Maria Silva")
            chave = st.text_input("Cole sua chave Grok (xAI)", type="password",
                                  placeholder="xai-...")
            entrar = st.form_submit_button("Entrar no app", type="primary",
                                           use_container_width=True)
        st.markdown(f"🔑 **Não tem chave?** [Clique aqui para obter sua chave Grok]({LINK_CHAVE}) "
                    "— entre na sua conta, vá em **API Keys** e clique em **Create API Key**.")
        if entrar:
            if not nome.strip() or not chave.strip():
                st.error("Preencha seu nome e sua chave.")
                return
            with st.spinner("Verificando sua chave…"):
                ok, msg = validar_chave(chave.strip())
            if ok:
                st.session_state.update(logado=True, nome=nome.strip(),
                                        api_key=chave.strip())
                st.rerun()
            else:
                st.error(msg)
    with col2:
        st.subheader("Como funciona")
        st.markdown(
            "1. Digite seu nome e cole sua chave Grok.\n"
            "2. Descreva seu produto ou serviço.\n"
            "3. Escolha estilo, formato, tom e áudio.\n"
            "4. Clique em **Criar vídeo** e baixe o resultado.\n\n"
            "Quer algo ultra profissional? Use **Criar vídeos pagos** com seu "
            "próprio avatar falando."
        )
        st.caption("Sua chave fica só nesta sessão do navegador e não é salva pelo app.")


# ----------------------------------------------------------------------------
# Abas
# ----------------------------------------------------------------------------
def salvar_na_galeria(url, titulo, tipo):
    st.session_state.galeria.insert(0, {"url": url, "titulo": titulo, "tipo": tipo,
                                        "hora": time.strftime("%d/%m %H:%M")})


def mostrar_video(url, nome_arquivo):
    st.video(url)
    dados = baixar_bytes(url)
    if dados:
        st.download_button("⬇️ Baixar vídeo (MP4)", dados, file_name=nome_arquivo,
                           mime="video/mp4", use_container_width=True)
    else:
        st.markdown(f"[⬇️ Abrir / baixar vídeo]({url})")


def aba_gratis():
    st.subheader("🎁 Criar vídeo grátis")
    st.caption("Vídeo de publicidade rápido em 480p, até 6 segundos.")

    c1, c2 = st.columns(2)
    with c1:
        produto = st.text_input("Produto / serviço / empresa *",
                                placeholder="Ex.: Hamburgueria Brasa Viva", key="g_prod")
        descricao = st.text_area("Descreva o que deve aparecer",
                                 placeholder="Ex.: hambúrguer artesanal suculento, queijo derretendo…",
                                 key="g_desc", height=100)
        publico = st.text_input("Público-alvo", placeholder="Ex.: jovens de 18 a 35 anos",
                                key="g_pub")
        cta = st.text_input("Chamada final (CTA)", placeholder="Ex.: Peça já pelo iFood!",
                            key="g_cta")
    with c2:
        estilo = st.selectbox("Estilo do vídeo", list(ESTILOS), key="g_est")
        tom = st.selectbox("Tom", TONS, key="g_tom")
        audio = st.selectbox("Áudio", list(AUDIOS), key="g_aud")
        prop = st.selectbox("Formato", list(PROPORCOES), key="g_prop")
        duracao = st.slider("Duração (segundos)", 3, 6, 6, key="g_dur")
        foto = st.file_uploader("Imagem do produto (opcional — anima sua foto)",
                                type=["png", "jpg", "jpeg", "webp"], key="g_foto")

    extra = st.text_input("Instruções extras (opcional)", key="g_extra")

    col_a, col_b = st.columns(2)
    if col_a.button("✨ Melhorar roteiro com IA", use_container_width=True, key="g_ia"):
        if not produto:
            st.warning("Informe o produto primeiro.")
        else:
            with st.spinner("A IA está escrevendo seu roteiro…"):
                try:
                    st.session_state.roteiro = chat_grok([
                        {"role": "system", "content":
                         "Você é diretor de comerciais. Escreva UM prompt em inglês, em um único "
                         "parágrafo de no máximo 90 palavras, para um gerador de vídeo de IA criar "
                         "um comercial curto. Descreva cena, câmera, luz, movimento e áudio. "
                         "Responda só com o prompt."},
                        {"role": "user", "content": montar_prompt(
                            produto, descricao, publico, estilo, tom, audio, cta, extra)},
                    ])
                except Exception as e:
                    st.error(str(e))

    prompt_final = st.text_area(
        "Prompt que será enviado à Grok Imagine (pode editar)",
        value=st.session_state.roteiro or montar_prompt(
            produto or "…", descricao, publico, estilo, tom, audio, cta, extra),
        height=130, key="g_prompt_final",
    )

    if col_b.button("🎬 Criar vídeo grátis", type="primary", use_container_width=True,
                    key="g_criar"):
        if not produto:
            st.warning("Informe o produto ou serviço.")
            return
        barra = st.progress(2, text="Enviando pedido…")
        try:
            imagem = arquivo_para_data_uri(foto) if foto else None
            rid = iniciar_video(prompt_final, duracao, PROPORCOES[prop], "480p", imagem)
            url = aguardar_video(rid, barra)
            st.session_state.roteiro = ""
            salvar_na_galeria(url, produto, "Grátis")
            st.success("Seu vídeo está pronto!")
            mostrar_video(url, f"videopub_{int(time.time())}.mp4")
        except Exception as e:
            barra.empty()
            st.error(str(e))


def aba_pago():
    st.subheader("💎 Criar vídeos pagos")
    st.markdown(
        '<div class="nota"><b>Nota:</b> Este app cria vídeos gratuitos e serve de ponte para '
        "vídeos ultra profissionais. Você não precisa de assinaturas, basta criar seu vídeo e "
        f"pagar poucos reais por ele (a partir de <b>R$ {PRECO_VIDEO_PRO}</b>).</div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**1. Escolha o apresentador**")
        modo_avatar = st.radio("Avatar", ["📷 Meu avatar (minha foto)",
                                          "🧑‍💼 Avatar pronto", "🚫 Sem apresentador"],
                               key="p_modo", label_visibility="collapsed")
        foto, avatar = None, None
        if modo_avatar.startswith("📷"):
            foto = st.file_uploader("Envie sua foto (rosto de frente, boa luz)",
                                    type=["png", "jpg", "jpeg", "webp"], key="p_foto")
            if foto:
                st.image(foto, width=180)
        elif modo_avatar.startswith("🧑"):
            avatar = st.selectbox("Escolha o avatar", list(AVATARES), key="p_avatar")
            avatar_custom = st.text_input("…ou descreva o seu avatar (opcional)",
                                          placeholder="Ex.: senhora simpática de óculos, padaria ao fundo",
                                          key="p_avatar_custom")
            if avatar_custom:
                avatar = avatar_custom

        st.markdown("**2. O que o apresentador vai falar**")
        fala = st.text_area("Texto da fala (em português)", key="p_fala", height=110,
                            placeholder="Ex.: Olá! Aqui na Brasa Viva o hambúrguer é artesanal "
                                        "e chega quentinho na sua casa. Peça já!")
        if st.button("✍️ Escrever fala com IA", key="p_fala_ia"):
            prod = st.session_state.get("p_prod", "") or "meu negócio"
            with st.spinner("Escrevendo…"):
                try:
                    st.session_state.p_fala_sugerida = chat_grok([
                        {"role": "system", "content":
                         "Escreva uma fala curta (máx. 35 palavras) em português do Brasil para um "
                         "apresentador de comercial, com chamada final. Responda só com a fala."},
                        {"role": "user", "content": f"Negócio: {prod}"}])
                except Exception as e:
                    st.error(str(e))
        if st.session_state.get("p_fala_sugerida"):
            st.info(st.session_state.p_fala_sugerida)
            st.caption("Copie a sugestão para o campo acima, se gostar.")

    with c2:
        st.markdown("**3. Configurações profissionais**")
        produto = st.text_input("Produto / empresa *", key="p_prod")
        estilo = st.selectbox("Estilo", list(ESTILOS), index=10, key="p_est")
        tom = st.selectbox("Tom", TONS, index=5, key="p_tom")
        cenario = st.text_input("Cenário", placeholder="Ex.: loja moderna, escritório, ao ar livre",
                                key="p_cen")
        audio = st.selectbox("Áudio de fundo", list(AUDIOS), index=1, key="p_aud")
        prop = st.selectbox("Formato", list(PROPORCOES), key="p_prop")
        resolucao = st.radio("Qualidade", ["720p (HD)", "480p"], horizontal=True, key="p_res")
        duracao = st.slider("Duração (segundos)", 5, 15, 10, key="p_dur")
        cta = st.text_input("Chamada final (CTA)", key="p_cta")

    st.markdown("---")
    st.markdown("**4. Pagamento**")
    pc1, pc2 = st.columns([1.3, 1])
    with pc1:
        if LINK_PAGAMENTO:
            st.link_button(f"💳 Pagar R$ {PRECO_VIDEO_PRO}", LINK_PAGAMENTO,
                           use_container_width=True)
        if PIX_CHAVE:
            st.code(f"PIX: {PIX_CHAVE}", language=None)
        if not LINK_PAGAMENTO and not PIX_CHAVE:
            st.info("O dono do app ainda não configurou o pagamento (PIX_CHAVE / LINK_PAGAMENTO).")
    with pc2:
        confirmou = st.checkbox("Já realizei o pagamento", key="p_pago")

    if st.button("🚀 Criar vídeo profissional", type="primary", use_container_width=True,
                 key="p_criar"):
        if not produto:
            st.warning("Informe o produto / empresa.")
            return
        if not confirmou:
            st.warning("Confirme o pagamento para gerar o vídeo profissional.")
            return
        if modo_avatar.startswith("📷") and not foto:
            st.warning("Envie sua foto para criar seu avatar.")
            return

        barra = st.progress(2, text="Preparando…")
        try:
            imagem = None
            if foto:
                imagem = arquivo_para_data_uri(foto)
            elif avatar:
                barra.progress(5, text="Criando o avatar…")
                desc = AVATARES.get(avatar, avatar)
                imagem = gerar_imagem(f"Photorealistic portrait of a {desc}. "
                                      f"Setting: {cenario or 'professional studio'}.",
                                      PROPORCOES[prop])
                st.image(imagem, caption="Avatar gerado", width=180)

            partes = [f"Professional advertising video for {produto}."]
            if imagem and fala:
                partes.append("The person in the image looks at the camera and speaks naturally "
                              "in Brazilian Portuguese with accurate lip-sync, saying: "
                              f"\"{fala}\".")
            elif fala:
                partes.append(f"Brazilian Portuguese voice-over says: \"{fala}\".")
            partes += [f"Setting: {cenario}." if cenario else "",
                       f"Style: {ESTILOS[estilo]}.", f"Tone: {tom}.",
                       f"Background audio: {AUDIOS[audio]}.",
                       f"Final on-screen call to action: '{cta}'." if cta else "",
                       "Ultra professional, broadcast quality, natural facial expressions."]
            prompt = " ".join(p for p in partes if p)

            rid = iniciar_video(prompt, duracao, PROPORCOES[prop],
                                resolucao.split(" ")[0], imagem)
            url = aguardar_video(rid, barra)
            salvar_na_galeria(url, produto, "Profissional")
            st.success("Seu vídeo profissional está pronto!")
            mostrar_video(url, f"videopub_pro_{int(time.time())}.mp4")
        except Exception as e:
            barra.empty()
            st.error(str(e))


def aba_galeria():
    st.subheader("📁 Meus vídeos")
    if not st.session_state.galeria:
        st.info("Os vídeos que você criar nesta sessão aparecem aqui.")
        return
    st.caption("Os links da Grok expiram depois de um tempo — baixe os vídeos que quiser guardar.")
    cols = st.columns(3)
    for i, item in enumerate(st.session_state.galeria):
        with cols[i % 3]:
            st.markdown(f"**{item['titulo']}** · {item['tipo']} · {item['hora']}")
            st.video(item["url"])
            st.markdown(f"[⬇️ Baixar]({item['url']})")


def aba_tutorial():
    st.subheader("📚 Tutorial completo")
    with st.expander("1. Como obter sua chave Grok (xAI)", expanded=True):
        st.markdown(
            f"1. Acesse **[console.x.ai]({LINK_CHAVE})** e entre com sua conta X, Google ou e-mail.\n"
            "2. Adicione créditos em **Billing** (a API da xAI é paga por uso).\n"
            "3. Vá em **API Keys → Create API Key**, dê um nome e marque as permissões de "
            "chat, imagem e vídeo.\n"
            "4. Copie a chave (começa com `xai-`) e cole na tela de entrada deste app.\n"
            "5. Guarde a chave em local seguro e não compartilhe com ninguém."
        )
    with st.expander("2. Criando um vídeo grátis"):
        st.markdown(
            "1. Abra a aba **Criar vídeo grátis**.\n"
            "2. Escreva o nome do produto e descreva o que deve aparecer.\n"
            "3. Escolha **estilo**, **tom**, **áudio** e **formato** (9:16 para Reels/TikTok, "
            "16:9 para YouTube, 1:1 para feed).\n"
            "4. (Opcional) Envie uma foto do produto para a IA animá-la.\n"
            "5. Clique em **Melhorar roteiro com IA** para um prompt mais caprichado.\n"
            "6. Clique em **Criar vídeo grátis** e aguarde de 1 a 3 minutos.\n"
            "7. Assista e clique em **Baixar vídeo**."
        )
    with st.expander("3. Criando um vídeo profissional com avatar falando"):
        st.markdown(
            "1. Abra **Criar vídeos pagos**.\n"
            "2. Escolha **Meu avatar** e envie uma foto sua de frente, bem iluminada — "
            "ou escolha um **avatar pronto** ou descreva o seu.\n"
            "3. Escreva a **fala** (ou peça para a IA escrever). Falas curtas, de até "
            "35 palavras, ficam mais naturais.\n"
            "4. Ajuste cenário, estilo, qualidade 720p e duração de até 15 s.\n"
            "5. Faça o pagamento, marque **Já realizei o pagamento** e clique em "
            "**Criar vídeo profissional**."
        )
    with st.expander("4. Dicas para vídeos que vendem"):
        st.markdown(
            "- Mostre o produto logo nos primeiros 2 segundos.\n"
            "- Seja específico: cores, ambiente, movimento de câmera, luz.\n"
            "- Uma ideia por vídeo. Para campanhas, crie vários vídeos curtos.\n"
            "- Use CTA claro: *Compre agora*, *Chame no WhatsApp*, *Link na bio*.\n"
            "- Formato vertical 9:16 funciona melhor em redes sociais.\n"
            "- Peça ajuda ao **Assistente IA** para ideias de roteiro."
        )
    with st.expander("5. Problemas comuns"):
        st.markdown(
            "- **Chave inválida:** confira se copiou a chave inteira e se ela tem permissões.\n"
            "- **Erro de saldo/créditos:** adicione créditos no console da xAI.\n"
            "- **Vídeo recusado:** a xAI bloqueia conteúdo impróprio, marcas de terceiros e "
            "pessoas famosas. Ajuste o texto.\n"
            "- **Demorou demais:** tente de novo com duração menor ou 480p.\n"
            "- **Link do vídeo parou de abrir:** os links expiram; baixe logo após gerar."
        )


def aba_assistente():
    st.subheader("🤖 Assistente IA")
    c1, c2 = st.columns([3, 1])
    with c2:
        st.session_state.modelo_chat = st.selectbox(
            "Modelo", MODELOS_CHAT, index=MODELOS_CHAT.index(st.session_state.modelo_chat))
        if st.button("🗑️ Nova conversa", use_container_width=True):
            st.session_state.chat = []
            st.rerun()
    with c1:
        st.caption("Converse à vontade — o assistente lembra de toda a conversa. Peça roteiros, "
                   "ideias de campanha, textos de legenda, prompts ou ajuda com o app.")

    sistema = {
        "role": "system",
        "content": (
            f"Você é o assistente do VideoPub IA, app que cria vídeos de publicidade com a "
            f"Grok Imagine. O usuário se chama {st.session_state.nome}. Responda em português "
            "do Brasil, de forma clara e prática. Ajude com: roteiros de comerciais, prompts de "
            "vídeo (em inglês, detalhando cena, câmera, luz, movimento e áudio), ideias de "
            "campanhas, legendas, hashtags e dúvidas de uso do app (aba grátis = 480p até 6s; "
            "aba paga = avatar com foto do usuário ou avatar pronto falando, 720p até 15s)."
        ),
    }

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
                    resposta = chat_grok([sistema] + st.session_state.chat[-30:])
                except Exception as e:
                    resposta = f"⚠️ {e}"
            st.markdown(resposta)
        st.session_state.chat.append({"role": "assistant", "content": resposta})


# ----------------------------------------------------------------------------
# App principal
# ----------------------------------------------------------------------------
def app():
    with st.sidebar:
        st.markdown(f"### 👋 Olá, {st.session_state.nome}!")
        st.caption("Conectado à Grok (xAI)")
        st.markdown(f"[🔑 Gerenciar minha chave]({LINK_CHAVE})")
        st.markdown(f"🎞️ Vídeos nesta sessão: **{len(st.session_state.galeria)}**")
        st.markdown("---")
        if st.button("Sair", use_container_width=True):
            for k in ("logado", "nome", "api_key", "chat", "galeria", "roteiro"):
                st.session_state.pop(k, None)
            st.rerun()

    st.markdown(
        '<div class="hero"><h1>🎬 VideoPub IA</h1>'
        "<p>Vídeos de publicidade grátis e ponte para vídeos ultra profissionais com a Grok Imagine.</p></div>",
        unsafe_allow_html=True,
    )

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


if st.session_state.logado:
    app()
else:
    tela_login()
