"""Estúdio de Vídeos — app para o Streamlit Community Cloud.

Cada pessoa usa a PRÓPRIA chave da Groq: ela é digitada no app, vale só para a sessão
daquela pessoa e não é gravada no servidor. O Python escreve o roteiro com a Groq e
entrega as cenas para o estúdio animado. Os projetos ficam salvos no navegador de cada um.
Arquivo único: não precisa de requirements.txt (só usa o Streamlit e a biblioteca padrão).
"""
import html
import json
import re
import time

import urllib.error
import urllib.request
import streamlit as st
import streamlit.components.v1 as components

HTML = r'''<title>Estúdio de Vídeos</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Figtree:wght@400;500;600;700&family=Chakra+Petch:wght@600;700&family=Gochi+Hand&family=Fraunces:ital,opsz,wght@0,9..144,600;1,9..144,600&family=Bebas+Neue&family=Baloo+2:wght@700;800&family=Manrope:wght@600;800&display=swap">
<style>
/* Layout: estúdio escuro de duas colunas — passos à esquerda, monitor de prévia fixo à direita; empilha no celular */
:root{
  --ink:#100e17;        /* fundo do estúdio */
  --panel:#1a1724;      /* superfícies */
  --panel-2:#231f30;
  --line:#332d45;
  --fg:#efeaf7;
  --muted:#a69fba;
  --rec:#ff5a36;        /* acento: luz de gravação */
  --rec-soft:#ff5a3622;
  --lilac:#b7a4ff;
  --ok:#5fd39a;
  --warn:#ffc155;
  --display:"Bricolage Grotesque", "Figtree", system-ui, sans-serif;
  --body:"Figtree", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  color-scheme: dark;
}
*{box-sizing:border-box}
html,body{background:var(--ink);color:var(--fg)}
body{font-family:var(--body);font-size:15px;line-height:1.5;min-height:100%}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--ink)}
button,input,select,textarea{font:inherit;color:inherit}
button{cursor:pointer}
:focus-visible{outline:2px solid var(--lilac);outline-offset:2px}
.wrap{padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));max-width:1320px;margin:0 auto}

/* topo */
header.top{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:color-mix(in srgb,var(--ink) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
header.top .wrap{display:flex;align-items:center;gap:12px;padding-block:12px}
.brand{display:flex;align-items:center;gap:10px;font-family:var(--display);font-weight:800;font-size:19px;letter-spacing:-.01em;margin-right:auto;min-width:0}
.brand .dot{width:12px;height:12px;border-radius:50%;background:var(--rec);box-shadow:0 0 0 4px var(--rec-soft);flex:none}
.brand small{font-family:var(--body);font-weight:500;font-size:12px;color:var(--muted);letter-spacing:.02em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border:1px solid var(--line);background:var(--panel);border-radius:10px;padding:9px 14px;font-weight:600;font-size:14px;transition:background .15s,border-color .15s;white-space:nowrap}
.btn:hover{background:var(--panel-2);border-color:#4a4262}
.btn.primary{background:var(--rec);border-color:var(--rec);color:#1a0b06}
.btn.primary:hover{background:#ff7352}
.btn.ghost{background:transparent}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn.sm{padding:6px 10px;font-size:13px;border-radius:8px}

/* grade principal */
main.wrap{display:grid;grid-template-columns:minmax(0,1fr) minmax(300px,420px);gap:28px;padding-block:24px 60px;align-items:start}
@media (max-width:900px){main.wrap{grid-template-columns:minmax(0,1fr)}.monitor{order:-1;position:static!important}}

/* trilha de passos */
.steps{display:flex;flex-wrap:wrap;gap:6px;padding-bottom:6px;margin-bottom:18px}
.step-chip{flex:none;display:flex;align-items:center;gap:8px;border:1px solid var(--line);background:transparent;border-radius:999px;padding:6px 12px 6px 6px;font-size:13px;font-weight:600;color:var(--muted)}
.step-chip .n{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;background:var(--panel-2);font-size:12px;font-variant-numeric:tabular-nums}
.step-chip.done .n{background:#2a3d33;color:var(--ok)}
.step-chip.on{color:var(--fg);border-color:var(--rec);background:var(--rec-soft)}
.step-chip.on .n{background:var(--rec);color:#1a0b06}

.eyebrow{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--rec)}
h1.step-title{font-family:var(--display);font-weight:800;font-size:clamp(26px,4vw,36px);line-height:1.08;letter-spacing:-.02em;margin:6px 0 6px;text-wrap:balance}
.lead{color:var(--muted);max-width:62ch;margin:0 0 20px}

/* cartões de opção */
.grid{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.opt{position:relative;text-align:left;border:1px solid var(--line);background:var(--panel);border-radius:14px;padding:14px;display:flex;flex-direction:column;gap:6px;min-height:96px;transition:border-color .15s,transform .15s}
.opt:hover{border-color:#4f4669;transform:translateY(-1px)}
.opt .ico{font-size:24px;line-height:1}
.opt b{font-weight:700;font-size:14px}
.opt span{font-size:12.5px;color:var(--muted);line-height:1.35}
.opt.on{border-color:var(--rec);background:linear-gradient(180deg,var(--rec-soft),transparent 70%),var(--panel)}
.opt.on::after{content:"✓";position:absolute;top:10px;right:10px;width:20px;height:20px;border-radius:50%;background:var(--rec);color:#1a0b06;font-size:12px;font-weight:800;display:grid;place-items:center}
.swatch{height:46px;border-radius:9px;margin-bottom:4px;display:grid;place-items:center;font-weight:800;font-size:18px;overflow:hidden}

.section{margin-top:26px}
.section h3{font-family:var(--display);font-size:17px;font-weight:700;margin:0 0 10px}
.seg{display:inline-flex;flex-wrap:wrap;gap:6px}
.seg button{border:1px solid var(--line);background:var(--panel);border-radius:999px;padding:7px 14px;font-weight:600;font-size:13.5px;font-variant-numeric:tabular-nums}
.seg button.on{background:var(--fg);color:var(--ink);border-color:var(--fg)}
.hint{display:flex;gap:10px;align-items:flex-start;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px;font-size:13.5px;color:var(--muted);margin-top:18px;max-width:70ch}
.hint b{color:var(--fg)}
.hint.warn{border-color:#5a4720;background:#2a2213}
label.f{display:flex;flex-direction:column;gap:6px;font-size:13px;font-weight:600;color:var(--muted)}
input[type=text],input[type=password],textarea,select{background:var(--ink);border:1px solid var(--line);border-radius:10px;padding:10px 12px;width:100%;color:var(--fg);font-size:14.5px}
textarea{resize:vertical;min-height:70px;line-height:1.45}
input[type=range]{width:100%;accent-color:var(--rec)}

/* roteiro */
.ai-box{display:flex;gap:8px;flex-wrap:wrap;align-items:stretch}
.ai-box input{flex:1 1 260px;min-width:0}
.scenes{display:flex;flex-direction:column;gap:10px;margin-top:14px}
.scene{display:grid;grid-template-columns:56px minmax(0,1fr) auto;gap:12px;align-items:start;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px}
.scene .em{width:56px;height:56px;border-radius:12px;background:var(--panel-2);font-size:28px;text-align:center;border:1px solid var(--line);padding:0}
.scene .fields{display:flex;flex-direction:column;gap:8px;min-width:0}
.scene .fields input{font-weight:700}
.scene .meta{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.scene .tools{display:flex;flex-direction:column;gap:6px}
.iconbtn{width:32px;height:32px;border-radius:8px;border:1px solid var(--line);background:transparent;display:grid;place-items:center;font-size:14px;color:var(--muted)}
.iconbtn:hover{color:var(--fg);background:var(--panel-2)}
details.vis summary{font-size:12px;color:var(--muted);cursor:pointer}
@media (max-width:520px){.scene{grid-template-columns:44px minmax(0,1fr)}.scene .em{width:44px;height:44px;font-size:22px}.scene .tools{grid-column:1/-1;flex-direction:row}}

.stepnav{display:flex;justify-content:space-between;gap:10px;margin-top:30px;padding-top:18px;border-top:1px solid var(--line)}

/* monitor de prévia */
.monitor{position:sticky;top:calc(env(safe-area-inset-top,0px) + 76px);background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:14px;display:flex;flex-direction:column;gap:12px}
.mon-head{display:flex;align-items:center;justify-content:space-between;font-size:12px;color:var(--muted);font-weight:600;letter-spacing:.06em;text-transform:uppercase}
.mon-head .live{display:flex;align-items:center;gap:6px}
.mon-head .live i{width:8px;height:8px;border-radius:50%;background:var(--muted)}
.mon-head .live.rec i{background:var(--rec);animation:blink 1s infinite}
@keyframes blink{50%{opacity:.25}}
.screen{background:#000;border-radius:12px;display:grid;place-items:center;overflow:hidden;max-height:62vh}
.screen canvas{display:block;max-width:100%;max-height:62vh;width:auto;height:auto}
@media (max-width:900px){.screen,.screen canvas{max-height:52vh}}
.transport{display:flex;align-items:center;gap:10px}
.play{width:42px;height:42px;border-radius:50%;border:none;background:var(--fg);color:var(--ink);font-size:16px;flex:none;display:grid;place-items:center}
.time{font-family:var(--mono);font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums;flex:none}
.timeline{display:flex;gap:3px;height:8px}
.timeline div{border-radius:3px;background:var(--panel-2);position:relative;overflow:hidden}
.timeline div i{position:absolute;inset:0 auto 0 0;background:var(--rec)}
.mon-note{font-size:12.5px;color:var(--muted);line-height:1.4}

/* gerar */
.gen-card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;display:flex;flex-direction:column;gap:12px}
.gen-card h3{margin:0;font-family:var(--display);font-size:18px}
.bar{height:10px;border-radius:99px;background:var(--panel-2);overflow:hidden}
.bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--rec),var(--lilac));transition:width .2s}
.checklist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px;font-size:13.5px}
.checklist li{display:flex;gap:8px;align-items:center;color:var(--muted)}
.checklist li.ok{color:var(--fg)}
.checklist li .s{width:18px;text-align:center}
.clip-row{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;font-size:13px;padding:8px 0;border-top:1px solid var(--line)}
.pill{font-size:11.5px;font-weight:700;padding:3px 8px;border-radius:99px;background:var(--panel-2);color:var(--muted);white-space:nowrap}
.pill.ok{background:#1f3a2c;color:var(--ok)}
.pill.err{background:#3d1f1c;color:#ff8a7a}
.pill.run{background:#3a2c14;color:var(--warn)}
.result-video{width:100%;border-radius:12px;background:#000;max-height:60vh}

/* gaveta e modal */
.scrim{position:fixed;inset:0;background:#05040acc;z-index:20;display:flex;justify-content:flex-end}
.sheet{width:min(440px,100%);height:100%;background:var(--panel);border-left:1px solid var(--line);padding:calc(env(safe-area-inset-top,0px) + 18px) max(18px,env(safe-area-inset-right,0px)) 18px 18px;overflow:auto;display:flex;flex-direction:column;gap:14px}
.sheet h2{font-family:var(--display);margin:0;font-size:22px}
.proj{display:flex;gap:10px;align-items:center;padding:10px;border:1px solid var(--line);border-radius:12px;background:var(--ink)}
.proj .pm{flex:1;min-width:0}
.proj .pm b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.proj .pm span{font-size:12px;color:var(--muted)}
.proj.cur{border-color:var(--rec)}
.toast{position:fixed;left:50%;bottom:calc(20px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);background:var(--fg);color:var(--ink);padding:10px 16px;border-radius:10px;font-weight:600;font-size:14px;z-index:30;max-width:calc(100% - 32px);box-shadow:0 10px 30px #0008}
.photo-drop{display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.photo-drop .ph{width:96px;height:96px;border-radius:50%;background:var(--panel-2) center/cover;border:2px dashed var(--line);display:grid;place-items:center;color:var(--muted);font-size:12px;flex:none}
.kbd{font-family:var(--mono);font-size:12px;background:var(--panel-2);padding:2px 6px;border-radius:5px}
.env-badge{font-size:11px;font-weight:700;padding:3px 8px;border-radius:99px;border:1px solid var(--line);color:var(--muted);white-space:nowrap}
@media (max-width:560px){.brand small{display:none}.hide-sm{display:none}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>

<header class="top">
  <div class="wrap">
    <div class="brand"><span class="dot"></span><span>Estúdio de Vídeos</span><small id="projName"></small></div>
    <span class="env-badge hide-sm" id="envBadge">carregando…</span>
    <button class="btn sm" id="btnProjects">Meus vídeos</button>
    <button class="btn sm ghost" id="btnSettings" aria-label="Configurações">⚙︎ <span class="hide-sm">Chaves de IA</span></button>
  </div>
</header>

<main class="wrap">
  <section id="stepArea" style="min-width:0">
    <nav class="steps" id="steps" aria-label="Passos"></nav>
    <div id="stepBody"></div>
    <div class="stepnav">
      <button class="btn" id="btnPrev">← Voltar</button>
      <button class="btn primary" id="btnNext">Próximo →</button>
    </div>
  </section>

  <aside class="monitor" aria-label="Prévia do vídeo">
    <div class="mon-head"><span class="live" id="liveLbl"><i></i><span id="liveTxt">Prévia</span></span><span id="fmtLbl">9:16 · 30 s</span></div>
    <div class="screen"><canvas id="cv" width="720" height="1280"></canvas></div>
    <div class="timeline" id="timeline"></div>
    <div class="transport">
      <button class="play" id="btnPlay" aria-label="Tocar">▶</button>
      <input type="range" id="scrub" min="0" max="1000" value="0" aria-label="Posição">
      <span class="time" id="timeLbl">0:00 / 0:30</span>
    </div>
    <button class="btn primary" id="btnFinish" style="width:100%;padding:12px 14px;font-size:15px">🎬 Finalizar vídeo</button>
    <div class="mon-note" id="monNote"></div>
  </aside>
</main>

<div id="layer"></div>

<script>
(() => {
"use strict";
/* ============ utilidades ============ */
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const easeOut = t => 1 - Math.pow(1 - clamp(t, 0, 1), 3);
const easeBack = t => { t = clamp(t, 0, 1); const c = 1.70158, c3 = c + 1; return 1 + c3 * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
const fmtT = s => { s = Math.max(0, Math.round(s)); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); };
const uid = () => Math.random().toString(36).slice(2, 10);
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } },
  del(k) { try { localStorage.removeItem(k); } catch (e) {} }
};
let toastTimer;
function toast(msg, ms = 3200) {
  let t = $(".toast"); if (!t) { t = document.createElement("div"); t.className = "toast"; t.setAttribute("role", "status"); document.body.appendChild(t); }
  t.textContent = msg; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => t.hidden = true, ms);
}

/* ============ catálogos ============ */
const PURPOSES = [
  { id: "anuncio", ico: "📣", name: "Anúncio / Vendas", desc: "Apresente um produto e chame para comprar", style: "vibrante", music: "animada" },
  { id: "aula", ico: "🎓", name: "Aula / Tutorial", desc: "Explique um passo a passo com clareza", style: "giz", music: "calma" },
  { id: "reels", ico: "📱", name: "Reels e Stories", desc: "Rápido, chamativo, feito para prender", style: "neon", music: "animada" },
  { id: "receita", ico: "🧁", name: "Receita", desc: "Ingredientes e modo de preparo", style: "infantil", music: "animada" },
  { id: "convite", ico: "🎉", name: "Parabéns / Convite", desc: "Aniversário, casamento, evento", style: "aquarela", music: "calma" },
  { id: "empresa", ico: "🏢", name: "Empresa", desc: "Institucional, serviços, comunicado", style: "empresa", music: "epica" },
  { id: "historia", ico: "📖", name: "História animada", desc: "Conto infantil, fábula, narrativa", style: "infantil", music: "calma" },
  { id: "imovel", ico: "🏡", name: "Imóvel / Obra", desc: "Mostre um imóvel, reforma ou projeto", style: "cinema", music: "epica" }
];
const FORMATS = [
  { id: "9:16", name: "Vertical 9:16", desc: "Reels, Stories, TikTok, Shorts", ico: "📱", w: 720, h: 1280 },
  { id: "16:9", name: "Horizontal 16:9", desc: "YouTube e sites", ico: "🖥️", w: 1280, h: 720 },
  { id: "1:1", name: "Quadrado 1:1", desc: "Feed do Instagram e Facebook", ico: "⬛", w: 960, h: 960 }
];
const DURATIONS = [15, 30, 60, 90];
const STYLES = {
  vibrante: { name: "Vibrante", desc: "Cores fortes e formas que flutuam", font: '800 {s}px "Bricolage Grotesque"', sub: '600 {s}px "Figtree"', fg: "#ffffff", cap: "#14101f", capBg: "#ffffff", pal: [["#ff5a36", "#ffb547"], ["#6a4cff", "#ff5fa2"], ["#00a889", "#c6f25b"], ["#2054ff", "#4fd4ff"]], sw: "linear-gradient(135deg,#ff5a36,#ffb547)" },
  neon: { name: "Neon", desc: "Fundo escuro, brilho e grade em movimento", font: '700 {s}px "Chakra Petch"', sub: '600 {s}px "Figtree"', fg: "#eafcff", cap: "#eafcff", capBg: "rgba(10,6,24,.78)", pal: [["#ff2bd6", "#22e4ff"], ["#7a5cff", "#22ffb5"], ["#ffcf3f", "#ff2b6a"]], sw: "linear-gradient(135deg,#0b0820,#3a0b52)" },
  giz: { name: "Lousa e giz", desc: "Visual de aula, escrito à mão", font: '400 {s}px "Gochi Hand"', sub: '400 {s}px "Gochi Hand"', fg: "#f4f1e6", cap: "#f4f1e6", capBg: "rgba(0,0,0,.28)", pal: [["#21392f", "#2c4a3d"]], sw: "#24402f" },
  aquarela: { name: "Aquarela", desc: "Papel claro e manchas suaves de tinta", font: 'italic 600 {s}px "Fraunces"', sub: '500 {s}px "Figtree"', fg: "#2b2230", cap: "#2b2230", capBg: "rgba(255,252,246,.86)", pal: [["#f7b6c2", "#9fd3e6"], ["#ffd59a", "#b7e4a7"], ["#c9b6f2", "#f9c7a3"]], sw: "radial-gradient(circle at 30% 40%,#f7b6c2,transparent 60%),radial-gradient(circle at 70% 60%,#9fd3e6,transparent 60%),#f8f2e8" },
  cinema: { name: "Cinema", desc: "Faixas pretas, granulado e letreiro", font: '400 {s}px "Bebas Neue"', sub: '500 {s}px "Figtree"', fg: "#fff4e0", cap: "#fff4e0", capBg: "rgba(0,0,0,.55)", pal: [["#3b1d10", "#c46a2c"], ["#0f2433", "#3c7a8c"], ["#2a1630", "#a2496a"]], sw: "linear-gradient(180deg,#000 18%,#7a3e1c 18% 82%,#000 82%)" },
  infantil: { name: "Infantil", desc: "Céu, nuvens e letras redondas", font: '800 {s}px "Baloo 2"', sub: '700 {s}px "Baloo 2"', fg: "#ffffff", cap: "#20305a", capBg: "#ffffff", pal: [["#5ec8ff", "#bdeeff"], ["#ffb36b", "#ffe2a8"], ["#8f7bff", "#d6ccff"]], sw: "linear-gradient(180deg,#5ec8ff,#bdeeff)" },
  empresa: { name: "Empresa", desc: "Limpo, sério e geométrico", font: '800 {s}px "Manrope"', sub: '600 {s}px "Manrope"', fg: "#0e1b3d", cap: "#ffffff", capBg: "#0e1b3d", pal: [["#f3f5fa", "#dfe6f5"]], sw: "linear-gradient(135deg,#f3f5fa 60%,#2453d6 60%)" }
};
const MUSIC = {
  animada: { name: "Animada", ico: "🥁", desc: "Batida pop alegre", bpm: 112 },
  calma: { name: "Calma", ico: "🌙", desc: "Piano suave e acolhedor", bpm: 76 },
  epica: { name: "Épica", ico: "🎻", desc: "Cordas e tambores de cinema", bpm: 88 },
  none: { name: "Sem música", ico: "🔇", desc: "Só a voz", bpm: 0 }
};
const CHARACTERS = ["👩‍🍳", "🧑‍🏫", "🧑‍💼", "👩‍💻", "👷", "🐶", "🐱", "🦊", "🐼", "🐲", "🦄", "🤖", "👽", "🧙", "🦸", "🐸"];
const LANGS = [{ id: "pt-BR", name: "Português" }, { id: "en-US", name: "Inglês" }, { id: "es-ES", name: "Espanhol" }];
const STEPS = ["Finalidade", "Formato", "Estilo", "Apresentador", "Voz", "Roteiro", "Música", "Gerar"];

/* ============ ambiente ============ */
const ENV = { viewer: !!window.claude, sample: null, downloads: null };
const settings = Object.assign({ groqKey: "", groqModel: "openai/gpt-oss-120b", xaiKey: "", xaiModel: "grok-imagine-video", xaiRes: "480p" }, store.get("evs.settings", {}));
function saveSettings() { store.set("evs.settings", settings); }
function engineName() {
  if (ENV.sample) return "Claude";
  if (settings.groqKey) return "Groq";
  return null;
}
function updateEnvBadge() {
  const e = engineName() || (ENV.hostAI ? ENV.hostAI + " (no topo da página)" : null);
  $("#envBadge").textContent = e ? "IA do roteiro: " + e : "Roteiro: modelos prontos";
}

/* ============ projeto ============ */
function sampleProject() {
  return {
    id: uid(), name: "Bolo vegano de chocolate", updated: Date.now(),
    purpose: "receita", format: "9:16", duration: 30, style: "vibrante",
    presenter: { type: "emoji", emoji: "👩‍🍳", photo: "" },
    voice: { mode: "browser", lang: "pt-BR", voiceName: "", rate: 1 },
    music: "animada", captions: true, brand: "@suareceita", topic: "Bolo vegano de chocolate, fácil e fofinho",
    scenes: [
      { id: uid(), emoji: "🍫", title: "Bolo vegano de chocolate", text: "Oi! Hoje vou te ensinar um bolo vegano delicioso, fácil e fofinho.", visual: "Cozy kitchen, a fluffy chocolate cake on a wooden table, warm light, cartoon 3D style" },
      { id: uid(), emoji: "🥣", title: "Separe os ingredientes", text: "Separe farinha, cacau, açúcar, óleo, leite vegetal e fermento.", visual: "Flour, cocoa, sugar and plant milk on a counter, playful 3D animation" },
      { id: uid(), emoji: "🔥", title: "Misture e asse", text: "Misture tudo e asse por trinta e cinco minutos a cento e oitenta graus.", visual: "Cake batter being poured into a pan and going into an oven, 3D cartoon" },
      { id: uid(), emoji: "🎂", title: "Pronto! Gostou?", text: "Pronto! Gostou? Me segue para mais receitas como essa.", visual: "Slice of chocolate cake with steam, happy chef waving, 3D cartoon" }
    ]
  };
}
let projects = store.get("evs.projects", null);
if (!Array.isArray(projects) || !projects.length) projects = [sampleProject()];
let curId = store.get("evs.current", projects[0].id);
let P = projects.find(p => p.id === curId) || projects[0];
let step = clamp(store.get("evs.step", 0), 0, STEPS.length - 1);
const runtime = { narrationUrl: "", narrationName: "", narrationDur: 0, clipVideos: {}, exportUrl: "", exportExt: "", exportBlob: null };

let saveTimer;
function save() {
  P.updated = Date.now();
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    if (!store.set("evs.projects", projects)) {
      // provavelmente a foto é grande demais: tenta sem fotos de outros projetos
      toast("Não consegui salvar no navegador. O projeto continua aberto aqui.");
    }
    store.set("evs.current", P.id);
  }, 250);
  timelineDirty = true;
}

/* ============ linha do tempo ============ */
let TL = { total: 30, scenes: [] };
let timelineDirty = true;
function words(s) { return String(s || "").trim().split(/\s+/).filter(Boolean).length; }
function buildTimeline() {
  let total = P.duration;
  if ((P.voice.mode === "upload" || P.voice.mode === "record") && runtime.narrationDur > 1) total = Math.ceil(runtime.narrationDur + 0.6);
  const sc = P.scenes.length ? P.scenes : [{ id: "x", emoji: "🎬", title: "Escreva seu roteiro", text: "", visual: "" }];
  const w = sc.map(s => Math.max(4, words(s.text) + words(s.title) * 0.4));
  const sum = w.reduce((a, b) => a + b, 0);
  let acc = 0;
  TL = { total, scenes: sc.map((s, i) => { const d = total * w[i] / sum; const o = { s, i, start: acc, dur: d }; acc += d; return o; }) };
  timelineDirty = false;
  drawTimelineBar();
}
function sceneAt(t) {
  const arr = TL.scenes;
  for (let i = 0; i < arr.length; i++) if (t < arr[i].start + arr[i].dur) return arr[i];
  return arr[arr.length - 1];
}
function drawTimelineBar() {
  const el = $("#timeline");
  el.innerHTML = TL.scenes.map(x => `<div style="flex:${x.dur.toFixed(3)}" title="${esc(x.s.title)}"><i></i></div>`).join("");
}

/* ============ áudio: música sintetizada ============ */
let AC = null, master = null, recDest = null, musicBus = null, voiceBus = null, analyser = null;
function audio() {
  if (AC) return AC;
  const C = window.AudioContext || window.webkitAudioContext;
  if (!C) return null;
  AC = new C();
  master = AC.createGain(); master.gain.value = 1; master.connect(AC.destination);
  recDest = AC.createMediaStreamDestination(); master.connect(recDest);
  musicBus = AC.createGain(); musicBus.gain.value = 0.32; musicBus.connect(master);
  voiceBus = AC.createGain(); voiceBus.gain.value = 1; voiceBus.connect(master);
  analyser = AC.createAnalyser(); analyser.fftSize = 512; voiceBus.connect(analyser);
  return AC;
}
const NOTE = n => 220 * Math.pow(2, n / 12); // n=0 → A3
// progressão C – G – Am – F (semitons a partir de A3)
const PROG = [[3, 7, 10], [-2, 2, 5], [0, 3, 7], [-4, 0, 3]];
let noiseBuf = null;
function noise() {
  if (noiseBuf) return noiseBuf;
  noiseBuf = AC.createBuffer(1, AC.sampleRate * 0.5, AC.sampleRate);
  const d = noiseBuf.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  return noiseBuf;
}
function tone(freq, when, dur, type, vol, att = 0.01, rel = 0.2, cutoff = 0) {
  const o = AC.createOscillator(), g = AC.createGain();
  o.type = type; o.frequency.value = freq;
  let node = o;
  if (cutoff) { const f = AC.createBiquadFilter(); f.type = "lowpass"; f.frequency.value = cutoff; o.connect(f); node = f; }
  node.connect(g); g.connect(musicBus);
  g.gain.setValueAtTime(0.0001, when);
  g.gain.exponentialRampToValueAtTime(vol, when + att);
  g.gain.setValueAtTime(vol, when + Math.max(att, dur - rel));
  g.gain.exponentialRampToValueAtTime(0.0001, when + dur);
  o.start(when); o.stop(when + dur + 0.05);
}
function kick(when, vol = 0.9) {
  const o = AC.createOscillator(), g = AC.createGain();
  o.frequency.setValueAtTime(140, when); o.frequency.exponentialRampToValueAtTime(42, when + 0.18);
  g.gain.setValueAtTime(vol, when); g.gain.exponentialRampToValueAtTime(0.0001, when + 0.3);
  o.connect(g); g.connect(musicBus); o.start(when); o.stop(when + 0.32);
}
function hat(when, vol = 0.12) {
  const s = AC.createBufferSource(); s.buffer = noise();
  const f = AC.createBiquadFilter(); f.type = "highpass"; f.frequency.value = 7000;
  const g = AC.createGain(); g.gain.setValueAtTime(vol, when); g.gain.exponentialRampToValueAtTime(0.0001, when + 0.05);
  s.connect(f); f.connect(g); g.connect(musicBus); s.start(when); s.stop(when + 0.06);
}
const Music = {
  timer: null, step: 0, t0: 0, spb: 0.25, mood: "none",
  start(offset) {
    this.stop();
    if (!AC || P.music === "none") return;
    this.mood = P.music;
    this.spb = 60 / MUSIC[this.mood].bpm / 2;
    this.t0 = AC.currentTime - offset;
    this.step = Math.ceil(offset / this.spb);
    musicBus.gain.cancelScheduledValues(AC.currentTime);
    musicBus.gain.setValueAtTime(0.32, AC.currentTime);
    this.timer = setInterval(() => this.tick(), 40); this.tick();
  },
  tick() {
    while (this.t0 + this.step * this.spb < AC.currentTime + 0.18) {
      const when = Math.max(AC.currentTime, this.t0 + this.step * this.spb);
      this.play(this.step, when); this.step++;
    }
  },
  play(s, when) {
    const ch = PROG[Math.floor(s / 8) % 4], b = s % 8, spb = this.spb;
    if (this.mood === "animada") {
      if (b % 4 === 0) kick(when);
      if (b % 2 === 1) hat(when);
      if (b === 4) { const sn = AC.createBufferSource(); sn.buffer = noise(); const g = AC.createGain(); g.gain.setValueAtTime(0.18, when); g.gain.exponentialRampToValueAtTime(0.0001, when + 0.15); sn.connect(g); g.connect(musicBus); sn.start(when); sn.stop(when + 0.16); }
      tone(NOTE(ch[b % 3] + 12 + (b > 3 ? 12 : 0)), when, spb * 0.9, "triangle", 0.11, 0.005, 0.1);
      if (b === 0) tone(NOTE(ch[0] - 12), when, spb * 7.5, "sawtooth", 0.12, 0.02, 0.4, 600);
    } else if (this.mood === "calma") {
      if (b === 0) ch.forEach(n => tone(NOTE(n), when, spb * 8.2, "sine", 0.07, 0.6, 1.2));
      if (b === 0) tone(NOTE(ch[0] - 12), when, spb * 8, "sine", 0.1, 0.3, 1);
      if (b === 2 || b === 5 || b === 7) tone(NOTE(ch[(s * 7) % 3] + 24), when, spb * 3, "sine", 0.05, 0.005, 0.8);
    } else if (this.mood === "epica") {
      if (b === 0) ch.forEach(n => tone(NOTE(n - 12), when, spb * 8.2, "sawtooth", 0.05, 0.5, 1, 900));
      if (b === 0) tone(NOTE(ch[0] - 24), when, spb * 8, "sawtooth", 0.1, 0.1, 0.8, 300);
      if (b === 0 || b === 3 || b === 6) kick(when, b === 0 ? 1 : 0.6);
      if (b === 7) tone(NOTE(ch[2] + 12), when, spb * 1.5, "square", 0.03, 0.01, 0.3, 2000);
    }
  },
  stop() {
    clearInterval(this.timer); this.timer = null;
    if (AC && musicBus) { const n = AC.currentTime; musicBus.gain.cancelScheduledValues(n); musicBus.gain.setValueAtTime(musicBus.gain.value, n); musicBus.gain.linearRampToValueAtTime(0, n + 0.15); }
  }
};
function previewMusic(mood) {
  if (!audio()) return; AC.resume();
  const prev = P.music; P.music = mood; Music.start(0); P.music = prev;
  setTimeout(() => { if (!player.playing) Music.stop(); }, 3500);
}

/* ============ narração: arquivo enviado ou gravado ============ */
// o áudio é decodificado na memória e tocado pelo AudioContext (funciona também para a gravação do vídeo)
let narrSrc = null;
async function setNarration(blob, name) {
  if (!audio()) { toast("Este navegador não toca áudio."); return; }
  try {
    const buf = await AC.decodeAudioData(await blob.arrayBuffer());
    runtime.narrBuf = buf; runtime.narrationUrl = "mem"; runtime.narrationName = name; runtime.narrationDur = buf.duration;
    timelineDirty = true; renderStep();
  } catch (e) { toast("Não consegui ler esse áudio. Tente mp3, m4a ou wav."); }
}
function startNarration(offset) {
  stopNarration();
  if (!runtime.narrBuf || offset >= runtime.narrBuf.duration) return;
  narrSrc = AC.createBufferSource(); narrSrc.buffer = runtime.narrBuf; narrSrc.connect(voiceBus);
  narrSrc.start(AC.currentTime + 0.02, Math.max(0, offset));
}
function stopNarration() { if (narrSrc) { try { narrSrc.stop(); } catch (e) {} narrSrc.disconnect(); narrSrc = null; } }

/* ============ voz do navegador (prévia) ============ */
let voices = [];
function loadVoices() { try { voices = speechSynthesis.getVoices() || []; } catch (e) { voices = []; } }
if ("speechSynthesis" in window) { loadVoices(); speechSynthesis.onvoiceschanged = () => { loadVoices(); if (step === 4) renderStep(); }; }
function pickVoice() {
  const lang = P.voice.lang.toLowerCase();
  const list = voices.filter(v => v.lang && v.lang.toLowerCase().replace("_", "-").startsWith(lang.slice(0, 2)));
  return list.find(v => v.name === P.voice.voiceName) || list.find(v => v.lang.toLowerCase().replace("_", "-") === lang) || list[0] || null;
}
let speakingNow = false;
function speak(text, onend) {
  if (!("speechSynthesis" in window) || !text) return;
  try {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    const v = pickVoice(); if (v) u.voice = v;
    u.lang = P.voice.lang; u.rate = P.voice.rate || 1;
    u.onstart = () => speakingNow = true;
    u.onend = u.onerror = () => { speakingNow = false; onend && onend(); };
    speechSynthesis.speak(u);
  } catch (e) {}
}
function stopSpeak() { try { speechSynthesis.cancel(); } catch (e) {} speakingNow = false; }

/* ============ imagens ============ */
const photoImg = new Image();
let photoReady = false;
function loadPhoto() { photoReady = false; if (P.presenter.photo) { photoImg.onload = () => photoReady = true; photoImg.src = P.presenter.photo; } }
function fileToSmallDataURL(file, max = 640) {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => { const im = new Image(); im.onload = () => { const k = Math.min(1, max / Math.max(im.width, im.height)); const c = document.createElement("canvas"); c.width = Math.round(im.width * k); c.height = Math.round(im.height * k); c.getContext("2d").drawImage(im, 0, 0, c.width, c.height); res(c.toDataURL("image/jpeg", 0.85)); }; im.onerror = rej; im.src = r.result; };
    r.onerror = rej; r.readAsDataURL(file);
  });
}

/* ============ renderizador ============ */
const cv = $("#cv"), ctx = cv.getContext("2d");
function fmt() { return FORMATS.find(f => f.id === P.format) || FORMATS[0]; }
function setCanvasSize() { const f = fmt(); if (cv.width !== f.w || cv.height !== f.h) { cv.width = f.w; cv.height = f.h; } }
function font(tpl, size) { return tpl.replace("{s}", Math.round(size)); }
function wrap(text, maxW) {
  const ws = String(text).split(/\s+/).filter(Boolean); const lines = []; let line = "";
  for (const w of ws) { const t = line ? line + " " + w : w; if (ctx.measureText(t).width > maxW && line) { lines.push(line); line = w; } else line = t; }
  if (line) lines.push(line); return lines;
}
function fitText(text, tpl, maxW, maxLines, start, min) {
  let s = start;
  while (s > min) { ctx.font = font(tpl, s); const L = wrap(text, maxW); if (L.length <= maxLines && L.every(l => ctx.measureText(l).width <= maxW)) return { size: s, lines: L }; s -= 2; }
  ctx.font = font(tpl, min); return { size: min, lines: wrap(text, maxW).slice(0, maxLines + 1) };
}
function rr(x, y, w, h, r) { ctx.beginPath(); ctx.roundRect ? ctx.roundRect(x, y, w, h, r) : ctx.rect(x, y, w, h); }
function cover(src, sw, sh, x, y, w, h) {
  const k = Math.max(w / sw, h / sh), dw = sw * k, dh = sh * k;
  ctx.drawImage(src, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
}
function hash(n) { const x = Math.sin(n * 127.1) * 43758.5453; return x - Math.floor(x); }

function drawBackground(st, key, idx, lt, T, W, H) {
  const BA = ctx.globalAlpha, ga = v => ctx.globalAlpha = BA * v;
  const pal = st.pal[idx % st.pal.length];
  const clip = runtime.clipVideos[TL.scenes[idx]?.s.id];
  if (clip && clip.readyState >= 2 && clip.videoWidth) {
    cover(clip, clip.videoWidth, clip.videoHeight, 0, 0, W, H);
    const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, "rgba(0,0,0,.35)"); g.addColorStop(0.45, "rgba(0,0,0,0)"); g.addColorStop(1, "rgba(0,0,0,.55)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); return true;
  }
  const m = Math.min(W, H);
  if (key === "vibrante") {
    const g = ctx.createLinearGradient(0, 0, W, H); g.addColorStop(0, pal[0]); g.addColorStop(1, pal[1]); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    for (let i = 0; i < 7; i++) { const r = m * (0.08 + hash(i + idx * 9) * 0.22); const x = W * hash(i * 3.1 + idx) + Math.sin(T * 0.6 + i) * m * 0.05; const y = H * hash(i * 7.7 + idx) + Math.cos(T * 0.5 + i * 2) * m * 0.05; ctx.fillStyle = `rgba(255,255,255,${0.08 + hash(i) * 0.1})`; ctx.beginPath(); if (i % 3 === 0) { ctx.arc(x, y, r, 0, 7); } else if (i % 3 === 1) { ctx.save(); ctx.translate(x, y); ctx.rotate(T * 0.3 + i); rr(-r, -r, r * 2, r * 2, r * 0.35); ctx.restore(); } else { ctx.moveTo(x, y - r); ctx.lineTo(x + r, y + r); ctx.lineTo(x - r, y + r); ctx.closePath(); } ctx.fill(); }
  } else if (key === "neon") {
    ctx.fillStyle = "#07051a"; ctx.fillRect(0, 0, W, H);
    const hz = H * 0.62; ctx.strokeStyle = pal[0]; ctx.lineWidth = 2; ctx.shadowColor = pal[0]; ctx.shadowBlur = 12; ga(0.55);
    for (let i = -12; i <= 12; i++) { ctx.beginPath(); ctx.moveTo(W / 2 + i * m * 0.02, hz); ctx.lineTo(W / 2 + i * m * 0.25, H); ctx.stroke(); }
    for (let i = 0; i < 10; i++) { const p = ((i / 10) + (T * 0.25) % 0.1) % 1; const y = hz + (H - hz) * p * p; ga(0.15 + p * 0.5); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    ga(1); ctx.shadowBlur = 0;
    const g = ctx.createRadialGradient(W / 2, hz, 0, W / 2, hz, m * 0.6); g.addColorStop(0, pal[1] + "55"); g.addColorStop(1, "transparent"); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    for (let i = 0; i < 40; i++) { ctx.fillStyle = `rgba(255,255,255,${0.2 + 0.6 * hash(i * 5.3)})`; ctx.fillRect(W * hash(i * 1.7), hz * hash(i * 9.1), 2, 2); }
  } else if (key === "giz") {
    const g = ctx.createRadialGradient(W / 2, H / 2, m * 0.1, W / 2, H / 2, Math.max(W, H) * 0.8); g.addColorStop(0, pal[1]); g.addColorStop(1, pal[0]); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ga(0.06); for (let i = 0; i < 60; i++) { ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.ellipse(W * hash(i * 2.3 + idx), H * hash(i * 4.1), m * 0.12 * hash(i), m * 0.03, hash(i * 8) * 3, 0, 7); ctx.fill(); }
    ga(1); ctx.strokeStyle = "#8a6a43"; ctx.lineWidth = m * 0.03; ctx.strokeRect(0, 0, W, H);
  } else if (key === "aquarela") {
    ctx.fillStyle = "#f8f2e8"; ctx.fillRect(0, 0, W, H);
    for (let i = 0; i < 6; i++) { const c = pal[i % 2]; const x = W * hash(i * 2.9 + idx * 3), y = H * hash(i * 6.1 + idx), r = m * (0.25 + 0.25 * hash(i * 3.3)); const g = ctx.createRadialGradient(x, y, 0, x, y, r * (1 + Math.sin(T * 0.4 + i) * 0.04)); g.addColorStop(0, c + "aa"); g.addColorStop(0.7, c + "33"); g.addColorStop(1, c + "00"); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); }
  } else if (key === "cinema") {
    const z = 1 + lt * 0.015; ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-W / 2, -H / 2);
    const g = ctx.createRadialGradient(W * 0.4, H * 0.4, 0, W / 2, H / 2, Math.max(W, H) * 0.75); g.addColorStop(0, pal[1]); g.addColorStop(1, pal[0]); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
    for (let i = 0; i < 18; i++) { const x = W * hash(i * 3.7 + idx), y = (H * hash(i * 1.9) - T * m * 0.02 * (0.5 + hash(i))) % H; ctx.fillStyle = "rgba(255,220,170,.25)"; ctx.beginPath(); ctx.arc(x, (y + H) % H, m * 0.004 * (1 + hash(i * 2) * 2), 0, 7); ctx.fill(); }
  } else if (key === "infantil") {
    const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, pal[0]); g.addColorStop(1, pal[1]); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#ffd84a"; ctx.beginPath(); ctx.arc(W * 0.84, H * 0.1, m * 0.09, 0, 7); ctx.fill();
    for (let i = 0; i < 4; i++) { const x = ((W * hash(i * 4.4) + T * m * 0.03 * (1 + i * 0.3)) % (W + m * 0.5)) - m * 0.25, y = H * (0.08 + 0.2 * hash(i * 2.2)), s = m * (0.07 + 0.04 * hash(i)); ctx.fillStyle = "rgba(255,255,255,.92)"; ctx.beginPath(); ctx.arc(x, y, s, 0, 7); ctx.arc(x + s * 1.1, y - s * 0.4, s * 1.2, 0, 7); ctx.arc(x + s * 2.2, y, s, 0, 7); ctx.fill(); }
    ctx.fillStyle = "#7fd36b"; ctx.beginPath(); ctx.ellipse(W * 0.25, H * 1.02, W * 0.6, H * 0.12, 0, 0, 7); ctx.fill(); ctx.fillStyle = "#62bf55"; ctx.beginPath(); ctx.ellipse(W * 0.85, H * 1.04, W * 0.5, H * 0.12, 0, 0, 7); ctx.fill();
  } else if (key === "empresa") {
    ctx.fillStyle = pal[0]; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#2453d6"; const p = easeOut(lt / 0.8); ctx.beginPath(); ctx.moveTo(W, H * (1 - 0.42 * p)); ctx.lineTo(W, H); ctx.lineTo(W * (1 - 0.7 * p), H); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#ff5a36"; ctx.fillRect(m * 0.07, m * 0.07, m * 0.12 * p, m * 0.012);
    ctx.strokeStyle = "rgba(14,27,61,.07)"; ctx.lineWidth = 1; for (let x = 0; x < W; x += m / 12) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
  }
  return false;
}

function voiceLevel(T) {
  if (analyser && player.playing && (P.voice.mode === "upload" || P.voice.mode === "record") && runtime.narrationUrl) {
    const a = new Uint8Array(analyser.fftSize); analyser.getByteTimeDomainData(a);
    let s = 0; for (let i = 0; i < a.length; i++) { const v = (a[i] - 128) / 128; s += v * v; } return clamp(Math.sqrt(s / a.length) * 5, 0, 1);
  }
  if (player.playing && P.voice.mode === "browser" && speakingNow) return 0.35 + 0.35 * Math.abs(Math.sin(T * 13)) * Math.abs(Math.sin(T * 5.3));
  return 0;
}

function drawScene(x, T, W, H, alpha) {
  const st = STYLES[P.style] || STYLES.vibrante, key = P.style in STYLES ? P.style : "vibrante";
  const lt = T - x.start, s = x.s, m = Math.min(W, H), vertical = H > W;
  ctx.save(); ctx.globalAlpha = alpha;
  const hasClip = drawBackground(st, key, x.i, lt, T, W, H);
  const fg = hasClip ? "#ffffff" : st.fg;

  // marca
  if (P.brand) { ctx.font = font(st.sub, m * 0.032); ctx.fillStyle = fg; ctx.globalAlpha = alpha * 0.85; ctx.textAlign = "left"; ctx.textBaseline = "top"; ctx.fillText(P.brand, m * 0.06, m * 0.05 + (key === "cinema" ? H * 0.1 : 0)); ctx.globalAlpha = alpha; }

  // emoji ilustrativo
  const showEmoji = !hasClip && s.emoji;
  const eSize = m * (vertical ? 0.3 : 0.24);
  const titleY = vertical ? H * 0.2 : H * 0.2;
  if (showEmoji) {
    const p = easeBack(lt / 0.55), bob = Math.sin(T * 2.2) * m * 0.012;
    const ex = vertical ? W / 2 : W * 0.74, ey = vertical ? H * 0.52 : H * 0.5;
    ctx.save(); ctx.translate(ex, ey + bob); ctx.rotate(Math.sin(T * 1.3) * 0.06); ctx.scale(p, p);
    ctx.fillStyle = "rgba(0,0,0,.14)"; ctx.beginPath(); ctx.ellipse(0, eSize * 0.55, eSize * 0.42, eSize * 0.08, 0, 0, 7); ctx.fill();
    ctx.font = `${eSize}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(s.emoji, 0, 0);
    ctx.restore();
  }

  // título
  const tw = vertical ? W * 0.84 : (showEmoji ? W * 0.52 : W * 0.8);
  const tx = vertical ? W / 2 : (showEmoji ? W * 0.07 : W / 2);
  const fit = fitText(s.title || "", st.font, tw, vertical ? 3 : 3, m * (key === "cinema" ? 0.14 : 0.105), m * 0.05);
  const lh = fit.size * (key === "cinema" ? 0.98 : 1.08);
  const ty = vertical ? titleY : (H / 2 - (fit.lines.length * lh) / 2 - H * 0.08);
  ctx.textAlign = vertical || !showEmoji ? "center" : "left"; ctx.textBaseline = "top";
  fit.lines.forEach((ln, i) => {
    const p = easeOut((lt - 0.1 - i * 0.12) / 0.45);
    ctx.save(); ctx.globalAlpha = alpha * p; ctx.translate(0, (1 - p) * m * 0.04);
    ctx.font = font(st.font, fit.size);
    if (key === "neon") { ctx.shadowColor = st.pal[x.i % st.pal.length][0]; ctx.shadowBlur = 24; }
    if (key === "vibrante" || hasClip) { ctx.shadowColor = "rgba(0,0,0,.28)"; ctx.shadowBlur = 18; ctx.shadowOffsetY = 4; }
    if (key === "cinema") { try { ctx.letterSpacing = (fit.size * 0.04) + "px"; } catch (e) {} }
    ctx.fillStyle = fg; ctx.fillText(key === "cinema" ? ln.toUpperCase() : ln, tx, ty + i * lh);
    ctx.restore();
  });
  if (key === "giz") { const p = easeOut((lt - 0.5) / 0.6); ctx.strokeStyle = "#ffd36b"; ctx.lineWidth = m * 0.008; ctx.lineCap = "round"; ctx.beginPath(); const uy = ty + fit.lines.length * lh + m * 0.01; const ux0 = vertical || !showEmoji ? W / 2 - tw * 0.3 : tx; ctx.moveTo(ux0, uy); ctx.quadraticCurveTo(ux0 + tw * 0.3 * p, uy + m * 0.015, ux0 + tw * 0.6 * p, uy); ctx.stroke(); }
  if (key === "cinema") { ctx.fillStyle = "#000"; ctx.globalAlpha = alpha; ctx.fillRect(0, 0, W, H * 0.1); ctx.fillRect(0, H * 0.9, W, H * 0.1); for (let i = 0; i < 120; i++) { ctx.fillStyle = `rgba(255,255,255,${hash(i + Math.floor(T * 24) * 13) * 0.06})`; ctx.fillRect(W * hash(i * 1.3 + T), H * hash(i * 2.7 + T), 2, 2); } }

  // apresentador
  const lvl = voiceLevel(T);
  const pr = P.presenter;
  if (pr.type !== "none") {
    const ps = m * (vertical ? 0.2 : 0.2);
    const px = vertical ? W * 0.2 : W * 0.12, py = vertical ? H * 0.74 : H * 0.7;
    const pop = easeBack(lt / 0.5) * (1 + lvl * 0.06);
    ctx.save(); ctx.translate(px, py + Math.sin(T * 2) * m * 0.006); ctx.scale(pop, pop * (1 - lvl * 0.04));
    if (pr.type === "photo" && photoReady) {
      ctx.fillStyle = key === "neon" ? st.pal[0][0] : "#ffffff"; ctx.beginPath(); ctx.arc(0, 0, ps / 2 + m * 0.012 + lvl * m * 0.012, 0, 7); ctx.fill();
      ctx.save(); ctx.beginPath(); ctx.arc(0, 0, ps / 2, 0, 7); ctx.clip(); cover(photoImg, photoImg.width, photoImg.height, -ps / 2, -ps / 2, ps, ps); ctx.restore();
    } else if (pr.type === "emoji" || pr.type === "photo") {
      ctx.fillStyle = "rgba(255,255,255,.9)"; ctx.beginPath(); ctx.arc(0, 0, ps / 2, 0, 7); ctx.fill();
      ctx.font = `${ps * 0.7}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(pr.emoji || "🙂", 0, ps * 0.03);
    }
    // ondas de fala
    if (lvl > 0.05) { ctx.strokeStyle = key === "aquarela" || key === "empresa" ? "rgba(14,27,61,.5)" : "rgba(255,255,255,.75)"; ctx.lineWidth = m * 0.006; ctx.lineCap = "round"; for (let k = 1; k <= 3; k++) { ctx.globalAlpha = alpha * lvl * (1 - k * 0.22); ctx.beginPath(); ctx.arc(ps * 0.48, -ps * 0.1, ps * 0.16 * k, -0.6, 0.6); ctx.stroke(); } }
    ctx.restore();
  }

  // legendas
  if (P.captions && s.text) {
    const ws = s.text.split(/\s+/).filter(Boolean), per = vertical ? 6 : 9;
    const chunks = []; for (let i = 0; i < ws.length; i += per) chunks.push(ws.slice(i, i + per).join(" "));
    const ci = clamp(Math.floor((lt / x.dur) * chunks.length), 0, chunks.length - 1);
    const cs = m * (vertical ? 0.048 : 0.042);
    ctx.font = font(st.sub, cs);
    const capW = vertical ? W * 0.84 : W * 0.66;
    const L = wrap(chunks[ci], capW - cs);
    const bh = L.length * cs * 1.3 + cs * 0.8;
    const by = vertical ? H * 0.86 - bh / 2 : H * 0.88 - bh;
    const bx = vertical ? (W - capW) / 2 : (pr.type !== "none" ? W * 0.27 : (W - capW) / 2);
    ctx.globalAlpha = alpha;
    ctx.fillStyle = hasClip ? "rgba(0,0,0,.6)" : st.capBg; rr(bx, by, capW, bh, cs * 0.5); ctx.fill();
    ctx.fillStyle = hasClip ? "#fff" : st.cap; ctx.textAlign = "center"; ctx.textBaseline = "top";
    L.forEach((ln, i) => ctx.fillText(ln, bx + capW / 2, by + cs * 0.4 + i * cs * 1.3));
  }
  ctx.restore();
}

function renderFrame(T) {
  if (timelineDirty) buildTimeline();
  setCanvasSize();
  const W = cv.width, H = cv.height;
  T = clamp(T, 0, TL.total - 0.001);
  const x = sceneAt(T);
  ctx.clearRect(0, 0, W, H);
  drawScene(x, T, W, H, 1);
  const tr = 0.4, next = TL.scenes[x.i + 1];
  const rem = x.start + x.dur - T;
  if (next && rem < tr) drawScene(next, T, W, H, 1 - rem / tr);
  // progresso
  const st = STYLES[P.style] || STYLES.vibrante;
  ctx.fillStyle = "rgba(255,255,255,.25)"; ctx.fillRect(0, H - 6, W, 6);
  ctx.fillStyle = st.pal[0][0] === "#21392f" ? "#ffd36b" : (P.style === "empresa" ? "#ff5a36" : "#ffffff"); ctx.fillRect(0, H - 6, W * (T / TL.total), 6);
  // linha do tempo da UI
  const bars = $("#timeline").children;
  TL.scenes.forEach((s, i) => { const b = bars[i]?.firstChild; if (b) b.style.width = (clamp((T - s.start) / s.dur, 0, 1) * 100) + "%"; });
  $("#timeLbl").textContent = fmtT(T) + " / " + fmtT(TL.total);
  if (!scrubbing) $("#scrub").value = Math.round(T / TL.total * 1000);
}

/* ============ player ============ */
const player = { playing: false, t: 0, startAt: 0, startPerf: 0, lastScene: -1, onEnd: null, silent: false };
let scrubbing = false;
function now() { return AC ? AC.currentTime : performance.now() / 1000; }
function syncClipsTo(T, play) {
  TL.scenes.forEach(x => {
    const v = runtime.clipVideos[x.s.id]; if (!v) return;
    const inScene = T >= x.start - 0.4 && T < x.start + x.dur;
    if (inScene) { const lt = clamp(T - x.start, 0, (v.duration || 99) - 0.05); if (Math.abs(v.currentTime - lt) > 0.3) { try { v.currentTime = lt; } catch (e) {} } if (play && v.paused) v.play().catch(() => {}); if (!play && !v.paused) v.pause(); }
    else if (!v.paused) v.pause();
  });
}
function play(fromStart) {
  audio(); if (AC) AC.resume();
  if (timelineDirty) buildTimeline();
  if (fromStart || player.t >= TL.total - 0.05) player.t = 0;
  player.playing = true; player.startAt = now() - player.t; player.lastScene = -1;
  if (!player.silent) Music.start(player.t);
  if ((P.voice.mode === "upload" || P.voice.mode === "record") && runtime.narrBuf && !player.silent && AC) startNarration(player.t);
  $("#btnPlay").textContent = "❚❚"; $("#btnPlay").setAttribute("aria-label", "Pausar");
  requestAnimationFrame(loop);
}
function pause() {
  player.playing = false; Music.stop(); stopNarration(); stopSpeak(); syncClipsTo(player.t, false);
  $("#btnPlay").textContent = "▶"; $("#btnPlay").setAttribute("aria-label", "Tocar");
}
function seek(T) { player.t = clamp(T, 0, TL.total); if (player.playing) { pause(); play(); } else { syncClipsTo(player.t, false); renderFrame(player.t); } }
function loop() {
  if (!player.playing) return;
  player.t = now() - player.startAt;
  if (player.t >= TL.total) {
    player.t = TL.total; renderFrame(TL.total - 0.001); pause();
    const cb = player.onEnd; player.onEnd = null; cb && cb(); return;
  }
  const x = sceneAt(player.t);
  if (x.i !== player.lastScene) {
    player.lastScene = x.i;
    if (P.voice.mode === "browser" && !player.silent) speak(x.s.text);
  }
  syncClipsTo(player.t, true);
  renderFrame(player.t);
  requestAnimationFrame(loop);
}
$("#btnPlay").onclick = () => player.playing ? pause() : play();
$("#scrub").addEventListener("input", e => { scrubbing = true; seek(e.target.value / 1000 * TL.total); });
$("#scrub").addEventListener("change", () => scrubbing = false);

/* ============ IA: roteiro ============ */
function scriptPrompt(topic) {
  const pur = PURPOSES.find(p => p.id === P.purpose)?.name || "vídeo";
  const n = clamp(Math.round(P.duration / 7), 3, 10);
  const lang = LANGS.find(l => l.id === P.voice.lang)?.name || "Português";
  const wps = 2.4;
  return `Você é roteirista de vídeos curtos para redes sociais.
Crie o roteiro de um vídeo animado.
Finalidade: ${pur}
Tema / pedido do cliente: ${topic}
Duração total: ${P.duration} segundos, em ${n} cenas.
Formato: ${P.format}. Estilo visual: ${STYLES[P.style]?.name}.
Idioma da narração e dos títulos: ${lang}.

Regras:
- "title": texto curto que aparece grande na tela (máx. 6 palavras).
- "text": a narração falada da cena. No total, cerca de ${Math.round(P.duration * wps)} palavras somando todas as cenas. Linguagem natural, como uma pessoa falando.
- "emoji": um único emoji que ilustra a cena.
- "visual": descrição EM INGLÊS de uma cena animada para um gerador de vídeo por IA (personagens, ambiente, câmera, estilo ${STYLES[P.style]?.name}). Uma frase.
- A primeira cena prende a atenção. A última cena tem uma chamada para ação adequada à finalidade.

Responda somente com JSON neste formato:
{"scenes":[{"title":"...","text":"...","emoji":"🙂","visual":"..."}]}`;
}
function normalizeScenes(data) {
  const arr = Array.isArray(data) ? data : (data && Array.isArray(data.scenes) ? data.scenes : null);
  if (!arr || !arr.length) throw new Error("A IA respondeu num formato inesperado.");
  return arr.slice(0, 12).map(s => ({ id: uid(), title: String(s.title || "").slice(0, 80), text: String(s.text || ""), emoji: String(s.emoji || "🎬").slice(0, 8), visual: String(s.visual || "") }));
}
async function groqChat(prompt) {
  const body = { model: settings.groqModel || "openai/gpt-oss-120b", messages: [{ role: "user", content: prompt }], temperature: 0.8, response_format: { type: "json_object" } };
  let r;
  try {
    r = await fetch("https://api.groq.com/openai/v1/chat/completions", { method: "POST", headers: { "Authorization": "Bearer " + settings.groqKey, "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch (e) {
    throw new Error(ENV.viewer ? "Esta página publicada não pode acessar a Groq. Use a versão para computador." : "Não consegui conectar à Groq. Confira sua internet.");
  }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = j?.error?.message || ("Erro " + r.status);
    if (r.status === 401) throw new Error("A chave da Groq foi recusada. Confira em Chaves de IA.");
    if (/model/i.test(msg)) throw new Error("O modelo \"" + body.model + "\" não está disponível na Groq. Troque o modelo em Chaves de IA.");
    throw new Error("Groq: " + msg);
  }
  const txt = j?.choices?.[0]?.message?.content || "";
  const m = txt.match(/\{[\s\S]*\}/); if (!m) throw new Error("A Groq não devolveu o roteiro em JSON.");
  return JSON.parse(m[0]);
}
function localScenes(topic) {
  const t = topic || "seu produto";
  const base = {
    anuncio: [["Chegou " + t, "Conheça " + t + ". Feito para facilitar o seu dia.", "✨"], ["Por que escolher?", "Qualidade, preço justo e atendimento de verdade.", "💎"], ["Peça agora", "Chame no WhatsApp e garanta o seu hoje mesmo.", "📲"]],
    aula: [["Hoje você aprende", "Hoje você vai aprender sobre " + t + ", passo a passo.", "🎓"], ["Primeiro passo", "Comece pelo básico e entenda a ideia principal.", "1️⃣"], ["Pratique", "Agora pratique. É assim que o conteúdo fixa.", "✍️"], ["Resumo", "Gostou? Salve este vídeo e compartilhe com quem precisa.", "📌"]]
  }[P.purpose] || [["" + t, "Vamos falar sobre " + t + ".", "🎬"], ["O que importa", "Aqui está o ponto principal que você precisa saber.", "💡"], ["Até a próxima", "Gostou? Curta e siga para mais.", "💜"]];
  return base.map(([title, text, emoji]) => ({ id: uid(), title, text, emoji, visual: "Animated scene about " + t }));
}
let aiCtl = null;
async function generateScript(topic) {
  const prompt = scriptPrompt(topic);
  if (ENV.sample) {
    aiCtl = new AbortController();
    try { return normalizeScenes(await ENV.sample.json(prompt, { signal: aiCtl.signal })); }
    catch (e) {
      const code = e && e.code;
      if (code === "not_granted") { ENV.sample = null; updateEnvBadge(); throw new Error("O uso da IA do Claude não foi autorizado nesta página. Escreva o roteiro à mão ou use a versão para computador com a Groq."); }
      if (code === "cancelled") throw new Error("Geração cancelada.");
      if (code === "rate_limited") throw new Error("Muitos pedidos seguidos. Espere alguns segundos e tente de novo.");
      throw new Error(e?.message || "A IA não conseguiu escrever o roteiro agora.");
    }
  }
  if (settings.groqKey) return normalizeScenes(await groqChat(prompt));
  return localScenes(topic);
}

/* ============ IA: clipes de vídeo (Grok Imagine / xAI) ============ */
const clipJobs = {}; // sceneId -> {status, msg}
async function xaiCreate(x) {
  const st = STYLES[P.style]?.name || "";
  const body = {
    model: settings.xaiModel || "grok-imagine-video",
    prompt: (x.s.visual || x.s.title) + `. Style: ${st}. No text, no captions, no letters on screen.`,
    duration: clamp(Math.round(x.dur), 1, 15),
    aspect_ratio: P.format,
    resolution: settings.xaiRes || "480p"
  };
  if (P.presenter.type === "photo" && P.presenter.photo && clipUsePhoto) body.image = { url: P.presenter.photo };
  const r = await fetch("https://api.x.ai/v1/videos/generations", { method: "POST", headers: { "Authorization": "Bearer " + settings.xaiKey, "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(r.status === 401 ? "Chave da xAI recusada." : (j?.error?.message || j?.error || ("Erro " + r.status)));
  if (!j.request_id) throw new Error("A xAI não devolveu o número do pedido.");
  return j.request_id;
}
async function xaiPoll(id) {
  for (let k = 0; k < 150; k++) {
    await new Promise(r => setTimeout(r, 4000));
    const r = await fetch("https://api.x.ai/v1/videos/" + id, { headers: { "Authorization": "Bearer " + settings.xaiKey } });
    const j = await r.json().catch(() => ({}));
    if (j.status === "done" && j.video?.url) return j.video.url;
    if (j.status === "failed") throw new Error(j.error?.message || "A geração falhou.");
    if (!r.ok && r.status !== 202) throw new Error(j?.error?.message || ("Erro " + r.status));
  }
  throw new Error("Demorou demais. Tente esta cena de novo.");
}
function loadClip(sceneId, url) {
  const v = document.createElement("video");
  v.crossOrigin = "anonymous"; v.muted = true; v.playsInline = true; v.preload = "auto"; v.src = url;
  v.addEventListener("loadeddata", () => { if (!player.playing) renderFrame(player.t); });
  runtime.clipVideos[sceneId] = v;
}
let clipUsePhoto = false, clipsRunning = false;
async function generateClips(only) {
  if (!settings.xaiKey) { openSettings(); toast("Cole sua chave da xAI para gerar clipes."); return; }
  if (timelineDirty) buildTimeline();
  clipsRunning = true; renderStep();
  const list = TL.scenes.filter(x => !only || x.s.id === only);
  await Promise.all(list.map(async (x, n) => {
    await new Promise(r => setTimeout(r, n * 2200)); // respeita o limite de pedidos
    clipJobs[x.s.id] = { status: "run", msg: "Gerando…" }; renderClipRows();
    try {
      const id = await xaiCreate(x);
      const url = await xaiPoll(id);
      x.s.clipUrl = url; save(); loadClip(x.s.id, url);
      clipJobs[x.s.id] = { status: "ok", msg: "Pronto" };
    } catch (e) {
      let msg = e.message || String(e);
      if (e instanceof TypeError) msg = ENV.viewer ? "A página publicada não acessa a xAI. Use a versão para computador." : "O navegador bloqueou o acesso à xAI (CORS). Veja a nota abaixo.";
      clipJobs[x.s.id] = { status: "err", msg };
    }
    renderClipRows();
  }));
  clipsRunning = false; renderStep();
}

/* ============ exportação ============ */
let exporting = false, recorder = null;
function pickMime() {
  const opts = [["video/mp4;codecs=avc1.42E01E,mp4a.40.2", "mp4"], ["video/mp4", "mp4"], ["video/webm;codecs=vp9,opus", "webm"], ["video/webm;codecs=vp8,opus", "webm"], ["video/webm", "webm"]];
  if (!window.MediaRecorder) return null;
  for (const [m, e] of opts) { try { if (MediaRecorder.isTypeSupported(m)) return { mime: m, ext: e }; } catch (_) {} }
  return { mime: "", ext: "webm" };
}
async function exportVideo() {
  if (exporting) return;
  const mt = pickMime();
  if (!mt || !cv.captureStream) { toast("Este navegador não grava vídeo. Use o Chrome, Edge ou Safari atualizados."); return; }
  audio(); if (AC) await AC.resume();
  if (timelineDirty) buildTimeline();
  let stream;
  try { stream = cv.captureStream(30); }
  catch (e) { toast("Os clipes de IA não permitem gravação aqui. Baixe os clipes separadamente."); return; }
  const tracks = [...stream.getVideoTracks()];
  if (recDest) recDest.stream.getAudioTracks().forEach(t => tracks.push(t));
  const ms = new MediaStream(tracks);
  const chunks = [];
  try { recorder = new MediaRecorder(ms, mt.mime ? { mimeType: mt.mime, videoBitsPerSecond: 6_000_000 } : undefined); }
  catch (e) { recorder = new MediaRecorder(ms); }
  recorder.ondataavailable = e => { if (e.data && e.data.size) chunks.push(e.data); };
  exporting = true; renderStep();
  $("#liveLbl").classList.add("rec"); $("#liveTxt").textContent = "Gravando";
  const done = new Promise(res => recorder.onstop = res);
  if (player.playing) pause();
  const voiceWas = P.voice.mode;
  if (voiceWas === "browser") P.voice.mode = "none"; // a voz do navegador não entra no arquivo
  player.t = 0;
  recorder.start(500);
  player.onEnd = () => { setTimeout(() => recorder && recorder.state !== "inactive" && recorder.stop(), 250); };
  play(true);
  const prog = setInterval(() => { const b = $("#expBar"); if (b) b.style.width = (player.t / TL.total * 100).toFixed(1) + "%"; const l = $("#expPct"); if (l) l.textContent = Math.round(player.t / TL.total * 100) + "%"; }, 200);
  await done;
  clearInterval(prog);
  P.voice.mode = voiceWas;
  $("#liveLbl").classList.remove("rec"); $("#liveTxt").textContent = "Prévia";
  exporting = false;
  if (!chunks.length || cancelExport) { cancelExport = false; renderStep(); toast("Exportação cancelada."); return; }
  const blob = new Blob(chunks, { type: (mt.mime || "video/webm").split(";")[0] });
  if (runtime.exportUrl) URL.revokeObjectURL(runtime.exportUrl);
  runtime.exportBlob = blob; runtime.exportUrl = URL.createObjectURL(blob); runtime.exportExt = mt.ext;
  renderStep();
  toast("Vídeo pronto! Confira e baixe abaixo.");
}
let cancelExport = false;
function stopExport() { cancelExport = true; player.onEnd = null; pause(); if (recorder && recorder.state !== "inactive") recorder.stop(); }
async function downloadExport() {
  if (!runtime.exportBlob) return;
  const name = (P.name || "video").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\w]+/g, "-").replace(/^-|-$/g, "").toLowerCase() + "." + runtime.exportExt;
  if (ENV.downloads) {
    try { await ENV.downloads.save({ filename: name, data: runtime.exportBlob }); toast("Vídeo salvo."); }
    catch (e) { if (e?.code === "declined") toast("Download cancelado."); else if (e?.code === "rate_limited") toast("Já existe um download aguardando. Tente em instantes."); else toast("Não foi possível baixar aqui. Abra a versão para computador."); }
    return;
  }
  if (ENV.viewer) { toast("Download indisponível nesta visualização."); return; }
  const a = document.createElement("a"); a.href = runtime.exportUrl; a.download = name; document.body.appendChild(a); a.click(); a.remove();
}

/* ============ gravação da própria voz ============ */
let micRec = null;
async function recordVoice() {
  if (micRec) { micRec.stop(); return; }
  let s;
  try { s = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } }); }
  catch (e) { toast(ENV.viewer ? "O microfone não é liberado nesta página. Grave no celular e envie o áudio." : "Não consegui usar o microfone. Libere o acesso no navegador."); return; }
  const parts = []; micRec = new MediaRecorder(s);
  micRec.ondataavailable = e => e.data.size && parts.push(e.data);
  micRec.onstop = () => { s.getTracks().forEach(t => t.stop()); micRec = null; player.silent = false; pause(); setNarration(new Blob(parts, { type: parts[0]?.type || "audio/webm" }), "Gravação"); P.voice.mode = "record"; save(); renderStep(); toast("Narração gravada."); };
  micRec.start();
  player.silent = true; player.onEnd = () => micRec && micRec.stop(); play(true); renderStep();
}

/* ============ telas dos passos ============ */
function optCard(on, attrs, ico, title, desc, extra = "") { return `<button class="opt${on ? " on" : ""}" ${attrs} aria-pressed="${on}">${extra}${ico ? `<span class="ico">${ico}</span>` : ""}<b>${esc(title)}</b>${desc ? `<span>${esc(desc)}</span>` : ""}</button>`; }
function head(n, title, lead) { return `<div class="eyebrow">Passo ${n + 1} de ${STEPS.length}</div><h1 class="step-title">${title}</h1><p class="lead">${lead}</p>`; }
function hint(html, cls = "") { return `<div class="hint ${cls}"><span>💡</span><div>${html}</div></div>`; }

const VIEWS = [
  () => head(0, "Para que é o seu vídeo?", "A finalidade ajusta o roteiro, o ritmo e o estilo sugerido.") +
    `<div class="grid">${PURPOSES.map(p => optCard(P.purpose === p.id, `data-purpose="${p.id}"`, p.ico, p.name, p.desc)).join("")}</div>` +
    `<div class="section"><label class="f" for="pname">Nome do projeto<input id="pname" type="text" value="${esc(P.name)}" maxlength="80"></label></div>`,

  () => head(1, "Formato e duração", "Vertical para Reels e Stories, horizontal para YouTube, quadrado para o feed.") +
    `<div class="grid">${FORMATS.map(f => optCard(P.format === f.id, `data-format="${f.id}"`, f.ico, f.name, f.desc)).join("")}</div>` +
    `<div class="section"><h3>Duração</h3><div class="seg">${DURATIONS.map(d => `<button data-dur="${d}" class="${P.duration === d ? "on" : ""}">${d} s</button>`).join("")}</div></div>` +
    hint("O mesmo roteiro pode sair nos três formatos. Troque aqui e veja a prévia se ajustar."),

  () => head(2, "Estilo da animação", "Cada estilo tem fundo animado, tipografia e transições próprias.") +
    `<div class="grid">${Object.entries(STYLES).map(([k, s]) => optCard(P.style === k, `data-style="${k}"`, "", s.name, s.desc, `<div class="swatch" style="background:${s.sw}"></div>`)).join("")}</div>` +
    hint("Com a chave da xAI, cada cena também pode virar um <b>clipe animado gerado por IA</b> nesse estilo. Isso fica no último passo."),

  () => head(3, "Quem apresenta?", "Use a sua foto, escolha um personagem ou faça o vídeo sem apresentador.") +
    `<div class="grid">${[["none", "🚫", "Sem apresentador", "Só texto e animação"], ["emoji", "🦊", "Personagem", "Bichos e pessoas animadas"], ["photo", "📸", "Minha foto", "Sua foto no vídeo"]].map(([id, ic, n, d]) => optCard(P.presenter.type === id, `data-ptype="${id}"`, ic, n, d)).join("")}</div>` +
    (P.presenter.type === "emoji" ? `<div class="section"><h3>Escolha o personagem</h3><div class="seg">${CHARACTERS.map(c => `<button data-char="${c}" class="${P.presenter.emoji === c ? "on" : ""}" style="font-size:22px;padding:6px 10px">${c}</button>`).join("")}</div></div>` : "") +
    (P.presenter.type === "photo" ? `<div class="section"><h3>Envie uma foto sua</h3><div class="photo-drop"><div class="ph" style="${P.presenter.photo ? `background-image:url(${P.presenter.photo});border-style:solid` : ""}">${P.presenter.photo ? "" : "sem foto"}</div><div style="display:flex;flex-direction:column;gap:8px"><label class="btn" for="photoIn">Escolher foto</label><input id="photoIn" type="file" accept="image/*" hidden>${P.presenter.photo ? `<button class="btn ghost sm" id="photoDel">Remover foto</button>` : ""}</div></div>` +
      hint("Use uma foto de frente e bem iluminada. Na prévia ela aparece num círculo que reage à voz. Para a foto <b>falar com movimento de boca</b>, use os clipes de IA (xAI) no último passo, com a opção de usar sua foto como imagem inicial.") + "</div>" : ""),

  () => {
    const vs = voices.filter(v => v.lang && v.lang.toLowerCase().replace("_", "-").startsWith(P.voice.lang.slice(0, 2).toLowerCase()));
    return head(4, "Voz e idioma", "Escolha como a narração vai soar.") +
      `<div class="grid">${[["browser", "🗣️", "Voz pronta", "Vozes do navegador, só na prévia"], ["record", "🎙️", "Minha voz", "Grave lendo o roteiro"], ["upload", "📁", "Enviar áudio", "Narração gravada no celular"], ["none", "🔇", "Sem voz", "Só música e legendas"]].map(([id, ic, n, d]) => optCard(P.voice.mode === id, `data-vmode="${id}"`, ic, n, d)).join("")}</div>` +
      `<div class="section"><h3>Idioma</h3><div class="seg">${LANGS.map(l => `<button data-lang="${l.id}" class="${P.voice.lang === l.id ? "on" : ""}">${l.name}</button>`).join("")}</div></div>` +
      (P.voice.mode === "browser" ? `<div class="section"><h3>Voz</h3>${vs.length ? `<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><select id="voiceSel" style="flex:1 1 240px;width:auto">${vs.map(v => `<option ${pickVoice()?.name === v.name ? "selected" : ""}>${esc(v.name)}</option>`).join("")}</select><button class="btn" id="voiceTest">▶ Ouvir</button></div>` : `<p class="lead">Nenhuma voz neste idioma foi encontrada no seu navegador.</p>`}<label class="f" style="margin-top:12px" for="rate">Velocidade: ${(P.voice.rate || 1).toFixed(1)}×<input id="rate" type="range" min="0.7" max="1.4" step="0.1" value="${P.voice.rate || 1}"></label>` + hint("A voz pronta toca na prévia, mas o navegador não deixa ela ser gravada dentro do arquivo de vídeo. Para ter narração no vídeo baixado, use <b>Minha voz</b> ou <b>Enviar áudio</b>.", "warn") + "</div>" : "") +
      (P.voice.mode === "record" ? `<div class="section"><h3>Gravar narração</h3><p class="lead">Ao clicar, o vídeo toca sem som e as legendas viram teleprompter. Leia em voz alta. A gravação para sozinha no fim.</p><button class="btn primary" id="recBtn">${micRec ? "■ Parar gravação" : "● Começar a gravar"}</button>${runtime.narrationUrl ? `<p class="mon-note" style="margin-top:10px">Narração atual: ${esc(runtime.narrationName)} · ${fmtT(runtime.narrationDur)}</p>` : ""}${ENV.viewer ? hint("Esta página publicada não tem acesso ao microfone. Grave no celular e use <b>Enviar áudio</b>, ou use a versão para computador.", "warn") : ""}</div>` : "") +
      (P.voice.mode === "upload" ? `<div class="section"><h3>Arquivo de narração</h3><label class="btn" for="audIn">Escolher áudio (mp3, m4a, wav, ogg)</label><input id="audIn" type="file" accept="audio/*" hidden>${runtime.narrationUrl ? `<p class="mon-note" style="margin-top:10px">${esc(runtime.narrationName)} · ${fmtT(runtime.narrationDur)}. A duração do vídeo segue o áudio.</p>` : ""}</div>` : "");
  },

  () => head(5, "Escreva o texto ou deixe a IA criar", "Cada cena tem um título que aparece grande na tela e a fala da narração.") +
    `<div class="gen-card"><h3>✨ A IA cria o roteiro</h3><p class="mon-note" style="margin:0">${engineName() ? `Usando <b>${engineName()}</b>. Diga o tema e o que não pode faltar.` : ENV.hostAI ? `O roteiro com IA (${esc(ENV.hostAI)}) é gerado no <b>topo da página</b>, acima do estúdio. As cenas aparecem aqui para você editar.` : "Nenhuma IA conectada: vou montar um roteiro-modelo. Para roteiros de verdade, cole a chave da Groq em <b>Chaves de IA</b> (versão para computador)."}</p>
      <div class="ai-box"><input id="topic" type="text" placeholder="Ex.: Promoção de pizza de sexta, 2 por R$ 79" value="${esc(P.topic || "")}"><button class="btn primary" id="aiBtn" ${aiBusy ? "disabled" : ""}>${aiBusy ? "Escrevendo…" : "Gerar roteiro"}</button>${aiBusy && ENV.sample ? `<button class="btn" id="aiStop">Parar</button>` : ""}</div></div>` +
    `<div class="scenes" id="sceneList">${P.scenes.map((s, i) => sceneCard(s, i)).join("")}</div>` +
    `<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn" id="addScene">+ Adicionar cena</button></div>`,

  () => head(6, "Música, legendas e marca", "Trilhas criadas na hora, sem direitos autorais.") +
    `<div class="grid">${Object.entries(MUSIC).map(([k, m]) => optCard(P.music === k, `data-music="${k}"`, m.ico, m.name, m.desc)).join("")}</div>` +
    (P.music !== "none" ? `<div style="margin-top:10px"><button class="btn sm" id="musTest">▶ Ouvir trecho</button></div>` : "") +
    `<div class="section"><h3>Legendas</h3><div class="seg"><button data-cap="1" class="${P.captions ? "on" : ""}">Mostrar legendas</button><button data-cap="0" class="${!P.captions ? "on" : ""}">Sem legendas</button></div></div>` +
    `<div class="section"><label class="f" for="brand">Sua marca ou @ (aparece no canto)<input id="brand" type="text" maxlength="40" value="${esc(P.brand || "")}" placeholder="@seuperfil"></label></div>`,

  () => {
    const dur = TL.total, xaiCost = (settings.xaiRes === "720p" ? 0.07 : 0.05) * TL.scenes.reduce((a, x) => a + clamp(Math.round(x.dur), 1, 15), 0);
    const narrInFile = (P.voice.mode === "upload" || P.voice.mode === "record") && runtime.narrationUrl;
    return head(7, "Clique em gerar e pronto!", "O vídeo é gravado em tempo real a partir da prévia, com animação, música e narração.") +
      `<div class="gen-card">
        <h3>🎬 Gerar meu vídeo</h3>
        <ul class="checklist">
          <li class="ok"><span class="s">✓</span>${TL.scenes.length} cenas · ${fmtT(dur)} · ${P.format}</li>
          <li class="ok"><span class="s">✓</span>Estilo ${STYLES[P.style]?.name} · música ${MUSIC[P.music]?.name.toLowerCase()}</li>
          <li class="${narrInFile ? "ok" : ""}"><span class="s">${narrInFile ? "✓" : "–"}</span>${narrInFile ? "Narração incluída no arquivo" : (P.voice.mode === "browser" ? "Voz pronta só na prévia (não entra no arquivo)" : "Sem narração no arquivo")}</li>
          <li class="${Object.keys(runtime.clipVideos).length ? "ok" : ""}"><span class="s">${Object.keys(runtime.clipVideos).length ? "✓" : "–"}</span>${Object.keys(runtime.clipVideos).length ? "Clipes de IA nas cenas" : "Fundos animados do estilo"}</li>
        </ul>
        ${exporting ? `<div class="bar"><i id="expBar"></i></div><div style="display:flex;justify-content:space-between;align-items:center"><span class="mon-note">Gravando… <span id="expPct">0%</span>. Deixe esta aba aberta e visível.</span><button class="btn sm" id="expStop">Cancelar</button></div>`
          : `<button class="btn primary" id="expBtn" style="align-self:flex-start">🎬 Gerar meu vídeo (${fmtT(dur)})</button>`}
        ${runtime.exportUrl && !exporting ? `<video class="result-video" src="${runtime.exportUrl}" controls playsinline></video><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" id="dlBtn">⬇ Baixar vídeo (.${runtime.exportExt})</button><span class="mon-note" style="align-self:center">${(runtime.exportBlob.size / 1048576).toFixed(1)} MB</span></div>` : ""}
      </div>` +
      `<div class="gen-card" style="margin-top:16px">
        <h3>🤖 Clipes animados por IA (Grok Imagine · xAI)</h3>
        <p class="mon-note" style="margin:0">Cada cena vira um clipe animado gerado por IA, usado como fundo do vídeo. Custo estimado: <b>US$ ${xaiCost.toFixed(2)}</b> em ${settings.xaiRes || "480p"}. ${settings.xaiKey ? "Chave da xAI configurada." : "Precisa da chave da xAI (console.x.ai)."}</p>
        ${P.presenter.type === "photo" && P.presenter.photo ? `<label style="display:flex;gap:8px;align-items:center;font-size:13.5px"><input type="checkbox" id="usePhoto" ${clipUsePhoto ? "checked" : ""}> Usar minha foto como imagem inicial (animar minha foto)</label>` : ""}
        <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn" id="clipBtn" ${clipsRunning ? "disabled" : ""}>${clipsRunning ? "Gerando clipes…" : (settings.xaiKey ? "Gerar clipes de todas as cenas" : "Configurar chave da xAI")}</button>${Object.keys(runtime.clipVideos).length && !clipsRunning ? `<button class="btn ghost" id="clipClear">Remover clipes</button>` : ""}</div>
        <div id="clipRows"></div>
        ${ENV.viewer ? hint("Esta página publicada não consegue falar com a xAI. Os clipes funcionam na <b>versão para computador</b> que te mandei no chat.", "warn") : ""}
      </div>`;
  }
];
let aiBusy = false;
function sceneCard(s, i) {
  const x = TL.scenes[i];
  return `<div class="scene" data-sid="${s.id}">
    <input class="em" data-f="emoji" value="${esc(s.emoji)}" aria-label="Emoji da cena ${i + 1}" maxlength="8">
    <div class="fields">
      <input type="text" data-f="title" value="${esc(s.title)}" placeholder="Título na tela" aria-label="Título da cena ${i + 1}">
      <textarea data-f="text" rows="2" placeholder="O que a narração fala nesta cena" aria-label="Narração da cena ${i + 1}">${esc(s.text)}</textarea>
      <details class="vis"><summary>Descrição para o clipe de IA</summary><textarea data-f="visual" rows="2" style="margin-top:6px" placeholder="Em inglês, ex.: a happy dog cooking in a colorful kitchen, 3D cartoon">${esc(s.visual)}</textarea></details>
      <span class="meta">Cena ${i + 1} · ${x ? x.dur.toFixed(1) + " s" : ""} · ${words(s.text)} palavras</span>
    </div>
    <div class="tools">
      <button class="iconbtn" data-act="play" title="Ver esta cena" aria-label="Ver cena ${i + 1}">▶</button>
      <button class="iconbtn" data-act="up" title="Subir" aria-label="Subir cena ${i + 1}">↑</button>
      <button class="iconbtn" data-act="down" title="Descer" aria-label="Descer cena ${i + 1}">↓</button>
      <button class="iconbtn" data-act="del" title="Apagar" aria-label="Apagar cena ${i + 1}">✕</button>
    </div>
  </div>`;
}
function renderClipRows() {
  const el = $("#clipRows"); if (!el) return;
  el.innerHTML = TL.scenes.map(x => {
    const j = clipJobs[x.s.id] || (runtime.clipVideos[x.s.id] ? { status: "ok", msg: "Pronto" } : null);
    const url = x.s.clipUrl;
    return `<div class="clip-row"><span class="pill">${x.i + 1}</span><span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(x.s.title)}${j && j.status === "err" ? `<br><small style="color:#ff8a7a;white-space:normal">${esc(j.msg)}</small>` : ""}</span><span style="display:flex;gap:6px;align-items:center">${j ? `<span class="pill ${j.status}">${esc(j.status === "run" ? "Gerando…" : j.status === "ok" ? "Pronto" : "Erro")}</span>` : ""}${url ? `<a class="btn sm ghost" href="${esc(url)}" target="_blank" rel="noopener">Abrir</a>` : ""}${!clipsRunning && settings.xaiKey ? `<button class="btn sm ghost" data-clip="${x.s.id}">${url ? "Refazer" : "Gerar"}</button>` : ""}</span></div>`;
  }).join("");
}

function renderSteps() {
  $("#steps").innerHTML = STEPS.map((n, i) => `<button class="step-chip${i === step ? " on" : ""}${i < step ? " done" : ""}" data-step="${i}"><span class="n">${i < step ? "✓" : i + 1}</span>${n}</button>`).join("");
  const nav = $("#steps"), c = nav.children[step];
  if (c && (c.offsetLeft < nav.scrollLeft || c.offsetLeft + c.offsetWidth > nav.scrollLeft + nav.clientWidth)) nav.scrollLeft = c.offsetLeft - 16;
}
function renderStep() {
  if (timelineDirty) buildTimeline();
  renderSteps();
  $("#stepBody").innerHTML = VIEWS[step]();
  $("#btnPrev").disabled = step === 0;
  $("#btnNext").textContent = step === STEPS.length - 1 ? "Novo vídeo +" : "Próximo →";
  $("#projName").textContent = "· " + (P.name || "Sem nome");
  const f = fmt(); $("#fmtLbl").textContent = f.id + " · " + fmtT(TL.total);
  $("#monNote").innerHTML = P.voice.mode === "browser" ? "A voz pronta toca na prévia. Clique ▶ para ouvir." : (P.voice.mode === "record" || P.voice.mode === "upload") && !runtime.narrationUrl ? "Sem narração ainda. Grave ou envie o áudio no passo Voz." : "";
  if (step === 7) renderClipRows();
  const fb = $("#btnFinish");
  fb.disabled = exporting;
  fb.textContent = exporting ? "Gravando o vídeo…" : runtime.exportUrl ? "⬇ Baixar vídeo pronto" : "🎬 Finalizar vídeo";
  if (!player.playing) renderFrame(player.t);
  store.set("evs.step", step);
}

/* ============ eventos ============ */
document.addEventListener("click", async e => {
  const t = e.target.closest("button,[data-step]"); if (!t) return;
  const d = t.dataset;
  if (d.step != null) { step = +d.step; renderStep(); window.scrollTo({ top: 0, behavior: "smooth" }); return; }
  if (d.purpose) { P.purpose = d.purpose; const pp = PURPOSES.find(p => p.id === d.purpose); if (pp) { P.style = pp.style; P.music = pp.music; } save(); renderStep(); return; }
  if (d.format) { P.format = d.format; save(); renderStep(); return; }
  if (d.dur) { P.duration = +d.dur; save(); renderStep(); return; }
  if (d.style) { P.style = d.style; save(); renderStep(); return; }
  if (d.ptype) { P.presenter.type = d.ptype; if (d.ptype === "emoji" && !P.presenter.emoji) P.presenter.emoji = "🦊"; save(); renderStep(); return; }
  if (d.char) { P.presenter.emoji = d.char; save(); renderStep(); return; }
  if (d.vmode) { P.voice.mode = d.vmode; save(); renderStep(); return; }
  if (d.lang) { P.voice.lang = d.lang; P.voice.voiceName = ""; save(); renderStep(); return; }
  if (d.music) { P.music = d.music; save(); renderStep(); if (d.music !== "none") previewMusic(d.music); return; }
  if (d.cap) { P.captions = d.cap === "1"; save(); renderStep(); return; }
  if (d.clip) { generateClips(d.clip); return; }
  if (d.act) {
    const card = t.closest(".scene"); const i = P.scenes.findIndex(s => s.id === card.dataset.sid); if (i < 0) return;
    if (d.act === "del") { if (P.scenes.length <= 1) { toast("O vídeo precisa de pelo menos uma cena."); return; } P.scenes.splice(i, 1); }
    if (d.act === "up" && i > 0) [P.scenes[i - 1], P.scenes[i]] = [P.scenes[i], P.scenes[i - 1]];
    if (d.act === "down" && i < P.scenes.length - 1) [P.scenes[i + 1], P.scenes[i]] = [P.scenes[i], P.scenes[i + 1]];
    if (d.act === "play") { if (timelineDirty) buildTimeline(); seek(TL.scenes[i].start); play(); return; }
    save(); renderStep(); return;
  }
  switch (t.id) {
    case "btnPrev": if (step > 0) { step--; renderStep(); window.scrollTo({ top: 0, behavior: "smooth" }); } break;
    case "btnNext": if (step < STEPS.length - 1) { step++; renderStep(); window.scrollTo({ top: 0, behavior: "smooth" }); } else newProject(); break;
    case "voiceTest": speak(P.scenes[0]?.text || "Olá! Esta é a minha voz."); break;
    case "musTest": previewMusic(P.music); break;
    case "recBtn": recordVoice(); break;
    case "photoDel": P.presenter.photo = ""; loadPhoto(); save(); renderStep(); break;
    case "addScene": P.scenes.push({ id: uid(), emoji: "✨", title: "Nova cena", text: "", visual: "" }); save(); renderStep(); break;
    case "aiBtn": {
      const topic = ($("#topic").value || "").trim();
      if (!topic) { toast("Escreva o tema do vídeo primeiro."); $("#topic").focus(); return; }
      if (!ENV.sample && !settings.groqKey && ENV.hostAI) { toast("Use o gerador de roteiro com IA no topo da página, acima do estúdio.", 5000); return; }
      P.topic = topic; aiBusy = true; renderStep();
      try { const sc = await generateScript(topic); P.scenes = sc; Object.keys(runtime.clipVideos).forEach(k => delete runtime.clipVideos[k]); if (!P.name || P.name === "Novo vídeo") P.name = topic.slice(0, 60); save(); toast("Roteiro pronto! Edite o que quiser."); }
      catch (err) { toast(err.message || "Não consegui gerar o roteiro.", 5000); }
      aiBusy = false; renderStep(); break;
    }
    case "aiStop": aiCtl && aiCtl.abort(); break;
    case "expBtn": exportVideo(); break;
    case "btnFinish":
      if (exporting) break;
      if (runtime.exportUrl) { downloadExport(); break; }
      step = 7; renderStep(); $("#stepArea").scrollIntoView({ behavior: "smooth", block: "start" });
      exportVideo(); break;
    case "expStop": stopExport(); break;
    case "dlBtn": downloadExport(); break;
    case "clipBtn": generateClips(); break;
    case "clipClear": Object.keys(runtime.clipVideos).forEach(k => delete runtime.clipVideos[k]); P.scenes.forEach(s => delete s.clipUrl); Object.keys(clipJobs).forEach(k => delete clipJobs[k]); save(); renderStep(); break;
    case "btnSettings": openSettings(); break;
    case "btnProjects": openProjects(); break;
  }
});
document.addEventListener("input", e => {
  const t = e.target;
  if (t.dataset.f) { const card = t.closest(".scene"); const s = P.scenes.find(s => s.id === card.dataset.sid); if (s) { s[t.dataset.f] = t.value; save(); if (!player.playing) { buildTimeline(); renderFrame(player.t); } const meta = card.querySelector(".meta"); const i = P.scenes.indexOf(s); if (meta && TL.scenes[i]) meta.textContent = `Cena ${i + 1} · ${TL.scenes[i].dur.toFixed(1)} s · ${words(s.text)} palavras`; } return; }
  if (t.id === "pname") { P.name = t.value; $("#projName").textContent = "· " + (P.name || "Sem nome"); save(); }
  if (t.id === "brand") { P.brand = t.value; save(); if (!player.playing) renderFrame(player.t); }
  if (t.id === "topic") { P.topic = t.value; save(); }
  if (t.id === "rate") { P.voice.rate = +t.value; save(); const l = t.closest("label"); if (l) l.firstChild.textContent = `Velocidade: ${(+t.value).toFixed(1)}×`; }
});
document.addEventListener("change", async e => {
  const t = e.target;
  if (t.id === "voiceSel") { P.voice.voiceName = t.value; save(); }
  if (t.id === "usePhoto") { clipUsePhoto = t.checked; }
  if (t.id === "photoIn" && t.files[0]) { try { P.presenter.photo = await fileToSmallDataURL(t.files[0]); loadPhoto(); save(); renderStep(); } catch (err) { toast("Não consegui abrir essa imagem."); } }
  if (t.id === "audIn" && t.files[0]) { setNarration(t.files[0], t.files[0].name); P.voice.mode = "upload"; save(); toast("Áudio carregado."); }
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeLayer();
  if (e.key === "Enter" && e.target.id === "topic") { e.preventDefault(); $("#aiBtn")?.click(); }
});

/* ============ gaveta de projetos e configurações ============ */
function closeLayer() { $("#layer").innerHTML = ""; }
function newProject() {
  pause();
  const np = sampleProject(); np.name = "Novo vídeo"; np.topic = ""; np.scenes = [{ id: uid(), emoji: "🎬", title: "Seu título aqui", text: "Escreva o que a narração vai falar nesta cena.", visual: "" }];
  projects.unshift(np); P = np; step = 0; player.t = 0; loadPhoto(); save(); closeLayer(); renderStep();
}
let pendingDelete = null;
function openProjects() {
  const L = $("#layer");
  L.innerHTML = `<div class="scrim" id="scrim"><div class="sheet" role="dialog" aria-label="Meus vídeos">
    <div style="display:flex;justify-content:space-between;align-items:center"><h2>Meus vídeos</h2><button class="btn sm ghost" id="closeL">Fechar</button></div>
    <button class="btn primary" id="newP">+ Criar novo vídeo</button>
    ${projects.map(p => `<div class="proj${p.id === P.id ? " cur" : ""}"><div class="pm"><b>${esc(p.name || "Sem nome")}</b><span>${p.format} · ${p.duration} s · ${STYLES[p.style]?.name || ""} · ${new Date(p.updated).toLocaleDateString("pt-BR")}</span></div>
      ${pendingDelete === p.id ? `<button class="btn sm" data-pdel2="${p.id}" style="border-color:#ff8a7a;color:#ff8a7a">Apagar mesmo</button><button class="btn sm ghost" data-pcancel="1">Não</button>` :
        `<button class="btn sm" data-popen="${p.id}">Abrir</button><button class="btn sm ghost" data-pdup="${p.id}" title="Duplicar">⧉</button><button class="btn sm ghost" data-pdel="${p.id}" title="Apagar">✕</button>`}</div>`).join("")}
    <p class="mon-note">Os projetos ficam salvos neste navegador.</p>
  </div></div>`;
  $("#scrim").onclick = ev => {
    if (ev.target.id === "scrim" || ev.target.id === "closeL") return closeLayer();
    const b = ev.target.closest("button"); if (!b) return; const d = b.dataset;
    if (b.id === "newP") return newProject();
    if (d.popen) { pause(); P = projects.find(p => p.id === d.popen); player.t = 0; Object.keys(runtime.clipVideos).forEach(k => delete runtime.clipVideos[k]); P.scenes.forEach(s => s.clipUrl && loadClip(s.id, s.clipUrl)); loadPhoto(); save(); closeLayer(); renderStep(); return; }
    if (d.pdup) { const src = projects.find(p => p.id === d.pdup); const c = JSON.parse(JSON.stringify(src)); c.id = uid(); c.name = src.name + " (cópia)"; c.scenes.forEach(s => s.id = uid()); projects.unshift(c); save(); openProjects(); return; }
    if (d.pdel) { pendingDelete = d.pdel; openProjects(); return; }
    if (d.pcancel) { pendingDelete = null; openProjects(); return; }
    if (d.pdel2) { projects = projects.filter(p => p.id !== d.pdel2); pendingDelete = null; if (!projects.length) projects = [sampleProject()]; if (!projects.find(p => p.id === P.id)) { P = projects[0]; loadPhoto(); renderStep(); } save(); openProjects(); }
  };
}
function openSettings() {
  const L = $("#layer");
  L.innerHTML = `<div class="scrim" id="scrim"><form class="sheet" id="setForm" role="dialog" aria-label="Chaves de IA">
    <div style="display:flex;justify-content:space-between;align-items:center"><h2>Chaves de IA</h2><button type="button" class="btn sm ghost" id="closeL">Fechar</button></div>
    ${ENV.viewer ? hint("Você está na <b>página publicada</b>. Aqui o roteiro é escrito pela IA do Claude e as chaves abaixo não funcionam, porque a página não pode acessar outros sites. Use as chaves na <b>versão para computador</b> (arquivo .html que te mandei no chat).", "warn") : ""}
    ${ENV.hostAI ? hint("Neste app, a chave da Groq vai no campo <b>Sua chave da Groq</b>, no topo da página. Aqui você só precisa preencher a chave da xAI, se quiser clipes de IA.") : ""}
    <h3 style="margin:8px 0 0;font-family:var(--display)">Groq · roteiros</h3>
    <label class="f" for="gk">Chave da Groq (começa com gsk_)<input id="gk" type="password" autocomplete="off" value="${esc(settings.groqKey)}" placeholder="gsk_..."></label>
    <label class="f" for="gm">Modelo<input id="gm" type="text" value="${esc(settings.groqModel)}"></label>
    <span class="mon-note">Crie a chave em console.groq.com → API Keys. Modelos atuais: openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b.</span>
    <h3 style="margin:14px 0 0;font-family:var(--display)">xAI · clipes animados (Grok Imagine)</h3>
    <label class="f" for="xk">Chave da xAI (começa com xai-)<input id="xk" type="password" autocomplete="off" value="${esc(settings.xaiKey)}" placeholder="xai-..."></label>
    <label class="f" for="xm">Modelo<input id="xm" type="text" value="${esc(settings.xaiModel)}"></label>
    <label class="f" for="xr">Resolução<select id="xr"><option ${settings.xaiRes === "480p" ? "selected" : ""}>480p</option><option ${settings.xaiRes === "720p" ? "selected" : ""}>720p</option></select></label>
    <span class="mon-note">Crie a chave em console.x.ai. Custa cerca de US$ 0,05 por segundo (480p) ou US$ 0,07 (720p).</span>
    <div style="display:flex;gap:8px;margin-top:8px"><button class="btn primary" type="submit">Salvar</button><button class="btn ghost" type="button" id="clrKeys">Apagar chaves</button></div>
    <p class="mon-note">As chaves ficam salvas só neste navegador, neste computador. Nunca compartilhe suas chaves.</p>
  </form></div>`;
  $("#scrim").onclick = ev => { if (ev.target.id === "scrim" || ev.target.id === "closeL") closeLayer(); if (ev.target.id === "clrKeys") { settings.groqKey = ""; settings.xaiKey = ""; saveSettings(); updateEnvBadge(); closeLayer(); renderStep(); toast("Chaves apagadas."); } };
  $("#setForm").onsubmit = ev => {
    ev.preventDefault();
    settings.groqKey = $("#gk").value.trim(); settings.groqModel = $("#gm").value.trim() || "openai/gpt-oss-120b";
    settings.xaiKey = $("#xk").value.trim(); settings.xaiModel = $("#xm").value.trim() || "grok-imagine-video"; settings.xaiRes = $("#xr").value;
    saveSettings(); updateEnvBadge(); closeLayer(); renderStep(); toast("Chaves salvas.");
  };
}

/* ============ início ============ */
// roteiro entregue pelo servidor (ex.: app no Streamlit, que guarda a chave da Groq em segredo)
const INJ = window.__EVS_INJECT__;
if (INJ && INJ.engine) ENV.hostAI = INJ.engine;
if (INJ && INJ.xaiKey) settings.xaiKey = INJ.xaiKey; // chave da sessão, digitada na tela de entrada
if (INJ && Array.isArray(INJ.scenes) && INJ.scenes.length && INJ.nonce && store.get("evs.injected", "") !== INJ.nonce) {
  try {
    const np = sampleProject();
    np.name = String(INJ.topic || "Novo vídeo").slice(0, 60); np.topic = INJ.topic || "";
    if (INJ.purpose) { np.purpose = INJ.purpose; const pp = PURPOSES.find(p => p.id === INJ.purpose); if (pp) { np.style = pp.style; np.music = pp.music; } }
    if (INJ.duration) np.duration = INJ.duration;
    if (INJ.format) np.format = INJ.format;
    if (INJ.lang) np.voice.lang = INJ.lang;
    np.scenes = normalizeScenes(INJ.scenes);
    projects.unshift(np); P = np; step = 5;
    store.set("evs.injected", INJ.nonce); store.set("evs.projects", projects); store.set("evs.current", P.id);
  } catch (e) {}
}
loadPhoto();
P.scenes.forEach(s => s.clipUrl && loadClip(s.id, s.clipUrl));
updateEnvBadge();
renderStep();
const fontsToLoad = ['800 40px "Bricolage Grotesque"', '600 40px "Figtree"', '700 40px "Chakra Petch"', '40px "Gochi Hand"', 'italic 600 40px "Fraunces"', '40px "Bebas Neue"', '800 40px "Baloo 2"', '700 40px "Baloo 2"', '800 40px "Manrope"', '600 40px "Manrope"'];
if (document.fonts) Promise.all(fontsToLoad.map(f => document.fonts.load(f).catch(() => {}))).then(() => { if (!player.playing) renderFrame(player.t); });
// anima a prévia em silêncio até a pessoa tocar
let idleT = 0, idleLast = performance.now();
(function idle(ts) {
  if (!player.playing && !exporting && !scrubbing && document.visibilityState === "visible") {
    const dt = (ts - idleLast) / 1000; idleLast = ts;
    if (player.t > 0.01) { idleLast = ts; } else { idleT = (idleT + Math.min(dt, 0.1)) % TL.total; renderFrame(idleT); $("#timeLbl").textContent = "0:00 / " + fmtT(TL.total); $("#scrub").value = 0; }
  } else idleLast = ts;
  requestAnimationFrame(idle);
})(performance.now());

if (window.claude && typeof window.claude.use === "function") {
  window.claude.use("sample").then(s => { ENV.sample = s || null; updateEnvBadge(); if (step === 5) renderStep(); }).catch(() => {});
  window.claude.use("downloads").then(d => { ENV.downloads = d || null; }).catch(() => {});
}
})();
</script>
'''

st.set_page_config(page_title="Estúdio de Vídeos", page_icon="🎬", layout="wide")
st.markdown("""<style>
.stApp{background:#100e17;color:#efeaf7}
header[data-testid="stHeader"]{background:transparent}
.stApp h1,.stApp h2,.stApp h3,.stApp p,.stApp label,.stApp li,[data-testid="stWidgetLabel"] p,[data-testid="stCaptionContainer"]{color:#efeaf7!important}
[data-testid="stCaptionContainer"]{opacity:.7}
[data-testid="stForm"]{background:#1a1724;border:1px solid #332d45;border-radius:16px}
[data-baseweb="input"],[data-baseweb="input"]>div,[data-baseweb="base-input"],.stApp input,[data-baseweb="select"]>div,[data-baseweb="select"]>div>div{background-color:#100e17!important;border-color:#332d45!important}
.stApp input::placeholder{color:#7d7592!important;-webkit-text-fill-color:#7d7592!important;opacity:1}
.stApp input{color:#efeaf7!important;-webkit-text-fill-color:#efeaf7}
[data-baseweb="select"] div{color:#efeaf7;background-color:#100e17!important}
[data-baseweb="select"] svg{fill:#a69fba}
[data-baseweb="input"] button svg{fill:#a69fba}
.stApp button[kind^="primary"]{background:#ff5a36;border-color:#ff5a36;color:#1a0b06;font-weight:700}
.stApp button[kind^="primary"]:hover{background:#ff7352;border-color:#ff7352;color:#1a0b06}
.stApp button[kind^="secondary"]{background:#1a1724;border-color:#332d45;color:#efeaf7}
</style>""", unsafe_allow_html=True)


PURPOSES = {
    "Anúncio / Vendas": "anuncio", "Aula / Tutorial": "aula", "Reels e Stories": "reels",
    "Receita": "receita", "Parabéns / Convite": "convite", "Empresa": "empresa",
    "História animada": "historia", "Imóvel / Obra": "imovel",
}
FORMATS = {"Vertical 9:16": "9:16", "Horizontal 16:9": "16:9", "Quadrado 1:1": "1:1"}
LANGS = {"Português": "pt-BR", "Inglês": "en-US", "Espanhol": "es-ES"}


GROQ_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]


def build_prompt(topic, purpose_name, duration, fmt, lang_name):
    n = max(3, min(10, round(duration / 7)))
    return f"""Você é roteirista de vídeos curtos para redes sociais.
Crie o roteiro de um vídeo animado.
Finalidade: {purpose_name}
Tema / pedido do cliente: {topic}
Duração total: {duration} segundos, em {n} cenas.
Formato: {fmt}.
Idioma da narração e dos títulos: {lang_name}.

Regras:
- "title": texto curto que aparece grande na tela (máx. 6 palavras).
- "text": a narração falada da cena. No total, cerca de {round(duration * 2.4)} palavras somando todas as cenas. Linguagem natural, como uma pessoa falando.
- "emoji": um único emoji que ilustra a cena.
- "visual": descrição EM INGLÊS de uma cena animada para um gerador de vídeo por IA (personagens, ambiente, câmera). Uma frase.
- A primeira cena prende a atenção. A última cena tem uma chamada para ação adequada à finalidade.

Responda somente com JSON neste formato:
{{"scenes":[{{"title":"...","text":"...","emoji":"🙂","visual":"..."}}]}}"""


def groq_call(prompt, key, model):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "estudio-de-videos"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError("A Groq recusou essa chave. Confira se copiou a chave inteira (começa com gsk_).")
        if e.code == 429:
            raise RuntimeError("A sua chave da Groq atingiu o limite de uso. Espere um pouco e tente de novo.")
        try:
            msg = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        raise RuntimeError(f"Groq ({e.code}): {msg or e.reason}", e.code)
    except urllib.error.URLError as e:
        raise RuntimeError(f"Não consegui conectar à Groq: {e.reason}")
    content = data["choices"][0]["message"]["content"]
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        raise RuntimeError("A Groq não devolveu o roteiro no formato esperado. Tente de novo.")
    parsed = json.loads(m.group(0))
    scenes = parsed.get("scenes") if isinstance(parsed, dict) else parsed
    if not scenes:
        raise RuntimeError("O roteiro veio vazio. Tente descrever melhor o tema.")
    return scenes


def groq_script(prompt, key):
    last = None
    for model in GROQ_MODELS:
        try:
            return groq_call(prompt, key, model)
        except RuntimeError as e:
            last = e
            # tenta o próximo modelo só quando o problema é o modelo
            if not (len(e.args) > 1 and e.args[1] in (400, 404) and "model" in str(e).lower()):
                raise
    raise last


def groq_check(key):
    """Confere a chave na Groq. Devolve None se estiver ok, ou a mensagem de erro."""
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {key}", "User-Agent": "estudio-de-videos"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20):
            return None
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return "A Groq recusou essa chave. Confira se copiou a chave inteira."
        return None  # outros erros não impedem a entrada
    except urllib.error.URLError:
        return None  # sem conexão agora: deixa entrar, o erro aparece ao gerar o roteiro


# ---------- tela de entrada ----------
def tela_entrada():
    st.markdown(
        "<div style='text-align:center;margin-top:6vh'>"
        "<div style='font-size:46px'>🎬</div>"
        "<h1 style='margin:6px 0 4px'>Estúdio de Vídeos</h1>"
        "<p style='opacity:.75;margin:0'>Crie vídeos animados com roteiro feito por IA.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    _, meio, _ = st.columns([1, 1.3, 1])
    with meio:
        with st.form("entrar"):
            nome = st.text_input("Seu nome", placeholder="Como você quer ser chamado")
            chave = st.text_input(
                "Sua chave da Groq",
                type="password",
                placeholder="gsk_...",
                help="Crie grátis em console.groq.com → API Keys.",
            )
            xai = st.text_input(
                "Chave da xAI (opcional)",
                type="password",
                placeholder="xai-...",
                help="Só para gerar clipes animados por IA (Grok Imagine). É paga por uso: console.x.ai.",
            )
            entrar = st.form_submit_button("Entrar no app", type="primary", use_container_width=True)
        st.caption("🔒 Suas chaves valem só nesta sessão. Elas não ficam salvas no servidor e ninguém mais vê.")
        st.caption("Não tem chave? Entre em console.groq.com, faça login e clique em **API Keys → Create API Key**.")

    if entrar:
        nome, chave, xai = nome.strip(), chave.strip(), xai.strip()
        if not nome:
            st.error("Digite o seu nome.")
        elif not chave.startswith("gsk_"):
            st.error("Cole a sua chave da Groq. Ela começa com gsk_.")
        elif xai and not xai.startswith("xai-"):
            st.error("A chave da xAI começa com xai-. Deixe em branco se não tiver.")
        else:
            with st.spinner("Conferindo a sua chave…"):
                erro = groq_check(chave)
            if erro:
                st.error(erro)
            else:
                st.session_state.update(user=nome, groq_key=chave, xai_key=xai)
                st.rerun()


if "user" not in st.session_state:
    tela_entrada()
    st.stop()


# ---------- topo: gerador de roteiro ----------
ca, cb = st.columns([5, 1])
ca.markdown(
    f"<h2 style='margin-bottom:0'>🎬 Olá, {html.escape(st.session_state['user'])}!</h2>"
    "<p style='opacity:.75;margin-top:4px'>Descreva o vídeo, a IA escreve o roteiro e o estúdio anima. "
    "Depois é só ajustar e clicar em <b>Gerar meu vídeo</b>.</p>",
    unsafe_allow_html=True,
)
if cb.button("Sair", use_container_width=True):
    for k in ("user", "groq_key", "xai_key", "inject"):
        st.session_state.pop(k, None)
    st.rerun()

with st.form("roteiro"):
    topic = st.text_input("Tema do vídeo", placeholder="Ex.: Promoção de pizza de sexta, 2 por R$ 79")
    c1, c2, c3, c4 = st.columns(4)
    purpose_name = c1.selectbox("Finalidade", list(PURPOSES))
    fmt_name = c2.selectbox("Formato", list(FORMATS))
    duration = c3.selectbox("Duração", [15, 30, 60, 90], index=1, format_func=lambda d: f"{d} segundos")
    lang_name = c4.selectbox("Idioma", list(LANGS))
    sent = st.form_submit_button("✨ Gerar roteiro com IA", type="primary")

if sent:
    if not topic.strip():
        st.error("Escreva o tema do vídeo.")
    else:
        with st.spinner("Escrevendo o roteiro…"):
            try:
                scenes = groq_script(
                    build_prompt(topic.strip(), purpose_name, duration, FORMATS[fmt_name], lang_name),
                    st.session_state["groq_key"],
                )
                st.session_state["inject"] = {
                    "nonce": f"{time.time():.3f}",
                    "topic": topic.strip(),
                    "purpose": PURPOSES[purpose_name],
                    "duration": duration,
                    "format": FORMATS[fmt_name],
                    "lang": LANGS[lang_name],
                    "scenes": scenes,
                }
                st.success(f"Roteiro pronto com {len(scenes)} cenas. Ele já abriu no estúdio abaixo, no passo Roteiro.")
            except Exception as e:  # noqa: BLE001
                st.error(str(e))

# ---------- estúdio ----------
inject = dict(st.session_state.get("inject") or {})
inject["engine"] = "Groq"
inject["userName"] = st.session_state["user"]
if st.session_state.get("xai_key"):
    inject["xaiKey"] = st.session_state["xai_key"]
script = "<script>window.__EVS_INJECT__ = " + json.dumps(inject, ensure_ascii=False).replace("</", "<\\/") + ";</script>"
page = (
    "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<style>body{margin:0}[hidden]{display:none!important}</style></head><body>"
    + script + HTML + "</body></html>"
)
if hasattr(st, "iframe"):
    st.iframe(page, height=1450)
else:  # versões antigas do Streamlit
    components.html(page, height=1450, scrolling=True)

st.caption("Dica: a exportação grava o vídeo em tempo real. Deixe esta aba aberta até terminar.")
