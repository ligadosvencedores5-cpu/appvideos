"""Estúdio de Vídeos — app para o Streamlit Community Cloud.

Cada pessoa usa a PRÓPRIA chave da Groq: ela é digitada no app, vale só para a sessão
daquela pessoa e não é gravada no servidor. O Python escreve o roteiro com a Groq e
entrega as cenas para o estúdio animado. Os projetos ficam salvos no navegador de cada um.
Arquivo único: não precisa de requirements.txt (só usa o Streamlit e a biblioteca padrão).
"""
import base64
import html
import json
import os
import re
import time
from datetime import datetime, timedelta

import urllib.error
import urllib.request
import streamlit as st
import streamlit.components.v1 as components

try:  # componente que conversa nos dois sentidos (Streamlit 1.5x+)
    from streamlit.components import v2 as components_v2
except Exception:  # noqa: BLE001
    components_v2 = None

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
a.btn{text-decoration:none;color:var(--fg)}
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
.opt.on b{padding-right:22px}
.opt:disabled{opacity:.4;cursor:not-allowed;transform:none}
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
    <button class="btn sm" id="btnKit">🎨 Minha marca</button>
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
    <button class="btn primary" id="btnFinish" style="width:100%;padding:12px 10px;font-size:14.5px;white-space:normal">🎬 Finalizar vídeo</button>
    <div id="proConfirm" hidden></div>
    <div class="mon-note" id="monNote"></div>
  </aside>
</main>

<div id="layer"></div>

<script>/*! qrcode-generator 1.4.4 · MIT License · (c) Kazuhiko Arase */
var qrcode=function(){var t=function(t,r){var e=t,n=g[r],o=null,i=0,a=null,u=[],f={},c=function(t,r){o=function(t){for(var r=new Array(t),e=0;e<t;e+=1){r[e]=new Array(t);for(var n=0;n<t;n+=1)r[e][n]=null}return r}(i=4*e+17),l(0,0),l(i-7,0),l(0,i-7),s(),h(),d(t,r),e>=7&&v(t),null==a&&(a=p(e,n,u)),w(a,r)},l=function(t,r){for(var e=-1;e<=7;e+=1)if(!(t+e<=-1||i<=t+e))for(var n=-1;n<=7;n+=1)r+n<=-1||i<=r+n||(o[t+e][r+n]=0<=e&&e<=6&&(0==n||6==n)||0<=n&&n<=6&&(0==e||6==e)||2<=e&&e<=4&&2<=n&&n<=4)},h=function(){for(var t=8;t<i-8;t+=1)null==o[t][6]&&(o[t][6]=t%2==0);for(var r=8;r<i-8;r+=1)null==o[6][r]&&(o[6][r]=r%2==0)},s=function(){for(var t=B.getPatternPosition(e),r=0;r<t.length;r+=1)for(var n=0;n<t.length;n+=1){var i=t[r],a=t[n];if(null==o[i][a])for(var u=-2;u<=2;u+=1)for(var f=-2;f<=2;f+=1)o[i+u][a+f]=-2==u||2==u||-2==f||2==f||0==u&&0==f}},v=function(t){for(var r=B.getBCHTypeNumber(e),n=0;n<18;n+=1){var a=!t&&1==(r>>n&1);o[Math.floor(n/3)][n%3+i-8-3]=a}for(n=0;n<18;n+=1){a=!t&&1==(r>>n&1);o[n%3+i-8-3][Math.floor(n/3)]=a}},d=function(t,r){for(var e=n<<3|r,a=B.getBCHTypeInfo(e),u=0;u<15;u+=1){var f=!t&&1==(a>>u&1);u<6?o[u][8]=f:u<8?o[u+1][8]=f:o[i-15+u][8]=f}for(u=0;u<15;u+=1){f=!t&&1==(a>>u&1);u<8?o[8][i-u-1]=f:u<9?o[8][15-u-1+1]=f:o[8][15-u-1]=f}o[i-8][8]=!t},w=function(t,r){for(var e=-1,n=i-1,a=7,u=0,f=B.getMaskFunction(r),c=i-1;c>0;c-=2)for(6==c&&(c-=1);;){for(var g=0;g<2;g+=1)if(null==o[n][c-g]){var l=!1;u<t.length&&(l=1==(t[u]>>>a&1)),f(n,c-g)&&(l=!l),o[n][c-g]=l,-1==(a-=1)&&(u+=1,a=7)}if((n+=e)<0||i<=n){n-=e,e=-e;break}}},p=function(t,r,e){for(var n=A.getRSBlocks(t,r),o=b(),i=0;i<e.length;i+=1){var a=e[i];o.put(a.getMode(),4),o.put(a.getLength(),B.getLengthInBits(a.getMode(),t)),a.write(o)}var u=0;for(i=0;i<n.length;i+=1)u+=n[i].dataCount;if(o.getLengthInBits()>8*u)throw"code length overflow. ("+o.getLengthInBits()+">"+8*u+")";for(o.getLengthInBits()+4<=8*u&&o.put(0,4);o.getLengthInBits()%8!=0;)o.putBit(!1);for(;!(o.getLengthInBits()>=8*u||(o.put(236,8),o.getLengthInBits()>=8*u));)o.put(17,8);return function(t,r){for(var e=0,n=0,o=0,i=new Array(r.length),a=new Array(r.length),u=0;u<r.length;u+=1){var f=r[u].dataCount,c=r[u].totalCount-f;n=Math.max(n,f),o=Math.max(o,c),i[u]=new Array(f);for(var g=0;g<i[u].length;g+=1)i[u][g]=255&t.getBuffer()[g+e];e+=f;var l=B.getErrorCorrectPolynomial(c),h=k(i[u],l.getLength()-1).mod(l);for(a[u]=new Array(l.getLength()-1),g=0;g<a[u].length;g+=1){var s=g+h.getLength()-a[u].length;a[u][g]=s>=0?h.getAt(s):0}}var v=0;for(g=0;g<r.length;g+=1)v+=r[g].totalCount;var d=new Array(v),w=0;for(g=0;g<n;g+=1)for(u=0;u<r.length;u+=1)g<i[u].length&&(d[w]=i[u][g],w+=1);for(g=0;g<o;g+=1)for(u=0;u<r.length;u+=1)g<a[u].length&&(d[w]=a[u][g],w+=1);return d}(o,n)};f.addData=function(t,r){var e=null;switch(r=r||"Byte"){case"Numeric":e=M(t);break;case"Alphanumeric":e=x(t);break;case"Byte":e=m(t);break;case"Kanji":e=L(t);break;default:throw"mode:"+r}u.push(e),a=null},f.isDark=function(t,r){if(t<0||i<=t||r<0||i<=r)throw t+","+r;return o[t][r]},f.getModuleCount=function(){return i},f.make=function(){if(e<1){for(var t=1;t<40;t++){for(var r=A.getRSBlocks(t,n),o=b(),i=0;i<u.length;i++){var a=u[i];o.put(a.getMode(),4),o.put(a.getLength(),B.getLengthInBits(a.getMode(),t)),a.write(o)}var g=0;for(i=0;i<r.length;i++)g+=r[i].dataCount;if(o.getLengthInBits()<=8*g)break}e=t}c(!1,function(){for(var t=0,r=0,e=0;e<8;e+=1){c(!0,e);var n=B.getLostPoint(f);(0==e||t>n)&&(t=n,r=e)}return r}())},f.createTableTag=function(t,r){t=t||2;var e="";e+='<table style="',e+=" border-width: 0px; border-style: none;",e+=" border-collapse: collapse;",e+=" padding: 0px; margin: "+(r=void 0===r?4*t:r)+"px;",e+='">',e+="<tbody>";for(var n=0;n<f.getModuleCount();n+=1){e+="<tr>";for(var o=0;o<f.getModuleCount();o+=1)e+='<td style="',e+=" border-width: 0px; border-style: none;",e+=" border-collapse: collapse;",e+=" padding: 0px; margin: 0px;",e+=" width: "+t+"px;",e+=" height: "+t+"px;",e+=" background-color: ",e+=f.isDark(n,o)?"#000000":"#ffffff",e+=";",e+='"/>';e+="</tr>"}return e+="</tbody>",e+="</table>"},f.createSvgTag=function(t,r,e,n){var o={};"object"==typeof arguments[0]&&(t=(o=arguments[0]).cellSize,r=o.margin,e=o.alt,n=o.title),t=t||2,r=void 0===r?4*t:r,(e="string"==typeof e?{text:e}:e||{}).text=e.text||null,e.id=e.text?e.id||"qrcode-description":null,(n="string"==typeof n?{text:n}:n||{}).text=n.text||null,n.id=n.text?n.id||"qrcode-title":null;var i,a,u,c,g=f.getModuleCount()*t+2*r,l="";for(c="l"+t+",0 0,"+t+" -"+t+",0 0,-"+t+"z ",l+='<svg version="1.1" xmlns="http://www.w3.org/2000/svg"',l+=o.scalable?"":' width="'+g+'px" height="'+g+'px"',l+=' viewBox="0 0 '+g+" "+g+'" ',l+=' preserveAspectRatio="xMinYMin meet"',l+=n.text||e.text?' role="img" aria-labelledby="'+y([n.id,e.id].join(" ").trim())+'"':"",l+=">",l+=n.text?'<title id="'+y(n.id)+'">'+y(n.text)+"</title>":"",l+=e.text?'<description id="'+y(e.id)+'">'+y(e.text)+"</description>":"",l+='<rect width="100%" height="100%" fill="white" cx="0" cy="0"/>',l+='<path d="',a=0;a<f.getModuleCount();a+=1)for(u=a*t+r,i=0;i<f.getModuleCount();i+=1)f.isDark(a,i)&&(l+="M"+(i*t+r)+","+u+c);return l+='" stroke="transparent" fill="black"/>',l+="</svg>"},f.createDataURL=function(t,r){t=t||2,r=void 0===r?4*t:r;var e=f.getModuleCount()*t+2*r,n=r,o=e-r;return I(e,e,(function(r,e){if(n<=r&&r<o&&n<=e&&e<o){var i=Math.floor((r-n)/t),a=Math.floor((e-n)/t);return f.isDark(a,i)?0:1}return 1}))},f.createImgTag=function(t,r,e){t=t||2,r=void 0===r?4*t:r;var n=f.getModuleCount()*t+2*r,o="";return o+="<img",o+=' src="',o+=f.createDataURL(t,r),o+='"',o+=' width="',o+=n,o+='"',o+=' height="',o+=n,o+='"',e&&(o+=' alt="',o+=y(e),o+='"'),o+="/>"};var y=function(t){for(var r="",e=0;e<t.length;e+=1){var n=t.charAt(e);switch(n){case"<":r+="&lt;";break;case">":r+="&gt;";break;case"&":r+="&amp;";break;case'"':r+="&quot;";break;default:r+=n}}return r};return f.createASCII=function(t,r){if((t=t||1)<2)return function(t){t=void 0===t?2:t;var r,e,n,o,i,a=1*f.getModuleCount()+2*t,u=t,c=a-t,g={"██":"█","█ ":"▀"," █":"▄","  ":" "},l={"██":"▀","█ ":"▀"," █":" ","  ":" "},h="";for(r=0;r<a;r+=2){for(n=Math.floor((r-u)/1),o=Math.floor((r+1-u)/1),e=0;e<a;e+=1)i="█",u<=e&&e<c&&u<=r&&r<c&&f.isDark(n,Math.floor((e-u)/1))&&(i=" "),u<=e&&e<c&&u<=r+1&&r+1<c&&f.isDark(o,Math.floor((e-u)/1))?i+=" ":i+="█",h+=t<1&&r+1>=c?l[i]:g[i];h+="\n"}return a%2&&t>0?h.substring(0,h.length-a-1)+Array(a+1).join("▀"):h.substring(0,h.length-1)}(r);t-=1,r=void 0===r?2*t:r;var e,n,o,i,a=f.getModuleCount()*t+2*r,u=r,c=a-r,g=Array(t+1).join("██"),l=Array(t+1).join("  "),h="",s="";for(e=0;e<a;e+=1){for(o=Math.floor((e-u)/t),s="",n=0;n<a;n+=1)i=1,u<=n&&n<c&&u<=e&&e<c&&f.isDark(o,Math.floor((n-u)/t))&&(i=0),s+=i?g:l;for(o=0;o<t;o+=1)h+=s+"\n"}return h.substring(0,h.length-1)},f.renderTo2dContext=function(t,r){r=r||2;for(var e=f.getModuleCount(),n=0;n<e;n++)for(var o=0;o<e;o++)t.fillStyle=f.isDark(n,o)?"black":"white",t.fillRect(n*r,o*r,r,r)},f};t.stringToBytes=(t.stringToBytesFuncs={default:function(t){for(var r=[],e=0;e<t.length;e+=1){var n=t.charCodeAt(e);r.push(255&n)}return r}}).default,t.createStringToBytes=function(t,r){var e=function(){for(var e=S(t),n=function(){var t=e.read();if(-1==t)throw"eof";return t},o=0,i={};;){var a=e.read();if(-1==a)break;var u=n(),f=n()<<8|n();i[String.fromCharCode(a<<8|u)]=f,o+=1}if(o!=r)throw o+" != "+r;return i}(),n="?".charCodeAt(0);return function(t){for(var r=[],o=0;o<t.length;o+=1){var i=t.charCodeAt(o);if(i<128)r.push(i);else{var a=e[t.charAt(o)];"number"==typeof a?(255&a)==a?r.push(a):(r.push(a>>>8),r.push(255&a)):r.push(n)}}return r}};var r,e,n,o,i,a=1,u=2,f=4,c=8,g={L:1,M:0,Q:3,H:2},l=0,h=1,s=2,v=3,d=4,w=5,p=6,y=7,B=(r=[[],[6,18],[6,22],[6,26],[6,30],[6,34],[6,22,38],[6,24,42],[6,26,46],[6,28,50],[6,30,54],[6,32,58],[6,34,62],[6,26,46,66],[6,26,48,70],[6,26,50,74],[6,30,54,78],[6,30,56,82],[6,30,58,86],[6,34,62,90],[6,28,50,72,94],[6,26,50,74,98],[6,30,54,78,102],[6,28,54,80,106],[6,32,58,84,110],[6,30,58,86,114],[6,34,62,90,118],[6,26,50,74,98,122],[6,30,54,78,102,126],[6,26,52,78,104,130],[6,30,56,82,108,134],[6,34,60,86,112,138],[6,30,58,86,114,142],[6,34,62,90,118,146],[6,30,54,78,102,126,150],[6,24,50,76,102,128,154],[6,28,54,80,106,132,158],[6,32,58,84,110,136,162],[6,26,54,82,110,138,166],[6,30,58,86,114,142,170]],e=1335,n=7973,i=function(t){for(var r=0;0!=t;)r+=1,t>>>=1;return r},(o={}).getBCHTypeInfo=function(t){for(var r=t<<10;i(r)-i(e)>=0;)r^=e<<i(r)-i(e);return 21522^(t<<10|r)},o.getBCHTypeNumber=function(t){for(var r=t<<12;i(r)-i(n)>=0;)r^=n<<i(r)-i(n);return t<<12|r},o.getPatternPosition=function(t){return r[t-1]},o.getMaskFunction=function(t){switch(t){case l:return function(t,r){return(t+r)%2==0};case h:return function(t,r){return t%2==0};case s:return function(t,r){return r%3==0};case v:return function(t,r){return(t+r)%3==0};case d:return function(t,r){return(Math.floor(t/2)+Math.floor(r/3))%2==0};case w:return function(t,r){return t*r%2+t*r%3==0};case p:return function(t,r){return(t*r%2+t*r%3)%2==0};case y:return function(t,r){return(t*r%3+(t+r)%2)%2==0};default:throw"bad maskPattern:"+t}},o.getErrorCorrectPolynomial=function(t){for(var r=k([1],0),e=0;e<t;e+=1)r=r.multiply(k([1,C.gexp(e)],0));return r},o.getLengthInBits=function(t,r){if(1<=r&&r<10)switch(t){case a:return 10;case u:return 9;case f:case c:return 8;default:throw"mode:"+t}else if(r<27)switch(t){case a:return 12;case u:return 11;case f:return 16;case c:return 10;default:throw"mode:"+t}else{if(!(r<41))throw"type:"+r;switch(t){case a:return 14;case u:return 13;case f:return 16;case c:return 12;default:throw"mode:"+t}}},o.getLostPoint=function(t){for(var r=t.getModuleCount(),e=0,n=0;n<r;n+=1)for(var o=0;o<r;o+=1){for(var i=0,a=t.isDark(n,o),u=-1;u<=1;u+=1)if(!(n+u<0||r<=n+u))for(var f=-1;f<=1;f+=1)o+f<0||r<=o+f||0==u&&0==f||a==t.isDark(n+u,o+f)&&(i+=1);i>5&&(e+=3+i-5)}for(n=0;n<r-1;n+=1)for(o=0;o<r-1;o+=1){var c=0;t.isDark(n,o)&&(c+=1),t.isDark(n+1,o)&&(c+=1),t.isDark(n,o+1)&&(c+=1),t.isDark(n+1,o+1)&&(c+=1),0!=c&&4!=c||(e+=3)}for(n=0;n<r;n+=1)for(o=0;o<r-6;o+=1)t.isDark(n,o)&&!t.isDark(n,o+1)&&t.isDark(n,o+2)&&t.isDark(n,o+3)&&t.isDark(n,o+4)&&!t.isDark(n,o+5)&&t.isDark(n,o+6)&&(e+=40);for(o=0;o<r;o+=1)for(n=0;n<r-6;n+=1)t.isDark(n,o)&&!t.isDark(n+1,o)&&t.isDark(n+2,o)&&t.isDark(n+3,o)&&t.isDark(n+4,o)&&!t.isDark(n+5,o)&&t.isDark(n+6,o)&&(e+=40);var g=0;for(o=0;o<r;o+=1)for(n=0;n<r;n+=1)t.isDark(n,o)&&(g+=1);return e+=Math.abs(100*g/r/r-50)/5*10},o),C=function(){for(var t=new Array(256),r=new Array(256),e=0;e<8;e+=1)t[e]=1<<e;for(e=8;e<256;e+=1)t[e]=t[e-4]^t[e-5]^t[e-6]^t[e-8];for(e=0;e<255;e+=1)r[t[e]]=e;var n={glog:function(t){if(t<1)throw"glog("+t+")";return r[t]},gexp:function(r){for(;r<0;)r+=255;for(;r>=256;)r-=255;return t[r]}};return n}();function k(t,r){if(void 0===t.length)throw t.length+"/"+r;var e=function(){for(var e=0;e<t.length&&0==t[e];)e+=1;for(var n=new Array(t.length-e+r),o=0;o<t.length-e;o+=1)n[o]=t[o+e];return n}(),n={getAt:function(t){return e[t]},getLength:function(){return e.length},multiply:function(t){for(var r=new Array(n.getLength()+t.getLength()-1),e=0;e<n.getLength();e+=1)for(var o=0;o<t.getLength();o+=1)r[e+o]^=C.gexp(C.glog(n.getAt(e))+C.glog(t.getAt(o)));return k(r,0)},mod:function(t){if(n.getLength()-t.getLength()<0)return n;for(var r=C.glog(n.getAt(0))-C.glog(t.getAt(0)),e=new Array(n.getLength()),o=0;o<n.getLength();o+=1)e[o]=n.getAt(o);for(o=0;o<t.getLength();o+=1)e[o]^=C.gexp(C.glog(t.getAt(o))+r);return k(e,0).mod(t)}};return n}var A=function(){var t=[[1,26,19],[1,26,16],[1,26,13],[1,26,9],[1,44,34],[1,44,28],[1,44,22],[1,44,16],[1,70,55],[1,70,44],[2,35,17],[2,35,13],[1,100,80],[2,50,32],[2,50,24],[4,25,9],[1,134,108],[2,67,43],[2,33,15,2,34,16],[2,33,11,2,34,12],[2,86,68],[4,43,27],[4,43,19],[4,43,15],[2,98,78],[4,49,31],[2,32,14,4,33,15],[4,39,13,1,40,14],[2,121,97],[2,60,38,2,61,39],[4,40,18,2,41,19],[4,40,14,2,41,15],[2,146,116],[3,58,36,2,59,37],[4,36,16,4,37,17],[4,36,12,4,37,13],[2,86,68,2,87,69],[4,69,43,1,70,44],[6,43,19,2,44,20],[6,43,15,2,44,16],[4,101,81],[1,80,50,4,81,51],[4,50,22,4,51,23],[3,36,12,8,37,13],[2,116,92,2,117,93],[6,58,36,2,59,37],[4,46,20,6,47,21],[7,42,14,4,43,15],[4,133,107],[8,59,37,1,60,38],[8,44,20,4,45,21],[12,33,11,4,34,12],[3,145,115,1,146,116],[4,64,40,5,65,41],[11,36,16,5,37,17],[11,36,12,5,37,13],[5,109,87,1,110,88],[5,65,41,5,66,42],[5,54,24,7,55,25],[11,36,12,7,37,13],[5,122,98,1,123,99],[7,73,45,3,74,46],[15,43,19,2,44,20],[3,45,15,13,46,16],[1,135,107,5,136,108],[10,74,46,1,75,47],[1,50,22,15,51,23],[2,42,14,17,43,15],[5,150,120,1,151,121],[9,69,43,4,70,44],[17,50,22,1,51,23],[2,42,14,19,43,15],[3,141,113,4,142,114],[3,70,44,11,71,45],[17,47,21,4,48,22],[9,39,13,16,40,14],[3,135,107,5,136,108],[3,67,41,13,68,42],[15,54,24,5,55,25],[15,43,15,10,44,16],[4,144,116,4,145,117],[17,68,42],[17,50,22,6,51,23],[19,46,16,6,47,17],[2,139,111,7,140,112],[17,74,46],[7,54,24,16,55,25],[34,37,13],[4,151,121,5,152,122],[4,75,47,14,76,48],[11,54,24,14,55,25],[16,45,15,14,46,16],[6,147,117,4,148,118],[6,73,45,14,74,46],[11,54,24,16,55,25],[30,46,16,2,47,17],[8,132,106,4,133,107],[8,75,47,13,76,48],[7,54,24,22,55,25],[22,45,15,13,46,16],[10,142,114,2,143,115],[19,74,46,4,75,47],[28,50,22,6,51,23],[33,46,16,4,47,17],[8,152,122,4,153,123],[22,73,45,3,74,46],[8,53,23,26,54,24],[12,45,15,28,46,16],[3,147,117,10,148,118],[3,73,45,23,74,46],[4,54,24,31,55,25],[11,45,15,31,46,16],[7,146,116,7,147,117],[21,73,45,7,74,46],[1,53,23,37,54,24],[19,45,15,26,46,16],[5,145,115,10,146,116],[19,75,47,10,76,48],[15,54,24,25,55,25],[23,45,15,25,46,16],[13,145,115,3,146,116],[2,74,46,29,75,47],[42,54,24,1,55,25],[23,45,15,28,46,16],[17,145,115],[10,74,46,23,75,47],[10,54,24,35,55,25],[19,45,15,35,46,16],[17,145,115,1,146,116],[14,74,46,21,75,47],[29,54,24,19,55,25],[11,45,15,46,46,16],[13,145,115,6,146,116],[14,74,46,23,75,47],[44,54,24,7,55,25],[59,46,16,1,47,17],[12,151,121,7,152,122],[12,75,47,26,76,48],[39,54,24,14,55,25],[22,45,15,41,46,16],[6,151,121,14,152,122],[6,75,47,34,76,48],[46,54,24,10,55,25],[2,45,15,64,46,16],[17,152,122,4,153,123],[29,74,46,14,75,47],[49,54,24,10,55,25],[24,45,15,46,46,16],[4,152,122,18,153,123],[13,74,46,32,75,47],[48,54,24,14,55,25],[42,45,15,32,46,16],[20,147,117,4,148,118],[40,75,47,7,76,48],[43,54,24,22,55,25],[10,45,15,67,46,16],[19,148,118,6,149,119],[18,75,47,31,76,48],[34,54,24,34,55,25],[20,45,15,61,46,16]],r=function(t,r){var e={};return e.totalCount=t,e.dataCount=r,e},e={};return e.getRSBlocks=function(e,n){var o=function(r,e){switch(e){case g.L:return t[4*(r-1)+0];case g.M:return t[4*(r-1)+1];case g.Q:return t[4*(r-1)+2];case g.H:return t[4*(r-1)+3];default:return}}(e,n);if(void 0===o)throw"bad rs block @ typeNumber:"+e+"/errorCorrectionLevel:"+n;for(var i=o.length/3,a=[],u=0;u<i;u+=1)for(var f=o[3*u+0],c=o[3*u+1],l=o[3*u+2],h=0;h<f;h+=1)a.push(r(c,l));return a},e}(),b=function(){var t=[],r=0,e={getBuffer:function(){return t},getAt:function(r){var e=Math.floor(r/8);return 1==(t[e]>>>7-r%8&1)},put:function(t,r){for(var n=0;n<r;n+=1)e.putBit(1==(t>>>r-n-1&1))},getLengthInBits:function(){return r},putBit:function(e){var n=Math.floor(r/8);t.length<=n&&t.push(0),e&&(t[n]|=128>>>r%8),r+=1}};return e},M=function(t){var r=a,e=t,n={getMode:function(){return r},getLength:function(t){return e.length},write:function(t){for(var r=e,n=0;n+2<r.length;)t.put(o(r.substring(n,n+3)),10),n+=3;n<r.length&&(r.length-n==1?t.put(o(r.substring(n,n+1)),4):r.length-n==2&&t.put(o(r.substring(n,n+2)),7))}},o=function(t){for(var r=0,e=0;e<t.length;e+=1)r=10*r+i(t.charAt(e));return r},i=function(t){if("0"<=t&&t<="9")return t.charCodeAt(0)-"0".charCodeAt(0);throw"illegal char :"+t};return n},x=function(t){var r=u,e=t,n={getMode:function(){return r},getLength:function(t){return e.length},write:function(t){for(var r=e,n=0;n+1<r.length;)t.put(45*o(r.charAt(n))+o(r.charAt(n+1)),11),n+=2;n<r.length&&t.put(o(r.charAt(n)),6)}},o=function(t){if("0"<=t&&t<="9")return t.charCodeAt(0)-"0".charCodeAt(0);if("A"<=t&&t<="Z")return t.charCodeAt(0)-"A".charCodeAt(0)+10;switch(t){case" ":return 36;case"$":return 37;case"%":return 38;case"*":return 39;case"+":return 40;case"-":return 41;case".":return 42;case"/":return 43;case":":return 44;default:throw"illegal char :"+t}};return n},m=function(r){var e=f,n=t.stringToBytes(r),o={getMode:function(){return e},getLength:function(t){return n.length},write:function(t){for(var r=0;r<n.length;r+=1)t.put(n[r],8)}};return o},L=function(r){var e=c,n=t.stringToBytesFuncs.SJIS;if(!n)throw"sjis not supported.";!function(t,r){var e=n("友");if(2!=e.length||38726!=(e[0]<<8|e[1]))throw"sjis not supported."}();var o=n(r),i={getMode:function(){return e},getLength:function(t){return~~(o.length/2)},write:function(t){for(var r=o,e=0;e+1<r.length;){var n=(255&r[e])<<8|255&r[e+1];if(33088<=n&&n<=40956)n-=33088;else{if(!(57408<=n&&n<=60351))throw"illegal char at "+(e+1)+"/"+n;n-=49472}n=192*(n>>>8&255)+(255&n),t.put(n,13),e+=2}if(e<r.length)throw"illegal char at "+(e+1)}};return i},D=function(){var t=[],r={writeByte:function(r){t.push(255&r)},writeShort:function(t){r.writeByte(t),r.writeByte(t>>>8)},writeBytes:function(t,e,n){e=e||0,n=n||t.length;for(var o=0;o<n;o+=1)r.writeByte(t[o+e])},writeString:function(t){for(var e=0;e<t.length;e+=1)r.writeByte(t.charCodeAt(e))},toByteArray:function(){return t},toString:function(){var r="";r+="[";for(var e=0;e<t.length;e+=1)e>0&&(r+=","),r+=t[e];return r+="]"}};return r},S=function(t){var r=t,e=0,n=0,o=0,i={read:function(){for(;o<8;){if(e>=r.length){if(0==o)return-1;throw"unexpected end of file./"+o}var t=r.charAt(e);if(e+=1,"="==t)return o=0,-1;t.match(/^\s$/)||(n=n<<6|a(t.charCodeAt(0)),o+=6)}var i=n>>>o-8&255;return o-=8,i}},a=function(t){if(65<=t&&t<=90)return t-65;if(97<=t&&t<=122)return t-97+26;if(48<=t&&t<=57)return t-48+52;if(43==t)return 62;if(47==t)return 63;throw"c:"+t};return i},I=function(t,r,e){for(var n=function(t,r){var e=t,n=r,o=new Array(t*r),i={setPixel:function(t,r,n){o[r*e+t]=n},write:function(t){t.writeString("GIF87a"),t.writeShort(e),t.writeShort(n),t.writeByte(128),t.writeByte(0),t.writeByte(0),t.writeByte(0),t.writeByte(0),t.writeByte(0),t.writeByte(255),t.writeByte(255),t.writeByte(255),t.writeString(","),t.writeShort(0),t.writeShort(0),t.writeShort(e),t.writeShort(n),t.writeByte(0);var r=a(2);t.writeByte(2);for(var o=0;r.length-o>255;)t.writeByte(255),t.writeBytes(r,o,255),o+=255;t.writeByte(r.length-o),t.writeBytes(r,o,r.length-o),t.writeByte(0),t.writeString(";")}},a=function(t){for(var r=1<<t,e=1+(1<<t),n=t+1,i=u(),a=0;a<r;a+=1)i.add(String.fromCharCode(a));i.add(String.fromCharCode(r)),i.add(String.fromCharCode(e));var f,c,g,l=D(),h=(f=l,c=0,g=0,{write:function(t,r){if(t>>>r!=0)throw"length over";for(;c+r>=8;)f.writeByte(255&(t<<c|g)),r-=8-c,t>>>=8-c,g=0,c=0;g|=t<<c,c+=r},flush:function(){c>0&&f.writeByte(g)}});h.write(r,n);var s=0,v=String.fromCharCode(o[s]);for(s+=1;s<o.length;){var d=String.fromCharCode(o[s]);s+=1,i.contains(v+d)?v+=d:(h.write(i.indexOf(v),n),i.size()<4095&&(i.size()==1<<n&&(n+=1),i.add(v+d)),v=d)}return h.write(i.indexOf(v),n),h.write(e,n),h.flush(),l.toByteArray()},u=function(){var t={},r=0,e={add:function(n){if(e.contains(n))throw"dup key:"+n;t[n]=r,r+=1},size:function(){return r},indexOf:function(r){return t[r]},contains:function(r){return void 0!==t[r]}};return e};return i}(t,r),o=0;o<r;o+=1)for(var i=0;i<t;i+=1)n.setPixel(i,o,e(i,o));var a=D();n.write(a);for(var u=function(){var t=0,r=0,e=0,n="",o={},i=function(t){n+=String.fromCharCode(a(63&t))},a=function(t){if(t<0);else{if(t<26)return 65+t;if(t<52)return t-26+97;if(t<62)return t-52+48;if(62==t)return 43;if(63==t)return 47}throw"n:"+t};return o.writeByte=function(n){for(t=t<<8|255&n,r+=8,e+=1;r>=6;)i(t>>>r-6),r-=6},o.flush=function(){if(r>0&&(i(t<<6-r),t=0,r=0),e%3!=0)for(var o=3-e%3,a=0;a<o;a+=1)n+="="},o.toString=function(){return n},o}(),f=a.toByteArray(),c=0;c<f.length;c+=1)u.writeByte(f[c]);return u.flush(),"data:image/gif;base64,"+u};return t}();qrcode.stringToBytesFuncs["UTF-8"]=function(t){return function(t){for(var r=[],e=0;e<t.length;e++){var n=t.charCodeAt(e);n<128?r.push(n):n<2048?r.push(192|n>>6,128|63&n):n<55296||n>=57344?r.push(224|n>>12,128|n>>6&63,128|63&n):(e++,n=65536+((1023&n)<<10|1023&t.charCodeAt(e)),r.push(240|n>>18,128|n>>12&63,128|n>>6&63,128|63&n))}return r}(t)},function(t){"function"==typeof define&&define.amd?define([],t):"object"==typeof exports&&(module.exports=t())}((function(){return qrcode}));
</script>
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
  if (window.__evsPonteOk) { try { window.parent.postMessage({ evs: "toast", msg: String(msg), ms }, "*"); return; } catch (e) {} } // no app do hub, o aviso aparece na tela da página
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
function saveSettings() { const c = Object.assign({}, settings); if (c.xaiKey === "__servidor__") c.xaiKey = ""; store.set("evs.settings", c); }
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
function clearExport() {
  if (exporting || !runtime.exportUrl) return;
  try { URL.revokeObjectURL(runtime.exportUrl); } catch (e) {}
  runtime.exportUrl = ""; runtime.exportBlob = null; runtime.exportExt = "";
  updateFinishBtn();
}
function updateFinishBtn() {
  const fb = document.getElementById("btnFinish"); if (!fb) return;
  fb.disabled = exporting;
  fb.textContent = exporting ? "Gravando o vídeo…" : runtime.exportUrl ? "⬇ Baixar vídeo pronto" : "🎬 Finalizar vídeo";
  const pb = document.getElementById("btnPro");
  if (pb) { pb.disabled = exporting || clipsRunning || proRunning; pb.textContent = proRunning ? (clipsRunning ? "⭐ Gerando cenas com IA…" : "⭐ Finalizando…") : "⭐ Criar vídeo profissional (IA)"; }
}
function save() {
  P.updated = Date.now();
  clearExport();
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
  if (["upload", "record", "xai"].includes(P.voice.mode) && runtime.narrationDur > 1) total = Math.ceil(runtime.narrationDur + 0.6);
  const sc = P.scenes.length ? P.scenes : [{ id: "x", emoji: "🎬", title: "Escreva seu roteiro", text: "", visual: "" }];
  if (P.scenes.length && narracaoIAValida()) {
    let acc0 = 0;
    TL = { total: P.scenes.reduce((a, s) => a + runtime.sceneDurs[s.id], 0), scenes: P.scenes.map((s, i) => { const d = runtime.sceneDurs[s.id]; const o = { s, i, start: acc0, dur: d }; acc0 += d; return o; }) };
    addEndCard(); timelineDirty = false; drawTimelineBar(); return;
  }
  const w = sc.map(s => Math.max(4, words(s.text) + words(s.title) * 0.4));
  const sum = w.reduce((a, b) => a + b, 0);
  let acc = 0;
  TL = { total, scenes: sc.map((s, i) => { const d = total * w[i] / sum; const o = { s, i, start: acc, dur: d }; acc += d; return o; }) };
  addEndCard();
  timelineDirty = false;
  drawTimelineBar();
}
function sceneAt(t) {
  if (TL.end && t >= TL.end.start) return TL.end;
  const arr = TL.scenes;
  for (let i = 0; i < arr.length; i++) if (t < arr[i].start + arr[i].dur) return arr[i];
  return arr[arr.length - 1];
}
function drawTimelineBar() {
  const el = $("#timeline");
  el.innerHTML = allScenes().map(x => `<div style="flex:${x.dur.toFixed(3)}" title="${esc(x.s.title)}"><i></i></div>`).join("");
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
  const bim = bgImgs[TL.scenes[idx]?.s.id];
  if (bim && bim.complete && bim.naturalWidth) {
    const z = 1.04 + lt * 0.02; ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-W / 2, -H / 2);
    cover(bim, bim.naturalWidth, bim.naturalHeight, 0, 0, W, H); ctx.restore();
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
  if (analyser && player.playing && ["upload", "record", "xai"].includes(P.voice.mode) && runtime.narrationUrl) {
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
  drawMarca(st, key, fg, alpha, W, H, m);

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
  if (pr.type !== "none" && !(hasClip && AI().mode === "avatar")) {
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
  drawAny(x, T, W, H, 1);
  const tr = 0.4, next = x.final ? null : (TL.scenes[x.i + 1] || TL.end);
  const rem = x.start + x.dur - T;
  if (next && rem < tr) drawAny(next, T, W, H, 1 - rem / tr);
  // progresso
  const st = STYLES[P.style] || STYLES.vibrante;
  ctx.fillStyle = "rgba(255,255,255,.25)"; ctx.fillRect(0, H - 6, W, 6);
  ctx.fillStyle = KIT.ativo && KIT.cor1 && (KIT.nome || KIT.logo) ? KIT.cor1 : (st.pal[0][0] === "#21392f" ? "#ffd36b" : (P.style === "empresa" ? "#ff5a36" : "#ffffff")); ctx.fillRect(0, H - 6, W * (T / TL.total), 6);
  // linha do tempo da UI
  const bars = $("#timeline").children;
  allScenes().forEach((s, i) => { const b = bars[i]?.firstChild; if (b) b.style.width = (clamp((T - s.start) / s.dur, 0, 1) * 100) + "%"; });
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
    if (inScene) { if (play && AI().audio !== "mudo") { routeClip(v); v.muted = false; } else v.muted = true; const lt = clamp(T - x.start, 0, (v.duration || 99) - 0.05); if (Math.abs(v.currentTime - lt) > 0.3) { try { v.currentTime = lt; } catch (e) {} } if (play && v.paused) v.play().catch(() => {}); if (!play && !v.paused) v.pause(); }
    else if (!v.paused) v.pause();
  });
}
function play(fromStart) {
  audio(); if (AC) AC.resume();
  if (timelineDirty) buildTimeline();
  if (fromStart || player.t >= TL.total - 0.05) player.t = 0;
  player.playing = true; player.startAt = now() - player.t; player.lastScene = -1;
  if (!player.silent) Music.start(player.t);
  if (["upload", "record", "xai"].includes(P.voice.mode) && (P.voice.mode !== "xai" || narracaoIAValida()) && runtime.narrBuf && !player.silent && AC && !(AI().audio === "fala" && Object.keys(runtime.clipVideos).length)) startNarration(player.t);
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
    if (P.voice.mode === "browser" && !player.silent && !(AI().audio !== "mudo" && runtime.clipVideos[x.s.id])) speak(x.s.text);
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
${P.styleDesc ? "Serviço ou produto do cliente (use estas informações reais: o que é, o que faz, para quem, diferenciais, preço e contato; NÃO invente dados que não estão aqui): " + P.styleDesc + "\n" : ""}Duração total: ${P.duration} segundos, em ${n} cenas.
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

/* ============ IA paga: xAI (Grok Imagine) ============ */
// Tudo aqui segue a documentação oficial da xAI (docs.x.ai). O painel só deixa escolher combinações que a API aceita.
// Preços aproximados em US$ (confira os valores atuais em console.x.ai).
const XAI_MODELS = {
  "grok-imagine-video-1.5-lite": { name: "Lite", tag: "mais barato", desc: "Ótimo custo. Fala com boca sincronizada. Até 1080p.", price: { "480p": 0.02, "720p": 0.03, "1080p": 0.14 }, refs: 0, voices: false, frames: false },
  "grok-imagine-video-1.5": { name: "1.5", tag: "melhor qualidade", desc: "Mais realista. Escolha de voz, personagem fixo e início e fim. Até 1080p.", price: { "480p": 0.08, "720p": 0.14, "1080p": 0.25 }, refs: 14, voices: true, frames: true },
  "grok-imagine-video": { name: "Clássico", tag: "econômico", desc: "Até 720p. É o modelo que edita e estende clipes.", price: { "480p": 0.05, "720p": 0.07 }, refs: 7, voices: false, frames: false }
};
const CLASSICO = "grok-imagine-video";
const XAI_IMG_MODELS = {
  "grok-imagine-image-2.0": { name: "Imagem 2.0", tag: "melhor", price: { low: { "1k": 0.04, "2k": 0.06 }, medium: { "1k": 0.06, "2k": 0.08 } } },
  "grok-imagine-image": { name: "Imagem 1.0", tag: "mais barato", price: { low: { "1k": 0.02, "2k": 0.02 } } }
};
const XAI_IMG_EDIT_EXTRA = 0.01;     // por imagem de entrada na edição (Imagem 2.0)
const XAI_TTS_PRICE = 15 / 1e6;      // US$ por caractere (US$ 15 por 1 milhão)
const XAI_CREDITOS = "https://console.x.ai/"; // site da xAI; lá: menu Billing
const XAI_CHAVES = "https://console.x.ai/";  // site da xAI; lá: menu API Keys
// Vozes prontas da xAI (lista oficial). Todas falam português quando o idioma é pt-BR.
const XAI_VOICES = ["eve", "ara", "leo", "rex", "sal", "carina", "zagan", "helix", "orion", "luna", "iris", "altair", "zenith", "perseus", "helios", "lux", "kepler", "rigel", "cosmo", "celeste", "ursa", "sirius", "lumen", "castor", "naksh", "atlas"];
const vozNome = v => v.charAt(0).toUpperCase() + v.slice(1);
// Modos de vídeo e os modelos que a xAI aceita em cada um
const XAI_MODES = {
  texto: { ico: "✍️", name: "Texto → vídeo", desc: "A IA cria cada cena a partir da descrição da cena (personagens, lugar, câmera).", models: ["grok-imagine-video-1.5-lite", "grok-imagine-video-1.5", CLASSICO] },
  avatar: { ico: "🗣️", name: "Minha foto falando", desc: "Sua foto vira um apresentador que fala a narração, com boca sincronizada.", models: ["grok-imagine-video-1.5-lite", "grok-imagine-video-1.5"], photo: true },
  personagem: { ico: "🧸", name: "Personagem fixo", desc: "A mesma pessoa, produto ou lugar aparece em todas as cenas. Use sua foto e até 6 referências.", models: ["grok-imagine-video-1.5", CLASSICO], refsMode: true },
  imagem: { ico: "🖼️", name: "Animar minhas imagens", desc: "Envie uma imagem por cena (produto, loja, imóvel) e a IA dá movimento a ela.", models: ["grok-imagine-video-1.5-lite", "grok-imagine-video-1.5", CLASSICO], sceneImg: true },
  inicio_fim: { ico: "🎞️", name: "Início e fim", desc: "Envie a foto do começo e do fim (ex.: antes e depois da obra). A IA cria o movimento entre elas.", models: ["grok-imagine-video-1.5"], sceneImg: true },
  foto_ia: { ico: "🎨", name: "Imagens com IA", desc: "A IA desenha uma imagem por cena e o app anima com zoom suave. Bem mais barato.", models: [] }
};
const AUDIO_OPTS = { mudo: "Mudo (uso minha música e voz)", efeitos: "Sons e efeitos da IA", fala: "A IA fala a narração" };
function AI() {
  if (!P.ai) P.ai = {};
  const ai = P.ai;
  if (ai.audio === undefined) ai.audio = ai.clipAudio ? "efeitos" : "mudo";
  if (!XAI_MODES[ai.mode]) ai.mode = "texto";
  if (!ai.tab) ai.tab = "video";
  if (!ai.voice) ai.voice = "auto";
  if (!ai.ttsVoice) ai.ttsVoice = "eve";
  if (!ai.ttsSpeed) ai.ttsSpeed = 1;
  if (!ai.extDur) ai.extDur = 6;
  if (!XAI_IMG_MODELS[ai.imgModel]) ai.imgModel = "grok-imagine-image-2.0";
  if (!ai.imgQuality || !XAI_IMG_MODELS[ai.imgModel].price[ai.imgQuality]) ai.imgQuality = "low";
  if (!["1k", "2k"].includes(ai.imgRes)) ai.imgRes = "1k";
  if (!Array.isArray(ai.refs)) ai.refs = [];
  const md = XAI_MODES[ai.mode];
  if (!XAI_MODELS[ai.model] || (md.models.length && !md.models.includes(ai.model))) ai.model = md.models[0] || "grok-imagine-video-1.5-lite";
  if (!AUDIO_OPTS[ai.audio]) ai.audio = "mudo";
  if (ai.mode === "avatar") ai.audio = "fala";
  if (ai.audio === "fala" && ai.model === CLASSICO) ai.audio = "efeitos"; // o clássico não sincroniza fala
  if (!XAI_MODELS[ai.model].voices) ai.voice = "auto";
  if (!["480p", "720p", "1080p"].includes(ai.res) || !XAI_MODELS[ai.model].price[ai.res]) ai.res = "480p";
  if (usaReferencia() && ai.res === "1080p") ai.res = "720p"; // referência (personagem ou voz escolhida): até 720p
  return ai;
}
// Modo de referência da xAI: personagem fixo, ou voz escolhida (reference_audios)
function usaReferencia() { const ai = P.ai || {}; return ai.mode === "personagem" || (ai.voice && ai.voice !== "auto" && XAI_MODELS[ai.model]?.voices && ai.audio === "fala"); }
function langName() { return LANGS.find(l => l.id === P.voice.lang)?.name || "Português"; }
function falaIdioma() { return { "pt-BR": "Brazilian Portuguese, with a natural Brazilian accent", "en-US": "American English", "es-ES": "Spanish" }[P.voice.lang] || "Brazilian Portuguese"; }
function clipSeconds(x) { const ai = AI(); return clamp(Math.round(x.dur), 1, ai.model === CLASSICO && usaReferencia() ? 10 : 15); }
function precoVideo() { const ai = AI(); return XAI_MODELS[ai.model].price[ai.res] || 0.05; }
function precoImagem() { const ai = AI(); return XAI_IMG_MODELS[ai.imgModel].price[ai.imgQuality][ai.imgRes]; }
function custoCena(x) { return AI().mode === "foto_ia" ? precoImagem() : clipSeconds(x) * precoVideo(); }
function xaiCost() { return TL.scenes.reduce((a, x) => a + custoCena(x), 0); }
function custoNarracao() { return P.scenes.reduce((a, s) => a + (s.text || "").length, 0) * XAI_TTS_PRICE; }
const usd = v => "US$ " + (v < 0.01 && v > 0 ? v.toFixed(3) : v.toFixed(2));
/* Ponte com o servidor: no app do Streamlit, os pedidos à xAI saem do servidor (Python), não do navegador.
   A chave do Grok fica só no servidor e os clipes chegam já baixados, sem bloqueio do navegador. */
const BR = { ok: false, pend: {}, n: 0, tries: 0 };
window.addEventListener("message", e => {
  const m = e.data; if (!m || typeof m !== "object") return;
  if (m.evs === "pong") { if (!BR.ok) { BR.ok = true; window.__evsPonteOk = true; if (ENV.ponte) bridgeStatus(); } return; }
  if (m.evs === "res" && m.res) { const cb = BR.pend[m.res.reqId]; if (cb) { delete BR.pend[m.res.reqId]; cb(m.res); } }
});
function bridgePing() {
  if (BR.ok || window.parent === window || BR.tries > 30) return;
  BR.tries++; try { window.parent.postMessage({ evs: "ping" }, "*"); } catch (e) {}
  setTimeout(bridgePing, 1500);
}
function bridgeCall(method, path, body) {
  return new Promise((res, rej) => {
    const reqId = uid() + "-" + (BR.n++);
    const t = setTimeout(() => { delete BR.pend[reqId]; rej(new Error("O servidor demorou para responder. Confira em instantes se a cena ficou pronta antes de tentar de novo.")); }, 240000);
    BR.pend[reqId] = r => { clearTimeout(t); res(r); };
    window.parent.postMessage({ evs: "req", req: { reqId, method, path, body: body || null } }, "*");
  });
}
function xaiError(status, j, body) {
  const usaImagem = body && (body.image || body.reference_images);
  if (status === 401 || status === 403) return "A xAI recusou a chave. Clique em Sair e entre de novo com a chave do Grok correta.";
  if (status === 402) return "Sem créditos na conta da xAI. Use o botão 💳 Comprar créditos na xAI.";
  if (status === 429) return "Muitos pedidos seguidos na xAI. Espere um minuto e tente de novo.";
  let m = j?.error?.message || j?.error || j?.message || ("Erro " + status);
  if (typeof m !== "string") m = JSON.stringify(m);
  if (usaImagem && status >= 400 && status < 500) m += " · A xAI pode não ter aceitado a imagem enviada. Tente uma foto JPG menor, de frente e bem iluminada, ou use o modo Texto → vídeo.";
  return m;
}
function keyPanel(extra = "") {
  return `<div class="keybox" style="border:1px dashed var(--lilac);border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:10px">
    <b style="font-size:15px">🔑 Coloque a sua chave do Grok para usar a IA paga</b>
    <ol style="margin:0;padding-left:20px;font-size:13.5px;color:var(--muted);display:flex;flex-direction:column;gap:4px">
      <li>Clique em <b>Obter minha chave</b>. Abre o site da xAI (em inglês). Entre na sua conta e clique em <b>API Keys</b> (chaves de API) no menu da esquerda.</li>
      <li>Clique em <b>Create API Key</b> (criar chave), dê um nome e confirme. Copie a chave: ela começa com <b>grok_</b>.</li>
      <li>Volte aqui, cole a chave no campo abaixo e clique em <b>Salvar chave</b>.</li>
    </ol>
    <div style="display:flex;gap:8px;flex-wrap:wrap"><a class="btn" href="${XAI_CHAVES}" target="_blank" rel="noopener">🔑 Obter minha chave do Grok</a><a class="btn" href="${XAI_CREDITOS}" target="_blank" rel="noopener">💳 Comprar créditos</a></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap"><input id="xaiKeyIn" type="password" autocomplete="off" placeholder="Cole aqui a sua chave do Grok (grok_...)" style="flex:1 1 240px;width:auto" aria-label="Chave do Grok"><button class="btn primary" id="xaiKeySave">Salvar chave</button></div>
    <div id="xaiKeyMsg" role="status" aria-live="polite" style="font-size:14px;font-weight:600"></div>
    <span class="mon-note">${ENV.ponte ? "A chave vai só para o servidor e vale enquanto você estiver no app. Ela não fica salva no navegador." : "A chave fica salva só neste navegador."} Sem créditos, a chave não gera nada.</span>${extra}
  </div>`;
}
let keyBoxOpen = false;
function keyMsg(txt, ok) { const el = document.getElementById("xaiKeyMsg"); if (el) { el.textContent = txt; el.style.color = ok ? "var(--ok)" : "#ff8a7a"; } }
async function saveXaiKey() {
  const inp = document.getElementById("xaiKeyIn"); const k = (inp?.value || "").trim();
  if (!k) { keyMsg("Cole a sua chave no campo acima antes de salvar."); toast("Cole a sua chave no campo antes de salvar."); inp?.focus(); return; }
  if (!/^(xai-|grok_)/.test(k) || k.length < 20) { keyMsg("⚠️ Essa não parece uma chave do Grok. Ela começa com grok_. Copie a chave inteira."); toast("Cole a chave do Grok inteira. Ela começa com grok_."); inp?.focus(); return; }
  if (ENV.ponte) {
    if (!BR.ok) { bridgePing(); keyMsg("⏳ A conexão com o servidor ainda está iniciando. Espere alguns segundos e clique de novo."); toast("Espere alguns segundos e tente de novo."); return; }
    const btn = document.getElementById("xaiKeySave"); if (btn) { btn.disabled = true; btn.textContent = "Conferindo com a xAI…"; }
    keyMsg("⏳ Conferindo a chave com a xAI…", true);
    try { const r = await bridgeCall("KEY", "setkey", { key: k }); if (!r.ok) throw new Error(r.error || "Não consegui salvar a chave."); }
    catch (e) { if (btn) { btn.disabled = false; btn.textContent = "Salvar chave"; } keyMsg("⚠️ " + (e.message || String(e))); toast(e.message || String(e), 6000); return; }
  }
  settings.xaiKey = ENV.ponte ? "__servidor__" : k; if (!ENV.ponte) saveSettings();
  keyBoxOpen = false; closeLayer(); renderStep(); toast("Chave do Grok conectada. Agora é só gerar!");
}
function askXaiKey() {
  step = 7; keyBoxOpen = true; closeLayer(); renderStep();
  setTimeout(() => { const i = document.getElementById("xaiKeyIn"); if (i) { i.scrollIntoView({ behavior: "smooth", block: "center" }); i.focus(); } }, 80);
  toast("Cole a sua chave do Grok no campo indicado e clique em Salvar chave.", 5000);
}
async function bridgeStatus() {
  try { const r = await bridgeCall("STATUS", "status"); if (r.ok && r.json?.hasXai) { settings.xaiKey = "__servidor__"; renderStep(); } } catch (e) {}
}
async function xaiFetch(path, body) {
  if (ENV.ponte) {
    if (!BR.ok) { bridgePing(); throw new Error("A conexão com o servidor ainda não ficou pronta. Espere alguns segundos e tente de novo."); }
    const r = await bridgeCall(body ? "POST" : "GET", path, body);
    if (!r.ok) throw new Error(r.error || xaiError(r.status, r.json, body));
    return r.json || {};
  }
  let r;
  try {
    r = await fetch("https://api.x.ai/v1/" + path, {
      method: body ? "POST" : "GET",
      headers: Object.assign({ "Authorization": "Bearer " + settings.xaiKey }, body ? { "Content-Type": "application/json" } : {}),
      body: body ? JSON.stringify(body) : undefined
    });
  } catch (e) {
    throw new Error(ENV.viewer ? "Esta página publicada não acessa a xAI. Use o app no Streamlit ou a versão para computador." : "O navegador bloqueou o acesso à xAI. Me avise para eu passar os clipes para o servidor.");
  }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(xaiError(r.status, j, body));
  return j;
}
const clipJobs = {}; // sceneId -> {status, msg}
// Acompanha o pedido de vídeo até ficar pronto, mostrando o progresso (%) e somando o gasto real informado pela xAI
async function xaiWait(id, onProg) {
  for (let k = 0; k < 160; k++) {
    await new Promise(r => setTimeout(r, 4000));
    const j = await xaiFetch("videos/" + id);
    if (typeof j.progress === "number" && onProg) onProg(j.progress);
    if (j.status === "done") {
      const ticks = j.usage?.cost_in_usd_ticks;
      if (typeof ticks === "number") { P.aiSpent = (P.aiSpent || 0) + ticks / 1e10; save(); }
      if (!j.video?.url && !j.video?.data) throw new Error("A moderação da xAI bloqueou esta cena. Mude a descrição da cena e tente de novo.");
      return j.video;
    }
    if (j.status === "failed" || j.status === "expired" || j.error) throw new Error(j.error?.message || "A geração falhou. Tente de novo ou mude a descrição da cena.");
  }
  throw new Error("Demorou demais. Tente esta cena de novo.");
}
// Monta o pedido de vídeo exatamente no formato da API para o modo escolhido
function clipBody(x) {
  const ai = AI(), st = STYLES[P.style]?.name || "", scene = x.s.visual || x.s.title;
  const body = { model: ai.model, duration: clipSeconds(x), aspect_ratio: P.format, resolution: ai.res, generate_audio: ai.audio !== "mudo" };
  const vozRef = ai.voice !== "auto" && XAI_MODELS[ai.model].voices && ai.audio === "fala";
  if (vozRef) body.reference_audios = [{ voice_id: ai.voice }];
  const comVoz = vozRef ? " speaking with the voice from <AUDIO_0>," : "";
  const fala = ai.audio === "fala" && x.s.text ? ` Someone${comVoz} says in ${falaIdioma()}: "${x.s.text}".` : "";
  if (ai.mode === "avatar") {
    body.image = { url: P.presenter.photo };
    body.prompt = `The person in the image talks directly to the camera with natural facial expressions and subtle head movement,${comVoz || ""} speaking in ${falaIdioma()}, saying exactly: "${x.s.text}". Accurate lip sync, clear and friendly voice. Keep the person's appearance and the background. No text on screen.`;
  } else if (ai.mode === "personagem") {
    const refs = refImages();
    body.reference_images = refs.map(r => ({ url: r.img }));
    const tags = refs.map((r, i) => `<IMAGE_${i}> (${r.label})`).join(", ");
    body.prompt = `Use these references: ${tags}. ${refs.some(r => r.label === "main character") ? "<IMAGE_0> is the main character. " : ""}${scene}. Style: ${st}.${fala} No text, no captions on screen.`;
  } else if (ai.mode === "imagem") {
    body.image = { url: x.s.img };
    body.prompt = `Bring this image to life with smooth cinematic motion and a gentle camera move. ${scene}.${fala} No text on screen.`;
  } else if (ai.mode === "inicio_fim") {
    if (x.s.img) body.image = { url: x.s.img };
    body.last_frame = { url: x.s.imgEnd };
    if (x.s.imgMid) body.keyframes = [{ image: { url: x.s.imgMid }, timestamp_s: Math.max(1 / 3, Math.round((body.duration / 2) * 3) / 3) }];
    body.prompt = `Smooth, realistic transition from the first frame to the last frame. ${scene}.${fala} No text on screen.`;
  } else {
    body.prompt = `${scene}. Style: ${st}.${fala} No text, no captions, no letters on screen.`;
  }
  return body;
}
// Referências do personagem fixo: sua foto (personagem principal) + até 6 imagens extras
function refImages() {
  const out = [];
  if (P.presenter.photo) out.push({ img: P.presenter.photo, label: "main character" });
  (AI().refs || []).forEach(r => out.push({ img: r.img, label: r.label || "reference" }));
  return out.slice(0, XAI_MODELS[AI().model].refs || 7);
}
function shrinkDataURL(src, max = 1024) {
  return new Promise((res) => {
    const im = new Image();
    im.onload = () => { const k = Math.min(1, max / Math.max(im.width, im.height)); const c = document.createElement("canvas"); c.width = Math.round(im.width * k); c.height = Math.round(im.height * k); c.getContext("2d").drawImage(im, 0, 0, c.width, c.height); try { res(c.toDataURL("image/jpeg", 0.85)); } catch (e) { res(src); } };
    im.onerror = () => res(src); im.src = src;
  });
}
const bgImgs = {};
function loadSceneImage(s) {
  if (!s.img) { delete bgImgs[s.id]; return; }
  if (bgImgs[s.id] && bgImgs[s.id]._src === s.img) return;
  const im = new Image(); im._src = s.img; im.onload = () => { if (!player.playing) renderFrame(player.t); }; im.src = s.img; bgImgs[s.id] = im;
}
async function imagemDaResposta(j) {
  const d = j?.data?.[0];
  if (d?.b64_json) return await shrinkDataURL((d.b64_json.startsWith("data:") ? "" : "data:image/png;base64,") + d.b64_json);
  if (d?.url) return d.url;
  throw new Error("A xAI não devolveu a imagem. Ela pode ter sido bloqueada pela moderação: mude a descrição.");
}
function imgParams() { const ai = AI(); const p = { model: ai.imgModel, n: 1, response_format: "b64_json", resolution: ai.imgRes }; if (ai.imgModel === "grok-imagine-image-2.0") p.quality = ai.imgQuality; return p; }
async function xaiImage(x) {
  return imagemDaResposta(await xaiFetch("images/generations", Object.assign(imgParams(), { prompt: `${x.s.visual || x.s.title}. Style: ${STYLES[P.style]?.name || ""}. No text, no letters, no captions.`, aspect_ratio: P.format })));
}
async function xaiImageEdit(x, instr, juntar) {
  const p = Object.assign(imgParams(), { model: "grok-imagine-image-2.0", prompt: instr, aspect_ratio: P.format });
  if (!p.quality) p.quality = "medium";
  if (juntar) p.images = [x.s.img, ...AI().refs.map(r => r.img)].filter(Boolean).slice(0, 5).map(u => ({ url: u, type: "image_url" }));
  else p.image = { url: x.s.img, type: "image_url" };
  return imagemDaResposta(await xaiFetch("images/edits", p));
}
function routeClip(v) {
  if (v._routed || !audio()) return;
  try { const n = AC.createMediaElementSource(v); n.connect(voiceBus); v._routed = true; } catch (e) {}
}
function loadClip(sceneId, url, noCors, isLocal) {
  const v = document.createElement("video");
  if (!noCors && !isLocal) v.crossOrigin = "anonymous";
  v.muted = true; v.playsInline = true; v.preload = "auto"; v.src = url;
  v._tainted = !!noCors;
  v.addEventListener("loadeddata", () => { if (!player.playing) renderFrame(player.t); });
  v.addEventListener("error", () => { if (!noCors && !isLocal) loadClip(sceneId, url, true); }, { once: true });
  runtime.clipVideos[sceneId] = v;
}
let clipsRunning = false;
function sceneDone(s) { return AI().mode === "foto_ia" ? !!(s.img && s.aiImg) : !!s.clipUrl; }
// O que falta para gerar a cena no modo atual (ou "" se está tudo certo)
function faltaNaCena(s) {
  const ai = AI();
  if (ai.mode === "imagem" && !s.img) return "Envie a imagem desta cena (📷).";
  if (ai.mode === "inicio_fim" && !s.imgEnd) return "Envie a foto do fim desta cena (📷 Fim).";
  return "";
}
async function receberVideo(x, vid) {
  let local = "";
  if (vid.data) { try { local = URL.createObjectURL(await (await fetch(vid.data)).blob()); } catch (e) { local = ""; } }
  x.s.clipUrl = vid.url || x.s.clipUrl; x.s.clipDur = vid.duration || x.s.clipDur; delete x.s.aiImg;
  save(); loadClip(x.s.id, local || vid.url, false, !!local);
}
// Gera, estende ou edita cenas. kind: gerar | estender | editar | img_gerar | img_editar | img_juntar
async function runAI(only, kind = "gerar", skipDone = false) {
  if (!settings.xaiKey) { askXaiKey(); return false; }
  const ai = AI();
  if (XAI_MODES[ai.mode].photo && !P.presenter.photo && kind === "gerar") { toast("Envie a sua foto no passo Apresentador primeiro."); return false; }
  if (ai.mode === "personagem" && kind === "gerar" && !refImages().length) { toast("Envie a sua foto no passo Apresentador ou adicione uma referência."); return false; }
  if (timelineDirty) buildTimeline();
  const imgKind = kind.startsWith("img_");
  const list = TL.scenes.filter(x => (!only || x.s.id === only) && !(skipDone && !imgKind && sceneDone(x.s)));
  if (!list.length) return true;
  if (kind === "gerar" && ai.mode !== "foto_ia") {
    const miss = list.map(x => [x, faltaNaCena(x.s)]).filter(a => a[1]);
    if (miss.length) { toast(`Cena ${miss.map(a => a[0].i + 1).join(", ")}: ${miss[0][1]}`, 6000); return false; }
  }
  if ((kind === "estender" || kind === "editar") && list.some(x => !x.s.clipUrl)) { toast("Gere o clipe desta cena primeiro."); return false; }
  if (kind === "editar" && list.some(x => (x.s.clipDur || 0) > 8.7)) { toast("A xAI só edita clipes de até 8,7 segundos. Esta cena é mais longa."); return false; }
  const editTxt = (document.getElementById(kind.startsWith("img_") ? "imgEdit" : "aiEdit")?.value || "").trim();
  if ((kind === "editar" || kind === "img_editar" || kind === "img_juntar") && !editTxt) { toast("Escreva o que a IA deve fazer no campo de instrução."); document.getElementById(kind.startsWith("img_") ? "imgEdit" : "aiEdit")?.focus(); return false; }
  if ((kind === "img_editar" || kind === "img_juntar") && list.some(x => !x.s.img)) { toast("A cena precisa de uma imagem primeiro (envie com 📷 ou gere com 🎨)."); return false; }
  if (kind === "img_juntar" && !ai.refs.length) { toast("Adicione pelo menos uma imagem de referência para juntar."); return false; }
  clipsRunning = true; renderStep();
  await Promise.all(list.map(async (x, n) => {
    await new Promise(r => setTimeout(r, n * 2200)); // respeita o limite de pedidos
    const rotulo = { gerar: "Gerando", estender: "Estendendo", editar: "Editando", img_gerar: "Desenhando", img_editar: "Editando imagem", img_juntar: "Juntando imagens" }[kind] || "Gerando";
    clipJobs[x.s.id] = { status: "run", msg: rotulo + "…" }; renderClipRows();
    const prog = p => { clipJobs[x.s.id] = { status: "run", msg: `${rotulo}… ${p}%` }; renderClipRows(); };
    try {
      if (kind === "img_gerar" || (kind === "gerar" && ai.mode === "foto_ia")) {
        x.s.img = await xaiImage(x); x.s.aiImg = true;
        if (kind === "gerar") { delete x.s.clipUrl; delete x.s.clipDur; delete runtime.clipVideos[x.s.id]; } // no modo Imagens com IA, a imagem vira o fundo
        loadSceneImage(x.s); save();
      } else if (kind === "img_editar" || kind === "img_juntar") {
        x.s.img = await xaiImageEdit(x, editTxt, kind === "img_juntar"); x.s.aiImg = true; loadSceneImage(x.s); save();
      } else {
        let req;
        if (kind === "estender") req = await xaiFetch("videos/extensions", { model: CLASSICO, prompt: `Continue the scene naturally. ${x.s.visual || x.s.title}`, duration: clamp(ai.extDur, 2, 10), video: { url: x.s.clipUrl } });
        else if (kind === "editar") req = await xaiFetch("videos/edits", { model: CLASSICO, prompt: editTxt, video: { url: x.s.clipUrl } });
        else req = await xaiFetch("videos/generations", clipBody(x));
        if (!req.request_id) throw new Error("A xAI não devolveu o número do pedido.");
        await receberVideo(x, await xaiWait(req.request_id, prog));
      }
      clipJobs[x.s.id] = { status: "ok", msg: "Pronto" };
    } catch (e) {
      clipJobs[x.s.id] = { status: "err", msg: e.message || String(e) };
    }
    renderClipRows();
  }));
  clipsRunning = false; renderStep();
  return list.every(x => clipJobs[x.s.id]?.status === "ok");
}
/* ---------- Voz da IA (texto para fala da xAI): a narração entra no arquivo baixado ---------- */
let ttsRunning = false;
async function ttsBuffer(text, voice) {
  const j = await xaiFetch("tts", { text, language: P.voice.lang === "pt-BR" ? "pt-BR" : P.voice.lang.slice(0, 2), voice_id: voice, speed: AI().ttsSpeed, output_format: { codec: "mp3", sample_rate: 44100, bit_rate: 128000 }, with_timestamps: true });
  if (!j.audio) throw new Error("A xAI não devolveu o áudio da voz.");
  const bin = atob(j.audio), bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return await audio().decodeAudioData(bytes.buffer);
}
async function ouvirVoz(v) {
  if (!settings.xaiKey) { askXaiKey(); return; }
  if (!audio()) return; AC.resume();
  try {
    toast("Gerando amostra da voz " + vozNome(v) + "…");
    const buf = await ttsBuffer(P.voice.lang === "pt-BR" ? "Olá! Esta é a minha voz para o seu vídeo." : "Hi! This is my voice for your video.", v);
    const src = AC.createBufferSource(); src.buffer = buf; src.connect(AC.destination); src.start();
  } catch (e) { toast(e.message || String(e), 5000); }
}
// Gera a voz de cada cena, ajusta a duração das cenas ao tamanho da fala e junta tudo numa narração só
async function gerarNarracaoIA() {
  if (!settings.xaiKey) { askXaiKey(); return false; }
  if (!audio()) { toast("Este navegador não toca áudio."); return false; }
  if (!P.scenes.some(s => (s.text || "").trim())) { toast("As cenas ainda não têm texto de narração."); return false; }
  ttsRunning = true; renderStep();
  try {
    const voice = AI().ttsVoice, bufs = [];
    for (let i = 0; i < P.scenes.length; i++) {
      const s = P.scenes[i];
      toast(`Gerando a voz da cena ${i + 1} de ${P.scenes.length}…`, 2500);
      bufs.push((s.text || "").trim() ? await ttsBuffer(s.text, voice) : null);
    }
    const sr = AC.sampleRate, ch = Math.max(1, ...bufs.filter(Boolean).map(b => b.numberOfChannels));
    const gap = 0.35, lead = 0.15, durs = {};
    P.scenes.forEach((s, i) => { durs[s.id] = bufs[i] ? Math.max(2.5, lead + bufs[i].duration + gap) : 3; });
    const total = Object.values(durs).reduce((a, b) => a + b, 0);
    const out = AC.createBuffer(ch, Math.ceil(total * sr), sr);
    let t = 0;
    P.scenes.forEach((s, i) => {
      const b = bufs[i];
      if (b) for (let c = 0; c < ch; c++) out.getChannelData(c).set(b.getChannelData(Math.min(c, b.numberOfChannels - 1)), Math.floor((t + lead) * sr));
      t += durs[s.id];
    });
    runtime.narrBuf = out; runtime.narrationUrl = "mem"; runtime.narrationName = "Voz da IA: " + vozNome(voice); runtime.narrationDur = total;
    runtime.sceneDurs = durs; runtime.ttsTexts = Object.fromEntries(P.scenes.map(s => [s.id, s.text || ""]));
    P.voice.mode = "xai"; timelineDirty = true; save();
    toast("Narração pronta! Ela entra no vídeo baixado.");
    return true;
  } catch (e) { toast(e.message || String(e), 6000); return false; }
  finally { ttsRunning = false; renderStep(); }
}
function narracaoIAValida() {
  return P.voice.mode === "xai" && runtime.narrBuf && runtime.sceneDurs && P.scenes.every(s => runtime.sceneDurs[s.id] !== undefined && (runtime.ttsTexts?.[s.id] ?? "") === (s.text || ""));
}
function vozIAPainel() {
  const ai = AI(), ok = narracaoIAValida();
  return `<div style="display:flex;flex-direction:column;gap:10px">
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end">
      <label class="f" for="ttsVoice" style="flex:1 1 200px">Voz<select id="ttsVoice">${XAI_VOICES.map(v => `<option value="${v}" ${ai.ttsVoice === v ? "selected" : ""}>${vozNome(v)}${v === "eve" ? " (padrão)" : ""}</option>`).join("")}</select></label>
      <button class="btn" id="ttsTest">▶ Ouvir esta voz</button>
    </div>
    <label class="f" for="ttsSpeed">Velocidade da fala: ${ai.ttsSpeed.toFixed(1)}×<input id="ttsSpeed" type="range" min="0.7" max="1.5" step="0.1" value="${ai.ttsSpeed}"></label>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><button class="btn primary" id="ttsGen" ${ttsRunning ? "disabled" : ""}>${ttsRunning ? "Gerando a voz…" : (ok ? "🎙️ Gerar a narração de novo" : "🎙️ Gerar narração com a voz da IA")}</button>
      <span class="mon-note">Custo: cerca de <b>${usd(custoNarracao())}</b> (US$ 15 por 1 milhão de letras).</span></div>
    ${ok ? `<span class="pill ok" style="align-self:flex-start">✓ Narração pronta: ${esc(runtime.narrationName)} · ${fmtT(runtime.narrationDur)}</span>` : (P.voice.mode === "xai" && runtime.narrBuf ? hint("Você mudou o texto das cenas. Gere a narração de novo para a voz acompanhar.", "warn") : "")}
    <span class="mon-note">A duração de cada cena se ajusta ao tamanho da fala, e a voz entra no arquivo baixado.</span>
  </div>`;
}
/* vídeo profissional em um clique: confirma o custo, gera o que falta e finaliza */
let proRunning = false;
function proPending() { if (timelineDirty) buildTimeline(); return TL.scenes.filter(x => !sceneDone(x.s)); }
function precisaNarracao() { return P.voice.mode === "xai" && !narracaoIAValida(); }
function proCost() { return proPending().reduce((a, x) => a + custoCena(x), 0) + (precisaNarracao() ? custoNarracao() : 0); }
function openProConfirm() {
  if (exporting || clipsRunning || proRunning || ttsRunning) return;
  const box = document.getElementById("proConfirm");
  if (!settings.xaiKey) { askXaiKey(); return; }
  const ai = AI(), miss = proPending(), nar = precisaNarracao();
  box.hidden = false;
  box.innerHTML = `<div class="hint" style="margin-top:0;border-color:var(--lilac)"><span>⭐</span><div>
    <b>Vídeo profissional com IA</b><br>
    Modo: <b>${esc(XAI_MODES[ai.mode].name)}</b>${ai.mode !== "foto_ia" ? ` · modelo <b>${esc(XAI_MODELS[ai.model].name)}</b> · ${ai.res} · ${esc(AUDIO_OPTS[ai.audio])}` : ""}.<br>
    ${miss.length || nar ? `Vai gerar ${miss.length ? `<b>${miss.length} ${miss.length > 1 ? "cenas" : "cena"}</b>` : ""}${miss.length && nar ? " e " : ""}${nar ? "<b>a narração com a voz da IA</b>" : ""} por cerca de <b>${usd(proCost())}</b>, cobrados na sua conta da xAI.` : "Tudo já está pronto. Vou só finalizar o vídeo, sem custo."}
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px"><button class="btn primary sm" id="proYes">Confirmar e criar</button><button class="btn sm" id="proOpts">Mudar opções</button><button class="btn ghost sm" id="proNo">Cancelar</button></div>
    <div class="mon-note" style="margin-top:8px">Sem créditos? <a href="${XAI_CREDITOS}" target="_blank" rel="noopener" style="color:var(--lilac)">💳 Comprar créditos na xAI</a></div>
  </div></div>`;
}
async function runPro() {
  const box = document.getElementById("proConfirm"); box.hidden = true; box.innerHTML = "";
  proRunning = true; step = 7; AI().tab = "video"; renderStep(); $("#stepArea").scrollIntoView({ behavior: "smooth", block: "start" });
  if (precisaNarracao() && !(await gerarNarracaoIA())) { proRunning = false; updateFinishBtn(); return; }
  const ok = await runAI(null, "gerar", true);
  if (!ok) { proRunning = false; updateFinishBtn(); toast("Algumas cenas não ficaram prontas. Veja o erro em cada cena e tente de novo.", 6000); return; }
  toast("Tudo pronto. Finalizando o vídeo…");
  proRunning = true; updateFinishBtn();
  await exportVideo();
  proRunning = false; updateFinishBtn();
}

/* ============ exportação ============ */
let exporting = false, recorder = null;
function pickMime() {
  const opts = [["video/mp4;codecs=avc1.42E01E,mp4a.40.2", "mp4"], ["video/mp4", "mp4"], ["video/webm;codecs=vp9,opus", "webm"], ["video/webm;codecs=vp8,opus", "webm"], ["video/webm", "webm"]];
  if (!window.MediaRecorder) return null;
  for (const [m, e] of opts) { try { if (MediaRecorder.isTypeSupported(m)) return { mime: m, ext: e }; } catch (_) {} }
  return { mime: "", ext: "webm" };
}
async function exportVideo(opts = {}) {
  if (exporting) return null;
  const mt = pickMime();
  if (!mt || !cv.captureStream) { toast("Este navegador não grava vídeo. Use o Chrome, Edge ou Safari atualizados."); return null; }
  audio(); if (AC) await AC.resume();
  if (timelineDirty) buildTimeline();
  if (Object.values(runtime.clipVideos).some(v => v._tainted)) { toast("O servidor da xAI não liberou os clipes para juntar no navegador. Use o botão Abrir em cada cena para baixar os clipes.", 7000); return null; }
  let stream;
  try { stream = cv.captureStream(30); }
  catch (e) { toast("Os clipes de IA não permitem gravação aqui. Baixe os clipes separadamente."); return null; }
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
  if (!chunks.length || cancelExport) { cancelExport = false; renderStep(); toast("Exportação cancelada."); return null; }
  const blob = new Blob(chunks, { type: (mt.mime || "video/webm").split(";")[0] });
  const url = URL.createObjectURL(blob);
  if (opts.multi) { renderStep(); return { blob, url, ext: mt.ext }; }
  if (runtime.exportUrl) URL.revokeObjectURL(runtime.exportUrl);
  runtime.exportBlob = blob; runtime.exportUrl = url; runtime.exportExt = mt.ext;
  renderStep();
  toast("Vídeo pronto! Confira e baixe abaixo.");
  return { blob, url, ext: mt.ext };
}
let cancelExport = false;
function stopExport() { cancelExport = true; player.onEnd = null; pause(); if (recorder && recorder.state !== "inactive") recorder.stop(); }
async function downloadExport() {
  if (!runtime.exportBlob) return;
  return baixarArquivo(runtime.exportBlob, nomeArquivo("", runtime.exportExt), runtime.exportUrl);
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
    hint("Com a chave do Grok, cada cena também pode virar um <b>clipe animado gerado por IA</b> nesse estilo. Isso fica no último passo."),

  () => head(3, "Quem apresenta?", "Use a sua foto, escolha um personagem ou faça o vídeo sem apresentador.") +
    `<div class="grid">${[["none", "🚫", "Sem apresentador", "Só texto e animação"], ["emoji", "🦊", "Personagem", "Bichos e pessoas animadas"], ["photo", "📸", "Minha foto", "Sua foto no vídeo"]].map(([id, ic, n, d]) => optCard(P.presenter.type === id, `data-ptype="${id}"`, ic, n, d)).join("")}</div>` +
    (P.presenter.type === "emoji" ? `<div class="section"><h3>Escolha o personagem</h3><div class="seg">${CHARACTERS.map(c => `<button data-char="${c}" class="${P.presenter.emoji === c ? "on" : ""}" style="font-size:22px;padding:6px 10px">${c}</button>`).join("")}</div></div>` : "") +
    (P.presenter.type === "photo" ? `<div class="section"><h3>Envie uma foto sua</h3><div class="photo-drop"><div class="ph" style="${P.presenter.photo ? `background-image:url(${P.presenter.photo});border-style:solid` : ""}">${P.presenter.photo ? "" : "sem foto"}</div><div style="display:flex;flex-direction:column;gap:8px"><label class="btn" for="photoIn">Escolher foto</label><input id="photoIn" type="file" accept="image/*" hidden>${P.presenter.photo ? `<button class="btn ghost sm" id="photoDel">Remover foto</button>` : ""}</div></div>` +
      hint("Use uma foto de frente e bem iluminada. Na prévia ela aparece num círculo que reage à voz. Para a foto <b>falar com movimento de boca</b>, use os clipes de IA (xAI) no último passo, com a opção de usar sua foto como imagem inicial.") + "</div>" : ""),

  () => {
    const vs = voices.filter(v => v.lang && v.lang.toLowerCase().replace("_", "-").startsWith(P.voice.lang.slice(0, 2).toLowerCase()));
    return head(4, "Voz e idioma", "Escolha como a narração vai soar.") +
      `<div class="grid">${[["browser", "🗣️", "Voz pronta", "Vozes do navegador, só na prévia"], ["xai", "✨", "Voz da IA", "Voz natural da xAI, entra no arquivo"], ["record", "🎙️", "Minha voz", "Grave lendo o roteiro"], ["upload", "📁", "Enviar áudio", "Narração gravada no celular"], ["none", "🔇", "Sem voz", "Só música e legendas"]].map(([id, ic, n, d]) => optCard(P.voice.mode === id, `data-vmode="${id}"`, ic, n, d)).join("")}</div>` +
      `<div class="section"><h3>Idioma</h3><div class="seg">${LANGS.map(l => `<button data-lang="${l.id}" class="${P.voice.lang === l.id ? "on" : ""}">${l.name}</button>`).join("")}</div></div>` +
      (P.voice.mode === "browser" ? `<div class="section"><h3>Voz</h3>${vs.length ? `<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><select id="voiceSel" style="flex:1 1 240px;width:auto">${vs.map(v => `<option ${pickVoice()?.name === v.name ? "selected" : ""}>${esc(v.name)}</option>`).join("")}</select><button class="btn" id="voiceTest">▶ Ouvir</button></div>` : `<p class="lead">Nenhuma voz neste idioma foi encontrada no seu navegador.</p>`}<label class="f" style="margin-top:12px" for="rate">Velocidade: ${(P.voice.rate || 1).toFixed(1)}×<input id="rate" type="range" min="0.7" max="1.4" step="0.1" value="${P.voice.rate || 1}"></label>` + hint("A voz pronta toca na prévia, mas o navegador não deixa ela ser gravada dentro do arquivo de vídeo. Para ter narração no vídeo baixado, use <b>Minha voz</b> ou <b>Enviar áudio</b>.", "warn") + "</div>" : "") +
      (P.voice.mode === "record" ? `<div class="section"><h3>Gravar narração</h3><p class="lead">Ao clicar, o vídeo toca sem som e as legendas viram teleprompter. Leia em voz alta. A gravação para sozinha no fim.</p><button class="btn primary" id="recBtn">${micRec ? "■ Parar gravação" : "● Começar a gravar"}</button>${runtime.narrationUrl ? `<p class="mon-note" style="margin-top:10px">Narração atual: ${esc(runtime.narrationName)} · ${fmtT(runtime.narrationDur)}</p>` : ""}${ENV.viewer ? hint("Esta página publicada não tem acesso ao microfone. Grave no celular e use <b>Enviar áudio</b>, ou use a versão para computador.", "warn") : ""}</div>` : "") +
      (P.voice.mode === "xai" ? `<div class="section"><h3>✨ Voz da IA (xAI)</h3>${settings.xaiKey ? vozIAPainel() : keyPanel()}</div>` : "") +
      (P.voice.mode === "upload" ? `<div class="section"><h3>Arquivo de narração</h3><label class="btn" for="audIn">Escolher áudio (mp3, m4a, wav, ogg)</label><input id="audIn" type="file" accept="audio/*" hidden>${runtime.narrationUrl ? `<p class="mon-note" style="margin-top:10px">${esc(runtime.narrationName)} · ${fmtT(runtime.narrationDur)}. A duração do vídeo segue o áudio.</p>` : ""}</div>` : "");
  },

  () => head(5, "Escreva o texto ou deixe a IA criar", "Cada cena tem um título que aparece grande na tela e a fala da narração.") +
    `${!engineName() && ENV.hostAI ? `<div class="gen-card"><h3>✨ Roteiro novo com IA</h3><p class="mon-note" style="margin:0">Para criar um roteiro novo, preencha <b>Tema do vídeo</b> e <b>Descreva o seu serviço ou produto</b> no <b>topo da página</b> e clique em <b>Gerar roteiro com IA</b>. As cenas novas aparecem aqui. Você também pode editar as cenas abaixo à mão.</p></div>` : `<div class="gen-card"><h3>✨ A IA cria o roteiro</h3><p class="mon-note" style="margin:0">${engineName() ? `Usando <b>${engineName()}</b>. Diga o tema e o que não pode faltar.` : ENV.hostAI ? `O roteiro com IA (${esc(ENV.hostAI)}) é gerado no <b>topo da página</b>, acima do estúdio. As cenas aparecem aqui para você editar.` : "Nenhuma IA conectada: vou montar um roteiro-modelo. Para roteiros de verdade, cole a chave da Groq em <b>Chaves de IA</b> (versão para computador)."}</p>
      <label class="f" for="styleDesc">Descreva o seu serviço ou produto<textarea id="styleDesc" rows="3" placeholder="O que é, o que faz, para quem é, diferenciais, preço e contato. Ex.: Pizzaria do Zé, delivery em Campinas, massa de fermentação natural, 2 pizzas grandes por R$ 79 às sextas, pedidos pelo WhatsApp (19) 99999-0000">${esc(P.styleDesc || "")}</textarea></label>
      <div class="ai-box"><input id="topic" type="text" placeholder="Tema. Ex.: Promoção de pizza de sexta, 2 por R$ 79" value="${esc(P.topic || "")}" aria-label="Tema do vídeo"><button class="btn primary" id="aiBtn" ${aiBusy ? "disabled" : ""}>${aiBusy ? "Escrevendo…" : "Gerar roteiro"}</button>${aiBusy && ENV.sample ? `<button class="btn" id="aiStop">Parar</button>` : ""}</div></div>`}` +
    `<div class="scenes" id="sceneList">${P.scenes.map((s, i) => sceneCard(s, i)).join("")}</div>` +
    `<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn" id="addScene">+ Adicionar cena</button></div>`,

  () => head(6, "Música, legendas e marca", "Trilhas criadas na hora, sem direitos autorais.") +
    `<div class="grid">${Object.entries(MUSIC).map(([k, m]) => optCard(P.music === k, `data-music="${k}"`, m.ico, m.name, m.desc)).join("")}</div>` +
    (P.music !== "none" ? `<div style="margin-top:10px"><button class="btn sm" id="musTest">▶ Ouvir trecho</button></div>` : "") +
    `<div class="section"><h3>Legendas</h3><div class="seg"><button data-cap="1" class="${P.captions ? "on" : ""}">Mostrar legendas</button><button data-cap="0" class="${!P.captions ? "on" : ""}">Sem legendas</button></div></div>` +
    `<div class="section"><label class="f" for="brand">Sua marca ou @ (aparece no canto)<input id="brand" type="text" maxlength="40" value="${esc(P.brand || "")}" placeholder="@seuperfil"></label></div>`,

  () => {
    const dur = TL.total, ai = AI();
    const narrInFile = ["upload", "record", "xai"].includes(P.voice.mode) && runtime.narrationUrl && (P.voice.mode !== "xai" || narracaoIAValida());
    return head(7, "Clique em gerar e pronto!", "O vídeo é gravado em tempo real a partir da prévia, com animação, música e narração.") +
      `<div class="gen-card">
        <h3>🎬 Gerar meu vídeo</h3>
        <ul class="checklist">
          <li class="ok"><span class="s">✓</span>${TL.scenes.length} cenas · ${fmtT(dur)} · ${P.format}</li>
          <li class="ok"><span class="s">✓</span>Estilo ${STYLES[P.style]?.name} · música ${MUSIC[P.music]?.name.toLowerCase()}</li>
          <li class="${narrInFile ? "ok" : ""}"><span class="s">${narrInFile ? "✓" : "–"}</span>${narrInFile ? "Narração incluída no arquivo" : (P.voice.mode === "browser" ? "Voz pronta só na prévia (não entra no arquivo)" : "Sem narração no arquivo")}</li>
          <li class="${Object.keys(runtime.clipVideos).length || P.scenes.some(s => s.img) ? "ok" : ""}"><span class="s">${Object.keys(runtime.clipVideos).length || P.scenes.some(s => s.img) ? "✓" : "–"}</span>${Object.keys(runtime.clipVideos).length ? "Clipes de IA nas cenas" : P.scenes.some(s => s.img) ? "Imagens nas cenas" : "Fundos animados do estilo"}</li>
        </ul>
        ${exporting ? `<div class="bar"><i id="expBar"></i></div><div style="display:flex;justify-content:space-between;align-items:center"><span class="mon-note">Gravando… <span id="expPct">0%</span>. Deixe esta aba aberta e visível.</span><button class="btn sm" id="expStop">Cancelar</button></div>`
          : `<div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" id="expBtn">🎬 Gerar meu vídeo (${fmtT(dur)})</button><button class="btn" id="expAll" title="Grava o mesmo vídeo em 9:16, 1:1 e 16:9, um depois do outro">📐 Gerar nos 3 formatos</button></div>
             <span class="mon-note">📐 <b>3 formatos</b>: o mesmo vídeo para Reels/Stories (9:16), feed (1:1) e YouTube (16:9). Leva 3 vezes o tempo do vídeo.</span>`}
        ${multiRunning ? `<span class="pill run" style="align-self:flex-start">Gravando os 3 formatos… ${(runtime.exports || []).length} de 3 prontos</span>` : ""}
        ${(runtime.exports || []).length && !multiRunning ? `<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><b style="font-size:13px">Seus 3 formatos:</b>${runtime.exports.map((e, i) => `<button class="btn sm primary" data-dlfmt="${i}">⬇ ${e.fmt} · ${FMT_SUFIXO[e.fmt]} (${(e.blob.size / 1048576).toFixed(1)} MB)</button>`).join("")}</div>` : ""}
        ${runtime.exportUrl && !exporting ? `<video class="result-video" src="${runtime.exportUrl}" controls playsinline></video><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" id="dlBtn">⬇ Baixar vídeo (.${runtime.exportExt})</button><span class="mon-note" style="align-self:center">${(runtime.exportBlob.size / 1048576).toFixed(1)} MB</span></div>` : ""}
      </div>` + postCard() + idiomasCard() +
      `<div class="gen-card" style="margin-top:16px">
        <h3>🤖 IA paga: vídeo, imagens e voz (Grok Imagine · xAI)</h3>
        <div style="border:1px solid var(--rec);background:var(--rec-soft);border-radius:12px;padding:12px 14px;display:flex;gap:10px;align-items:flex-start"><span style="font-size:20px;line-height:1.2">💸</span><div style="display:flex;flex-direction:column;gap:6px"><b style="font-size:15px">Vídeos profissionais sem assinatura mensal.</b><span style="color:var(--fg)">Este app é uma ponte entre você e uma IA de vídeo profissional (Grok Imagine, da xAI). Em vez de pagar uma assinatura todo mês, você usa a sua própria chave e paga só pelo vídeo que gerar, direto na sua conta da xAI, a partir de poucos reais por vídeo.</span><span class="mon-note">O custo exato aparece abaixo, antes de você gerar.${P.aiSpent ? ` Gasto real já registrado neste projeto: <b>${usd(P.aiSpent)}</b>.` : ""}</span><a class="btn sm" href="${XAI_CREDITOS}" target="_blank" rel="noopener" style="align-self:flex-start;margin-top:4px">💳 Comprar créditos na xAI</a></div></div>
        ${!settings.xaiKey || keyBoxOpen ? keyPanel(settings.xaiKey ? `<button class="btn ghost sm" id="xaiKeyCancel" style="align-self:flex-start">Manter a chave atual</button>` : "") : `<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><span class="pill ok">✓ Chave do Grok conectada</span><button class="btn ghost sm" id="xaiKeyChange">Trocar chave</button></div>`}
        <div class="seg" style="display:flex" role="tablist">${[["video", "🎬 Vídeo"], ["imagens", "🖼️ Imagens"], ["voz", "🎙️ Voz da IA"]].map(([k, n]) => `<button data-aitab="${k}" class="${ai.tab === k ? "on" : ""}" role="tab" aria-selected="${ai.tab === k}">${n}</button>`).join("")}</div>
        ${ai.tab === "video" ? `
        <div><b style="font-size:13px">1. O que a IA vai fazer</b>
          <div class="grid" style="margin-top:8px">${Object.entries(XAI_MODES).map(([k, m]) => optCard(ai.mode === k, `data-aimode="${k}"`, m.ico, m.name, m.desc)).join("")}</div></div>
        ${XAI_MODES[ai.mode].photo && !P.presenter.photo ? hint(`Este modo usa a sua foto. <button class="btn sm" data-step="3">Enviar foto no passo Apresentador</button>`, "warn") : ""}
        ${ai.mode === "avatar" ? hint("A fala vem do próprio clipe, com a boca sincronizada. A IA tenta seguir o texto de cada cena. Confira antes de publicar.") : ""}
        ${ai.mode === "personagem" ? refsPainel() : ""}
        ${ai.mode === "imagem" ? hint("Use o botão 📷 em cada cena, logo abaixo, para enviar a imagem. Mesmo sem gerar o clipe, a imagem já aparece como fundo com zoom suave, de graça.") : ""}
        ${ai.mode === "inicio_fim" ? hint("Em cada cena, envie a foto do <b>início</b> e a do <b>fim</b> (botões 📷 abaixo). Se quiser, envie também uma foto do <b>meio</b>. Ótimo para antes e depois de obra, reforma ou transformação.") : ""}
        ${ai.mode !== "foto_ia" ? `<div><b style="font-size:13px">2. Modelo</b>
          <div class="grid" style="margin-top:8px">${Object.entries(XAI_MODELS).map(([k, m]) => { const ok = XAI_MODES[ai.mode].models.includes(k); return optCard(ai.model === k, `data-aimodel="${k}" ${ok ? "" : "disabled title=\"Este modelo não faz este modo\""}`, "", m.name + " · " + m.tag, (ok ? m.desc : "Não disponível neste modo.") + " A partir de " + usd(Math.min(...Object.values(m.price))) + "/s."); }).join("")}</div></div>
        <div style="display:flex;gap:18px;flex-wrap:wrap">
          <div><b style="font-size:13px">3. Resolução</b><div class="seg" style="margin-top:8px;display:flex">${["480p", "720p", "1080p"].map(r => { const ok = XAI_MODELS[ai.model].price[r] && !(usaReferencia() && r === "1080p"); return `<button data-aires="${r}" class="${ai.res === r ? "on" : ""}" ${ok ? "" : "disabled style=\"opacity:.4\""}>${r}${XAI_MODELS[ai.model].price[r] ? " · " + usd(XAI_MODELS[ai.model].price[r]) + "/s" : ""}</button>`; }).join("")}</div></div>
          <div><b style="font-size:13px">4. Som do clipe</b><div class="seg" style="margin-top:8px;display:flex">${Object.entries(AUDIO_OPTS).map(([k, n]) => { const ok = ai.mode === "avatar" ? k === "fala" : !(k === "fala" && ai.model === CLASSICO); return `<button data-aiaudio="${k}" class="${ai.audio === k ? "on" : ""}" ${ok ? "" : "disabled style=\"opacity:.4\""}>${n}</button>`; }).join("")}</div></div>
        </div>
        ${ai.audio === "fala" ? `<div><b style="font-size:13px">5. Voz de quem fala no clipe</b><div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px">
          <select id="aiVoice" style="width:auto;flex:1 1 220px" ${XAI_MODELS[ai.model].voices ? "" : "disabled"}><option value="auto" ${ai.voice === "auto" ? "selected" : ""}>Automática (a IA escolhe pela pessoa)</option>${XAI_VOICES.map(v => `<option value="${v}" ${ai.voice === v ? "selected" : ""}>${vozNome(v)}</option>`).join("")}</select>
          ${ai.voice !== "auto" ? `<button class="btn sm" data-ouvir="${ai.voice}">▶ Ouvir</button>` : ""}</div>
          <span class="mon-note">${XAI_MODELS[ai.model].voices ? "Escolher uma voz usa o modo de referência da xAI (até 720p)." : "Para escolher a voz, use o modelo 1.5. No Lite, a IA escolhe a voz sozinha."}</span></div>` : ""}` : hint("Neste modo, use a aba <b>🖼️ Imagens</b> para escolher o modelo, a qualidade e a resolução das imagens.")}
        <div class="hint" style="margin-top:0"><span>💰</span><div>Custo estimado das cenas: <b>${usd(xaiCost())}</b> (${ai.mode === "foto_ia" ? TL.scenes.length + " imagens · " + usd(precoImagem()) + " cada" : TL.scenes.reduce((a, x) => a + clipSeconds(x), 0) + " s de vídeo em " + ai.res + " · " + usd(precoVideo()) + "/s"}). Valores aproximados, cobrados na conta da xAI de quem gera.</div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" id="clipBtn" ${clipsRunning ? "disabled" : ""}>${clipsRunning ? "Gerando com IA…" : (settings.xaiKey ? (ai.mode === "foto_ia" ? "🎨 Gerar imagens de todas as cenas" : "🤖 Gerar clipes de todas as cenas") : "🔑 Colocar a chave do Grok (campo acima)")}</button>${(Object.keys(runtime.clipVideos).length || P.scenes.some(s => s.img)) && !clipsRunning ? `<button class="btn ghost" id="clipClear">Remover fundos de IA</button>` : ""}</div>
        <details class="vis"${P.scenes.some(s => s.clipUrl) ? " open" : ""}><summary style="font-size:13px">✂️ Editar e estender clipes prontos (botões ✏️ e ➕ em cada cena)</summary>
          <div style="display:flex;flex-direction:column;gap:8px;margin-top:8px">
            <label class="f" for="aiEdit">O que mudar no clipe (botão ✏️ · clipes de até 8,7 s)<input id="aiEdit" type="text" placeholder="Ex.: deixe o céu ao entardecer e adicione neve caindo"></label>
            <label class="f" for="extDur">Quanto estender (botão ➕): ${ai.extDur} s<input id="extDur" type="range" min="2" max="10" step="1" value="${ai.extDur}"></label>
            <span class="mon-note">Editar e estender usam o modelo Clássico (cerca de ${usd(XAI_MODELS[CLASSICO].price["480p"])}/s).</span>
          </div></details>
        <div id="clipRows"></div>` : ""}
        ${ai.tab === "imagens" ? `
        <p class="mon-note" style="margin:0">Crie ou melhore a imagem de cada cena. As imagens viram o fundo da cena (com zoom suave, de graça) e também podem ser animadas no modo <b>🖼️ Animar minhas imagens</b> ou <b>🎞️ Início e fim</b>.</p>
        <div><b style="font-size:13px">Modelo de imagem</b><div class="grid" style="margin-top:8px">${Object.entries(XAI_IMG_MODELS).map(([k, m]) => optCard(ai.imgModel === k, `data-imgmodel="${k}"`, "", m.name + " · " + m.tag, "A partir de " + usd(Math.min(...Object.values(m.price.low))) + " por imagem.")).join("")}</div></div>
        <div style="display:flex;gap:18px;flex-wrap:wrap">
          <div><b style="font-size:13px">Qualidade</b><div class="seg" style="margin-top:8px;display:flex">${[["low", "Normal"], ["medium", "Alta"]].map(([q, n]) => `<button data-imgq="${q}" class="${ai.imgQuality === q ? "on" : ""}" ${XAI_IMG_MODELS[ai.imgModel].price[q] ? "" : "disabled style=\"opacity:.4\""}>${n}</button>`).join("")}</div></div>
          <div><b style="font-size:13px">Resolução</b><div class="seg" style="margin-top:8px;display:flex">${["1k", "2k"].map(r => `<button data-imgres="${r}" class="${ai.imgRes === r ? "on" : ""}">${r.toUpperCase()}</button>`).join("")}</div></div>
        </div>
        <label class="f" for="imgEdit">Instrução para ✏️ Editar ou 🧩 Juntar<input id="imgEdit" type="text" placeholder="Ex.: deixe a foto noturna com luzes acesas · coloque o produto na mão da pessoa"></label>
        ${refsPainel()}
        <div class="hint" style="margin-top:0"><span>💰</span><div>Gerar: <b>${usd(precoImagem())}</b> por imagem · Editar: cerca de <b>${usd(XAI_IMG_MODELS["grok-imagine-image-2.0"].price[ai.imgQuality === "medium" ? "medium" : "low"][ai.imgRes] + XAI_IMG_EDIT_EXTRA)}</b> · Juntar: um pouco mais por imagem usada.</div></div>
        ${P.scenes.some(s => s.clipUrl) ? hint("Nas cenas que já têm clipe de vídeo, o clipe continua aparecendo no vídeo. A imagem fica guardada para animar depois ou para usar se você remover o clipe.") : ""}
        <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" id="imgAllBtn" ${clipsRunning ? "disabled" : ""}>${clipsRunning ? "Gerando…" : "🎨 Gerar imagens de todas as cenas"}</button></div>
        <div id="clipRows"></div>` : ""}
        ${ai.tab === "voz" ? `
        <p class="mon-note" style="margin:0">Narração com voz natural da IA, em ${esc(langName())}. Diferente da voz pronta do navegador, <b>esta voz entra no vídeo baixado</b>.</p>
        ${vozIAPainel()}` : ""}
        ${ENV.viewer ? hint("Esta página publicada não consegue falar com a xAI. Use o app no Streamlit ou a versão para computador.", "warn") : ""}
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
function refsPainel() {
  const ai = AI(), max = 6;
  return `<div><b style="font-size:13px">Imagens de referência</b> <span class="mon-note">(produto, lugar, objeto · até ${max})</span>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;align-items:center">
      ${P.presenter.photo ? `<div title="Sua foto (personagem principal)" style="width:56px;height:56px;border-radius:10px;background:center/cover url(${P.presenter.photo});border:2px solid var(--lilac)"></div>` : ""}
      ${ai.refs.map(r => `<div style="position:relative;width:56px;height:56px;border-radius:10px;background:center/cover url(${r.img});border:1px solid var(--line)"><button class="iconbtn" data-refdel="${r.id}" title="Remover" aria-label="Remover referência" style="position:absolute;top:-8px;right:-8px;width:22px;height:22px;background:var(--panel);font-size:11px">✕</button></div>`).join("")}
      ${ai.refs.length < max ? `<label class="btn sm" for="refIn">+ Adicionar referência</label><input id="refIn" type="file" accept="image/*" hidden>` : ""}
    </div></div>`;
}
function renderClipRows() {
  const el = $("#clipRows"); if (!el) return;
  const ai = AI(), tabImg = ai.tab === "imagens";
  el.innerHTML = TL.scenes.map(x => {
    const s = x.s, j = clipJobs[s.id] || (!tabImg && runtime.clipVideos[s.id] ? { status: "ok", msg: "Pronto" } : null);
    const has = !!s.clipUrl, canAct = !clipsRunning && settings.xaiKey;
    const up = (slot, txt, on) => `<label class="btn sm ghost" for="simg-${slot}-${s.id}" title="Enviar imagem">${txt}${on ? " ✓" : ""}</label><input id="simg-${slot}-${s.id}" data-simg="${s.id}" data-slot="${slot}" type="file" accept="image/*" hidden>`;
    let tools = "";
    if (tabImg) {
      tools = up("img", "📷", s.img) +
        (canAct ? `<button class="btn sm ghost" data-imggen="${s.id}" title="Gerar imagem com IA">🎨 Gerar</button>` : "") +
        (canAct && s.img ? `<button class="btn sm ghost" data-imgedit="${s.id}" title="Editar com a instrução acima">✏️ Editar</button>` : "") +
        (canAct && s.img && ai.refs.length ? `<button class="btn sm ghost" data-imgjoin="${s.id}" title="Juntar com as referências">🧩 Juntar</button>` : "") +
        (s.img ? `<button class="btn sm ghost" data-imgdel="${s.id}" title="Remover imagem">✕</button>` : "");
    } else {
      if (ai.mode === "inicio_fim") tools += up("img", "📷 Início", s.img) + up("imgMid", "📷 Meio", s.imgMid) + up("imgEnd", "📷 Fim", s.imgEnd);
      else if (ai.mode === "imagem" || ai.mode === "foto_ia" || s.img) tools += up("img", "📷", s.img);
      if (has) tools += `<a class="btn sm ghost" href="${esc(s.clipUrl)}" target="_blank" rel="noopener" title="Abrir ou baixar o clipe">Abrir</a>`;
      if (canAct) tools += `<button class="btn sm ghost" data-clip="${s.id}">${has || (s.img && s.aiImg && ai.mode === "foto_ia") ? "Refazer" : "Gerar"}</button>`;
      if (canAct && has) tools += `<button class="btn sm ghost" data-clipext="${s.id}" title="Estender o clipe">➕ ${ai.extDur} s</button>` + ((s.clipDur || 0) <= 8.7 ? `<button class="btn sm ghost" data-clipedit="${s.id}" title="Editar com a instrução acima">✏️</button>` : "");
    }
    const thumb = s.img ? `<span style="width:40px;height:40px;border-radius:8px;flex:none;background:center/cover url(${s.img});border:1px solid var(--line)"></span>` : `<span class="pill">${x.i + 1}</span>`;
    const custo = tabImg ? usd(precoImagem()) : (ai.mode === "foto_ia" ? usd(precoImagem()) : clipSeconds(x) + " s · " + usd(custoCena(x)));
    return `<div class="clip-row">${thumb}
      <span style="min-width:0"><span style="display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${x.i + 1}. ${esc(s.title)}</span><small class="mon-note">${custo}${s.clipDur ? " · clipe de " + s.clipDur + " s" : ""}</small>${j && j.status === "err" ? `<br><small style="color:#ff8a7a">${esc(j.msg)}</small>${/crédito/i.test(j.msg) ? ` <a class="btn sm" href="${XAI_CREDITOS}" target="_blank" rel="noopener" style="margin-top:4px">💳 Comprar créditos na xAI</a>` : ""}` : ""}</span>
      <span style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;justify-content:flex-end">${j ? `<span class="pill ${j.status}">${esc(j.status === "run" ? j.msg : j.status === "ok" ? "Pronto" : "Erro")}</span>` : ""}${tools}</span></div>`;
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
  updateFinishBtn();
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
  if (d.clip) { runAI(d.clip); return; }
  if (d.clipext) { runAI(d.clipext, "estender"); return; }
  if (d.clipedit) { runAI(d.clipedit, "editar"); return; }
  if (d.aimode) { AI().mode = d.aimode; save(); renderStep(); return; }
  if (d.aimodel) { AI().model = d.aimodel; save(); renderStep(); return; }
  if (d.aires) { AI().res = d.aires; save(); renderStep(); return; }
  if (d.aiaudio) { AI().audio = d.aiaudio; save(); renderStep(); return; }
  if (d.aitab) { AI().tab = d.aitab; save(); renderStep(); return; }
  if (d.imgmodel) { AI().imgModel = d.imgmodel; save(); renderStep(); return; }
  if (d.imgq) { AI().imgQuality = d.imgq; save(); renderStep(); return; }
  if (d.imgres) { AI().imgRes = d.imgres; save(); renderStep(); return; }
  if (d.imggen) { runAI(d.imggen, "img_gerar"); return; }
  if (d.imgedit) { runAI(d.imgedit, "img_editar"); return; }
  if (d.imgjoin) { runAI(d.imgjoin, "img_juntar"); return; }
  if (d.imgdel) { const s = P.scenes.find(s => s.id === d.imgdel); if (s) { delete s.img; delete s.aiImg; loadSceneImage(s); save(); renderStep(); } return; }
  if (d.refdel) { AI().refs = AI().refs.filter(r => r.id !== d.refdel); save(); renderStep(); return; }
  if (d.ouvir) { ouvirVoz(d.ouvir); return; }
  if (d.traduzir) { traduzirProjeto(d.traduzir); return; }
  if (d.dlfmt !== undefined) { const e = (runtime.exports || [])[+d.dlfmt]; if (e) baixarArquivo(e.blob, nomeArquivo(FMT_SUFIXO[e.fmt], e.ext), e.url); return; }
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
    case "btnPro": openProConfirm(); break;
    case "xaiKeySave": saveXaiKey(); break;
    case "xaiKeyChange": keyBoxOpen = true; renderStep(); setTimeout(() => document.getElementById("xaiKeyIn")?.focus(), 50); break;
    case "xaiKeyCancel": keyBoxOpen = false; renderStep(); break;
    case "proYes": runPro(); break;
    case "proNo": { const b = document.getElementById("proConfirm"); b.hidden = true; b.innerHTML = ""; break; }
    case "proOpts": { const b = document.getElementById("proConfirm"); b.hidden = true; b.innerHTML = ""; step = 7; renderStep(); setTimeout(() => document.getElementById("clipBtn")?.scrollIntoView({ behavior: "smooth", block: "center" }), 50); break; }
    case "btnFinish":
      if (exporting) break;
      if (runtime.exportUrl) { downloadExport(); break; }
      step = 7; renderStep(); $("#stepArea").scrollIntoView({ behavior: "smooth", block: "start" });
      exportVideo(); break;
    case "expStop": stopExport(); break;
    case "dlBtn": downloadExport(); break;
    case "clipBtn": runAI(); break;
    case "imgAllBtn": runAI(null, "img_gerar"); break;
    case "ttsGen": gerarNarracaoIA(); break;
    case "ttsTest": ouvirVoz(AI().ttsVoice); break;
    case "clipClear": Object.keys(runtime.clipVideos).forEach(k => delete runtime.clipVideos[k]); P.scenes.forEach(s => { delete s.clipUrl; delete s.clipDur; delete s.img; delete s.imgMid; delete s.imgEnd; delete s.aiImg; delete bgImgs[s.id]; }); Object.keys(clipJobs).forEach(k => delete clipJobs[k]); save(); renderStep(); break;
    case "btnSettings": openSettings(); break;
    case "btnProjects": openProjects(); break;
    case "btnKit": openKit(); break;
    case "expAll": exportAllFormats(); break;
    case "postGen": gerarPost(); break;
    case "postCopy": copiarPost(); break;
  }
});
document.addEventListener("input", e => {
  const t = e.target;
  if (t.dataset.f) { const card = t.closest(".scene"); const s = P.scenes.find(s => s.id === card.dataset.sid); if (s) { s[t.dataset.f] = t.value; save(); timelineDirty = true; if (!player.playing) { buildTimeline(); renderFrame(player.t); } const meta = card.querySelector(".meta"); const i = P.scenes.indexOf(s); if (meta && TL.scenes[i]) meta.textContent = `Cena ${i + 1} · ${TL.scenes[i].dur.toFixed(1)} s · ${words(s.text)} palavras`; } return; }
  if (t.id === "pname") { P.name = t.value; $("#projName").textContent = "· " + (P.name || "Sem nome"); save(); }
  if (t.id === "brand") { P.brand = t.value; save(); if (!player.playing) renderFrame(player.t); }
  if (t.id === "topic") { P.topic = t.value; save(); }
  if (t.id === "styleDesc") { P.styleDesc = t.value; save(); }
  if (t.id === "ttsSpeed") { AI().ttsSpeed = +t.value; save(); const l = t.closest("label"); if (l) l.firstChild.textContent = `Velocidade da fala: ${(+t.value).toFixed(1)}×`; return; }
  if (t.id === "extDur") { AI().extDur = +t.value; save(); const l = t.closest("label"); if (l) l.firstChild.textContent = `Quanto estender (botão ➕): ${t.value} s`; renderClipRows(); return; }
  if (t.id === "rate") { P.voice.rate = +t.value; save(); const l = t.closest("label"); if (l) l.firstChild.textContent = `Velocidade: ${(+t.value).toFixed(1)}×`; }
});
document.addEventListener("change", async e => {
  const t = e.target;
  if (t.id === "voiceSel") { P.voice.voiceName = t.value; save(); }
  if (t.dataset.simg && t.files[0]) {
    const s = P.scenes.find(s => s.id === t.dataset.simg), slot = ["img", "imgMid", "imgEnd"].includes(t.dataset.slot) ? t.dataset.slot : "img";
    if (s) { try { s[slot] = await fileToSmallDataURL(t.files[0], 1024); if (slot === "img") { s.aiImg = false; loadSceneImage(s); } save(); renderStep(); toast({ img: "Imagem da cena adicionada.", imgMid: "Foto do meio adicionada.", imgEnd: "Foto do fim adicionada." }[slot]); } catch (err) { toast("Não consegui abrir essa imagem."); } }
  }
  if (t.id === "bkIn" && t.files[0]) { restaurarBackup(t.files[0]); return; }
  if (t.id === "refIn" && t.files[0]) { try { const img = await fileToSmallDataURL(t.files[0], 1024); AI().refs.push({ id: uid(), img, label: "reference" }); save(); renderStep(); toast("Referência adicionada."); } catch (err) { toast("Não consegui abrir essa imagem."); } }
  if (t.id === "ttsVoice") { AI().ttsVoice = t.value; save(); renderStep(); }
  if (t.id === "aiVoice") { AI().voice = t.value; save(); renderStep(); }
  if (t.id === "photoIn" && t.files[0]) { try { P.presenter.photo = await fileToSmallDataURL(t.files[0]); loadPhoto(); save(); renderStep(); } catch (err) { toast("Não consegui abrir essa imagem."); } }
  if (t.id === "audIn" && t.files[0]) { setNarration(t.files[0], t.files[0].name); P.voice.mode = "upload"; save(); toast("Áudio carregado."); }
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeLayer();
  if (e.key === "Enter" && e.target.id === "topic") { e.preventDefault(); $("#aiBtn")?.click(); }
  if (e.key === "Enter" && e.target.id === "xaiKeyIn") { e.preventDefault(); saveXaiKey(); }
});

/* ============ gaveta de projetos e configurações ============ */
function closeLayer() { $("#layer").innerHTML = ""; }
function newProject() {
  pause(); clearExport();
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
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px"><button class="btn sm" id="bkSave">💾 Baixar backup</button><label class="btn sm" for="bkIn">📂 Restaurar backup</label><input id="bkIn" type="file" accept=".json,application/json" hidden></div>
    <p class="mon-note">Os projetos ficam salvos neste navegador. Baixe um <b>backup</b> de vez em quando para guardar os seus vídeos e a sua marca, ou para levar para outro aparelho (lá, use <b>Restaurar backup</b>).</p>
  </div></div>`;
  $("#scrim").onclick = ev => {
    if (ev.target.id === "scrim" || ev.target.id === "closeL") return closeLayer();
    const b = ev.target.closest("button"); if (!b) return; const d = b.dataset;
    if (b.id === "newP") return newProject();
    if (b.id === "bkSave") return baixarBackup();
    if (d.popen) { pause(); clearExport(); P = projects.find(p => p.id === d.popen); player.t = 0; Object.keys(runtime.clipVideos).forEach(k => delete runtime.clipVideos[k]); P.scenes.forEach(s => s.clipUrl && loadClip(s.id, s.clipUrl)); P.scenes.forEach(loadSceneImage); loadPhoto(); save(); closeLayer(); renderStep(); return; }
    if (d.pdup) { const src = projects.find(p => p.id === d.pdup); const c = JSON.parse(JSON.stringify(src)); c.id = uid(); c.name = src.name + " (cópia)"; c.scenes.forEach(s => s.id = uid()); projects.unshift(c); save(); openProjects(); return; }
    if (d.pdel) { pendingDelete = d.pdel; openProjects(); return; }
    if (d.pcancel) { pendingDelete = null; openProjects(); return; }
    if (d.pdel2) { projects = projects.filter(p => p.id !== d.pdel2); pendingDelete = null; if (!projects.length) projects = [sampleProject()]; if (!projects.find(p => p.id === P.id)) { P = projects[0]; loadPhoto(); renderStep(); } save(); openProjects(); }
  };
}
function openSettings() {
  const L = $("#layer");
  if (ENV.hostAI) {
    L.innerHTML = `<div class="scrim" id="scrim"><div class="sheet" role="dialog" aria-label="Chaves de IA">
      <div style="display:flex;justify-content:space-between;align-items:center"><h2>Chaves de IA</h2><button type="button" class="btn sm ghost" id="closeL">Fechar</button></div>
      <ul class="checklist"><li class="${settings.xaiKey ? "ok" : ""}"><span class="s">${settings.xaiKey ? "✓" : "–"}</span>Chave do Grok Imagine (xAI): ${settings.xaiKey ? "conectada (roteiros, chat, vídeos, imagens e voz)" : "ainda não colocada"}</li></ul>
      <p class="mon-note">Para trocar a sua chave, use o quadro abaixo.</p>
      ${keyPanel()}
    </div></div>`;
    $("#scrim").onclick = ev => { if (ev.target.id === "scrim" || ev.target.id === "closeL") closeLayer(); };
    return;
  }
  L.innerHTML = `<div class="scrim" id="scrim"><form class="sheet" id="setForm" role="dialog" aria-label="Chaves de IA">
    <div style="display:flex;justify-content:space-between;align-items:center"><h2>Chaves de IA</h2><button type="button" class="btn sm ghost" id="closeL">Fechar</button></div>
    ${ENV.viewer ? hint("Você está na <b>página publicada</b>. Aqui o roteiro é escrito pela IA do Claude e as chaves abaixo não funcionam, porque a página não pode acessar outros sites. Use as chaves na <b>versão para computador</b> (arquivo .html que te mandei no chat).", "warn") : ""}
    ${ENV.hostAI ? hint("Neste app, a chave da Groq vai no campo <b>Sua chave da Groq</b>, no topo da página. Aqui você só precisa preencher a chave do Grok, se quiser clipes de IA.") : ""}
    <h3 style="margin:8px 0 0;font-family:var(--display)">Groq · roteiros</h3>
    <label class="f" for="gk">Chave da Groq (começa com gsk_)<input id="gk" type="password" autocomplete="off" value="${esc(settings.groqKey)}" placeholder="gsk_..."></label>
    <label class="f" for="gm">Modelo<input id="gm" type="text" value="${esc(settings.groqModel)}"></label>
    <span class="mon-note">Crie a chave em console.groq.com → API Keys. Modelos atuais: openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b.</span>
    <h3 style="margin:14px 0 0;font-family:var(--display)">xAI · clipes animados (Grok Imagine)</h3>
    <label class="f" for="xk">Chave do Grok (começa com grok_)<input id="xk" type="password" autocomplete="off" value="${esc(settings.xaiKey)}" placeholder="grok_..."></label>
    <span class="mon-note">Crie a chave em console.x.ai. O modelo, a resolução e o custo você escolhe no passo Gerar.</span>
    <div style="display:flex;gap:8px;margin-top:8px"><button class="btn primary" type="submit">Salvar</button><button class="btn ghost" type="button" id="clrKeys">Apagar chaves</button></div>
    <p class="mon-note">As chaves ficam salvas só neste navegador, neste computador. Nunca compartilhe suas chaves.</p>
  </form></div>`;
  $("#scrim").onclick = ev => { if (ev.target.id === "scrim" || ev.target.id === "closeL") closeLayer(); if (ev.target.id === "clrKeys") { settings.groqKey = ""; settings.xaiKey = ""; saveSettings(); updateEnvBadge(); closeLayer(); renderStep(); toast("Chaves apagadas."); } };
  $("#setForm").onsubmit = ev => {
    ev.preventDefault();
    settings.groqKey = $("#gk").value.trim(); settings.groqModel = $("#gm").value.trim() || "openai/gpt-oss-120b";
    settings.xaiKey = $("#xk").value.trim();
    saveSettings(); updateEnvBadge(); closeLayer(); renderStep(); toast("Chaves salvas.");
  };
}

/* ============ recursos de associado ============ */
/* ---- Kit da marca: logo, cores e contatos cadastrados uma vez, usados em todos os vídeos ---- */
const KIT_DEF = { ativo: true, nome: "", slogan: "", logo: "", cor1: "#ff5a36", cor2: "#1a1724", insta: "", whats: "", site: "", endereco: "", marcaDagua: true, cenaFinal: true, qr: true, durFinal: 4 };
let KIT = Object.assign({}, KIT_DEF, store.get("evs.kit", {}));
const kitLogo = new Image(); let kitLogoOk = false;
function loadKitLogo() { kitLogoOk = false; if (KIT.logo) { kitLogo.onload = () => { kitLogoOk = true; if (!player.playing) renderFrame(player.t); }; kitLogo.src = KIT.logo; } }
function saveKit() { if (!store.set("evs.kit", KIT)) toast("Não consegui salvar a marca no navegador. Tente um logo menor."); loadKitLogo(); timelineDirty = true; if (!player.playing) renderFrame(player.t); }
function kitTemFinal() { return KIT.ativo && KIT.cenaFinal && !!(KIT.nome || KIT.whats || KIT.insta || KIT.site || KIT.logo); }
function whatsLink() { const d = (KIT.whats || "").replace(/\D/g, ""); if (d.length < 8) return ""; return "https://wa.me/" + (d.length <= 11 ? "55" + d : d); }
function qrAlvo() { return whatsLink() || (KIT.site ? (/^https?:\/\//i.test(KIT.site) ? KIT.site : "https://" + KIT.site) : (KIT.insta ? "https://instagram.com/" + KIT.insta.replace(/^@/, "") : "")); }
let qrCache = { txt: "", canvas: null };
function qrCanvas(txt) {
  if (!txt || typeof qrcode !== "function") return null;
  if (qrCache.txt === txt) return qrCache.canvas;
  try {
    const q = qrcode(0, "M"); q.addData(txt); q.make();
    const n = q.getModuleCount(), mg = 3, px = 8, c = document.createElement("canvas");
    c.width = c.height = (n + mg * 2) * px;
    const g = c.getContext("2d"); g.fillStyle = "#fff"; g.fillRect(0, 0, c.width, c.height); g.fillStyle = "#000";
    for (let r = 0; r < n; r++) for (let k = 0; k < n; k++) if (q.isDark(r, k)) g.fillRect((k + mg) * px, (r + mg) * px, px, px);
    qrCache = { txt, canvas: c }; return c;
  } catch (e) { return null; }
}
function corTexto(hex) {
  let c = String(hex || "#000").replace("#", ""); if (c.length === 3) c = c.split("").map(x => x + x).join("");
  const n = parseInt(c, 16) || 0, r = n >> 16 & 255, g = n >> 8 & 255, b = n & 255;
  return (0.299 * r + 0.587 * g + 0.114 * b) > 150 ? "#14101f" : "#ffffff";
}
function addEndCard() {
  TL.end = null;
  if (!kitTemFinal()) return;
  const d = clamp(KIT.durFinal || 4, 3, 6);
  TL.end = { final: true, s: { id: "__fim__", title: "Cena final", text: "" }, i: TL.scenes.length, start: TL.total, dur: d };
  TL.total += d;
}
function allScenes() { return TL.end ? [...TL.scenes, TL.end] : TL.scenes; }
function drawAny(x, T, W, H, a) { if (x.final) drawEndCard(x, T, W, H, a); else drawScene(x, T, W, H, a); }
// logo e @ no canto de todas as cenas
function drawMarca(st, key, fg, alpha, W, H, m) {
  const usaKit = KIT.ativo && KIT.marcaDagua;
  const txt = usaKit ? (KIT.insta ? (KIT.insta.startsWith("@") ? KIT.insta : "@" + KIT.insta) : (KIT.nome || P.brand)) : P.brand;
  const y0 = m * 0.05 + (key === "cinema" ? H * 0.1 : 0);
  let x0 = m * 0.06;
  ctx.save(); ctx.globalAlpha = alpha * 0.92;
  if (usaKit && kitLogoOk) { const h = m * 0.075, w = Math.min(h * kitLogo.width / kitLogo.height, m * 0.3); ctx.drawImage(kitLogo, x0, y0 - h * 0.2, w, h); x0 += w + m * 0.02; }
  if (txt) { ctx.font = font(st.sub, m * 0.032); ctx.fillStyle = fg; ctx.textAlign = "left"; ctx.textBaseline = "top"; ctx.shadowColor = "rgba(0,0,0,.35)"; ctx.shadowBlur = 6; ctx.fillText(txt, x0, y0); }
  ctx.restore();
}
// cena final de contato, com QR code que abre o WhatsApp (ou o site / Instagram)
function drawEndCard(x, T, W, H, alpha) {
  const m = Math.min(W, H), lt = T - x.start, vertical = H > W, c1 = KIT.cor1 || "#ff5a36", c2 = KIT.cor2 || "#1a1724", fg = corTexto(c2);
  ctx.save(); ctx.globalAlpha = alpha;
  ctx.fillStyle = c2; ctx.fillRect(0, 0, W, H);
  ctx.globalAlpha = alpha * 0.2; ctx.fillStyle = c1;
  ctx.beginPath(); ctx.arc(W * 0.92, H * 0.08, m * 0.36 * (1 + Math.sin(T * 1.2) * 0.03), 0, 7); ctx.fill();
  ctx.beginPath(); ctx.arc(W * 0.06, H * 0.95, m * 0.3, 0, 7); ctx.fill();
  ctx.globalAlpha = alpha;
  const qr = KIT.qr ? qrCanvas(qrAlvo()) : null;
  const cx = vertical ? W / 2 : (qr ? W * 0.36 : W / 2), colW = vertical ? W * 0.84 : (qr ? W * 0.56 : W * 0.8);
  let y = vertical ? H * 0.14 : H * 0.14;
  ctx.textAlign = "center"; ctx.textBaseline = "top";
  const pop = easeBack(lt / 0.5);
  if (kitLogoOk) { const h = m * 0.2, w = Math.min(h * kitLogo.width / kitLogo.height, colW); ctx.save(); ctx.translate(cx, y + h / 2); ctx.scale(pop, pop); ctx.drawImage(kitLogo, -w / 2, -h / 2, w, h); ctx.restore(); y += h + m * 0.04; }
  const nome = KIT.nome || P.brand || "";
  if (nome) { const tpl = '800 {s}px "Bricolage Grotesque"', fit = fitText(nome, tpl, colW, 2, m * 0.085, m * 0.045); ctx.font = font(tpl, fit.size); ctx.fillStyle = fg; fit.lines.forEach((l, i) => ctx.fillText(l, cx, y + i * fit.size * 1.05)); y += fit.lines.length * fit.size * 1.05 + m * 0.015; }
  if (KIT.slogan) { const tpl = '500 {s}px "Figtree"', fit = fitText(KIT.slogan, tpl, colW, 2, m * 0.04, m * 0.026); ctx.font = font(tpl, fit.size); ctx.fillStyle = fg; ctx.globalAlpha = alpha * 0.85; fit.lines.forEach((l, i) => ctx.fillText(l, cx, y + i * fit.size * 1.25)); ctx.globalAlpha = alpha; y += fit.lines.length * fit.size * 1.25 + m * 0.03; }
  const linhas = [KIT.whats && "WhatsApp " + KIT.whats, KIT.insta && (KIT.insta.startsWith("@") ? KIT.insta : "@" + KIT.insta), KIT.site, KIT.endereco].filter(Boolean);
  const fs = m * 0.034; ctx.font = font('700 {s}px "Figtree"', fs);
  linhas.forEach((l, i) => {
    const p = easeOut((lt - 0.25 - i * 0.12) / 0.4), tw = Math.min(ctx.measureText(l).width + fs * 1.6, colW);
    ctx.globalAlpha = alpha * p; ctx.fillStyle = c1; rr(cx - tw / 2, y, tw, fs * 1.7, fs * 0.85); ctx.fill();
    ctx.fillStyle = corTexto(c1); ctx.fillText(l, cx, y + fs * 0.33, tw - fs); y += fs * 2.1;
  });
  ctx.globalAlpha = alpha;
  if (qr) {
    const qs = vertical ? Math.min(m * 0.42, H - y - m * 0.16) : Math.min(m * 0.5, W * 0.26);
    if (qs > m * 0.14) {
      const qx = vertical ? W / 2 - qs / 2 : W * 0.7, qy = vertical ? y + m * 0.03 : H / 2 - qs / 2 - m * 0.03;
      ctx.globalAlpha = alpha * easeOut((lt - 0.5) / 0.5);
      ctx.fillStyle = "#ffffff"; rr(qx - m * 0.02, qy - m * 0.02, qs + m * 0.04, qs + m * 0.04, m * 0.03); ctx.fill();
      ctx.imageSmoothingEnabled = false; ctx.drawImage(qr, qx, qy, qs, qs); ctx.imageSmoothingEnabled = true;
      ctx.font = font('600 {s}px "Figtree"', m * 0.028); ctx.fillStyle = fg; ctx.textAlign = "center";
      ctx.fillText(whatsLink() ? "Aponte a câmera e fale no WhatsApp" : "Aponte a câmera do celular", qx + qs / 2, qy + qs + m * 0.035);
    }
  }
  ctx.restore();
}
function filePng(file, max = 600) {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => { const im = new Image(); im.onload = () => { const k = Math.min(1, max / Math.max(im.width, im.height)); const c = document.createElement("canvas"); c.width = Math.round(im.width * k); c.height = Math.round(im.height * k); c.getContext("2d").drawImage(im, 0, 0, c.width, c.height); res(c.toDataURL("image/png")); }; im.onerror = rej; im.src = r.result; };
    r.onerror = rej; r.readAsDataURL(file);
  });
}
function lerKitDoForm() {
  const v = id => (document.getElementById(id)?.value || "").trim(), c = id => !!document.getElementById(id)?.checked;
  Object.assign(KIT, { ativo: c("kAtivo"), nome: v("kNome"), slogan: v("kSlogan"), cor1: v("kCor1") || KIT.cor1, cor2: v("kCor2") || KIT.cor2, whats: v("kWhats"), insta: v("kInsta"), site: v("kSite"), endereco: v("kEnd"), marcaDagua: c("kMarca"), cenaFinal: c("kFinal"), qr: c("kQr"), durFinal: +(document.getElementById("kDur")?.value || 4) });
}
function openKit() {
  const L = $("#layer"), k = KIT;
  const chk = (id, on, txt) => `<label style="display:flex;gap:8px;align-items:center;font-size:14px"><input type="checkbox" id="${id}" ${on ? "checked" : ""}> ${txt}</label>`;
  L.innerHTML = `<div class="scrim" id="scrim"><form class="sheet" id="kitForm" role="dialog" aria-label="Minha marca">
    <div style="display:flex;justify-content:space-between;align-items:center"><h2>🎨 Minha marca</h2><button type="button" class="btn sm ghost" id="closeL">Fechar</button></div>
    <p class="mon-note" style="font-size:14px">Cadastre uma vez. Todos os seus vídeos saem com o seu logo, as suas cores e uma <b>cena final de contato com QR code</b>.</p>
    ${chk("kAtivo", k.ativo, "<b>Usar a minha marca nos vídeos</b>")}
    <label class="f" for="kNome">Nome do negócio<input id="kNome" type="text" maxlength="60" value="${esc(k.nome)}" placeholder="Ex.: HE Projeto Civil"></label>
    <label class="f" for="kSlogan">Frase de efeito (opcional)<input id="kSlogan" type="text" maxlength="80" value="${esc(k.slogan)}" placeholder="Ex.: Do projeto à chave na mão"></label>
    <div class="photo-drop"><div class="ph" style="border-radius:12px;${k.logo ? `background:#fff center/contain no-repeat url(${k.logo});border-style:solid` : ""}">${k.logo ? "" : "sem logo"}</div>
      <div style="display:flex;flex-direction:column;gap:6px"><label class="btn" for="kLogo">Escolher logo</label><input id="kLogo" type="file" accept="image/*" hidden>${k.logo ? `<button type="button" class="btn ghost sm" id="kLogoDel">Remover logo</button>` : ""}<span class="mon-note">PNG com fundo transparente fica melhor.</span></div></div>
    <div style="display:flex;gap:12px;flex-wrap:wrap"><label class="f" for="kCor1">Cor principal<input id="kCor1" type="color" value="${esc(k.cor1)}" style="width:90px;height:40px;padding:2px"></label><label class="f" for="kCor2">Fundo da cena final<input id="kCor2" type="color" value="${esc(k.cor2)}" style="width:90px;height:40px;padding:2px"></label></div>
    <label class="f" for="kWhats">WhatsApp (vira o QR code)<input id="kWhats" type="text" inputmode="tel" value="${esc(k.whats)}" placeholder="(19) 99999-0000"></label>
    <label class="f" for="kInsta">Instagram<input id="kInsta" type="text" value="${esc(k.insta)}" placeholder="@seuperfil"></label>
    <label class="f" for="kSite">Site (opcional)<input id="kSite" type="text" value="${esc(k.site)}" placeholder="www.seusite.com.br"></label>
    <label class="f" for="kEnd">Endereço (opcional)<input id="kEnd" type="text" value="${esc(k.endereco)}" placeholder="Rua, número, bairro"></label>
    ${chk("kMarca", k.marcaDagua, "Mostrar o logo e o @ no canto dos vídeos")}
    ${chk("kFinal", k.cenaFinal, "Cena final de contato no fim de todo vídeo")}
    ${chk("kQr", k.qr, "QR code na cena final (abre o seu WhatsApp)")}
    <label class="f" for="kDur">Duração da cena final: <span id="kDurLbl">${k.durFinal}</span> s<input id="kDur" type="range" min="3" max="6" step="1" value="${k.durFinal}"></label>
    <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" type="submit">Salvar minha marca</button><button type="button" class="btn" id="kVer">👀 Ver a cena final</button></div>
    <p class="mon-note">A marca fica salva neste navegador e entra no backup (Meus vídeos → Baixar backup).</p>
  </form></div>`;
  $("#scrim").onclick = ev => {
    if (ev.target.id === "scrim" || ev.target.id === "closeL") return closeLayer();
    if (ev.target.id === "kLogoDel") { lerKitDoForm(); KIT.logo = ""; saveKit(); openKit(); }
    if (ev.target.id === "kVer") { lerKitDoForm(); saveKit(); closeLayer(); buildTimeline(); if (TL.end) { pause(); seek(TL.end.start + 0.9); } else toast("Preencha o nome, o WhatsApp ou o logo e deixe a cena final ligada."); }
  };
  $("#kLogo").onchange = async e => { const f = e.target.files[0]; if (!f) return; try { lerKitDoForm(); KIT.logo = await filePng(f); saveKit(); openKit(); toast("Logo adicionado."); } catch (err) { toast("Não consegui abrir essa imagem."); } };
  $("#kDur").oninput = e => { $("#kDurLbl").textContent = e.target.value; };
  $("#kitForm").onsubmit = ev => { ev.preventDefault(); lerKitDoForm(); saveKit(); closeLayer(); renderStep(); toast(kitTemFinal() ? "Marca salva! Os vídeos já saem com a sua identidade." : "Marca salva."); };
}
/* ---- IA de texto: Groq pelo servidor (hub), Claude (página publicada) ou Groq direto (computador) ---- */
async function aiJSON(prompt) {
  if (ENV.ponte) {
    if (!BR.ok) { bridgePing(); throw new Error("A conexão com o servidor ainda não ficou pronta. Espere alguns segundos e tente de novo."); }
    const r = await bridgeCall("GROQ", "json", { prompt });
    if (!r.ok) throw new Error(r.error || "A IA não respondeu. Tente de novo.");
    return r.json || {};
  }
  if (ENV.sample) return await ENV.sample.json(prompt);
  if (settings.groqKey) return await groqChat(prompt);
  throw new Error("Nenhuma IA de texto conectada. Coloque a chave da Groq em Chaves de IA.");
}
/* ---- Texto do post: legenda, chamada e hashtags para copiar ---- */
let postBusy = false;
function normPost(p) { if (!p || typeof p !== "object") return null; return { legenda: String(p.legenda || "").trim(), cta: String(p.cta || "").trim(), hashtags: (Array.isArray(p.hashtags) ? p.hashtags : String(p.hashtags || "").split(/[\s,]+/)).map(h => String(h).replace(/^#/, "").replace(/\s+/g, "")).filter(Boolean).slice(0, 15) }; }
function postTexto(p) { if (!p) return ""; return [p.legenda, p.cta, (p.hashtags || []).map(h => "#" + h).join(" ")].filter(Boolean).join("\n\n").trim(); }
function contatosTexto() { return [KIT.nome, KIT.whats && "WhatsApp " + KIT.whats, KIT.insta, KIT.site, KIT.endereco].filter(Boolean).join(" · "); }
async function gerarPost() {
  if (postBusy) return;
  postBusy = true; renderStep();
  try {
    const roteiro = P.scenes.map((s, i) => `${i + 1}. ${s.title}: ${s.text}`).join("\n");
    const j = await aiJSON(`Você é social media de pequenos negócios. Escreva o texto para postar junto com este vídeo no Instagram/TikTok, em ${langName()}.
Negócio e contatos reais: ${contatosTexto() || P.styleDesc || "não informado"}
Roteiro do vídeo:
${roteiro}
Regras: "legenda" com 2 a 4 frases e emojis moderados; "cta" curta usando o contato real, se houver; "hashtags" com 8 a 12 itens sem #. NÃO invente preços, telefones ou endereços.
Responda somente com JSON: {"legenda":"...","cta":"...","hashtags":["..."]}`);
    const p = normPost(j.post || j);
    if (!p || !p.legenda) throw new Error("A IA não devolveu o texto. Tente de novo.");
    P.post = p; save(); toast("Texto do post pronto!");
  } catch (e) { toast(e.message || String(e), 6000); }
  finally { postBusy = false; renderStep(); }
}
function copiarPost() {
  const t = postTexto(P.post); if (!t) return;
  const ok = () => toast("Texto copiado! É só colar no Instagram ou no TikTok.");
  const fallback = () => { const ta = document.getElementById("postTxt"); if (ta) { ta.focus(); ta.select(); try { document.execCommand("copy"); ok(); return; } catch (e) {} } toast("Selecione o texto e copie com Ctrl+C."); };
  try { navigator.clipboard.writeText(t).then(ok, fallback); } catch (e) { fallback(); }
}
function postCard() {
  return `<div class="gen-card" style="margin-top:16px">
    <h3>📝 Texto do post</h3>
    ${P.post ? `<textarea id="postTxt" rows="7" readonly style="font-size:14px">${esc(postTexto(P.post))}</textarea>
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary sm" id="postCopy">📋 Copiar texto</button><button class="btn sm" id="postGen" ${postBusy ? "disabled" : ""}>${postBusy ? "Escrevendo…" : "✨ Gerar de novo"}</button></div>`
    : `<p class="mon-note" style="margin:0">Legenda, chamada para ação e hashtags para postar junto com este vídeo.</p>
      <button class="btn" id="postGen" style="align-self:flex-start" ${postBusy ? "disabled" : ""}>${postBusy ? "Escrevendo…" : "✨ Gerar texto do post com IA"}</button>`}
  </div>`;
}
/* ---- Um vídeo, três formatos ---- */
let multiRunning = false;
const FMT_SUFIXO = { "9:16": "reels-stories", "1:1": "feed", "16:9": "youtube" };
async function exportAllFormats() {
  if (exporting || multiRunning) return;
  const orig = P.format;
  (runtime.exports || []).forEach(e => { try { URL.revokeObjectURL(e.url); } catch (x) {} });
  runtime.exports = []; multiRunning = true;
  for (const f of ["9:16", "1:1", "16:9"]) {
    P.format = f; timelineDirty = true; setCanvasSize(); renderStep();
    toast(`Gravando o formato ${f} (${runtime.exports.length + 1} de 3)…`, 3000);
    const r = await exportVideo({ multi: true });
    if (!r) break;
    runtime.exports.push(Object.assign({ fmt: f }, r));
  }
  P.format = orig; timelineDirty = true; multiRunning = false; setCanvasSize(); renderStep();
  if (runtime.exports.length === 3) toast("Os 3 formatos estão prontos! Baixe cada um abaixo.", 5000);
}
function nomeArquivo(sufixo, ext) { return ((P.name || "video").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\w]+/g, "-").replace(/^-|-$/g, "").toLowerCase() || "video") + (sufixo ? "-" + sufixo : "") + "." + ext; }
async function baixarArquivo(blob, nome, url) {
  if (ENV.downloads) {
    try { await ENV.downloads.save({ filename: nome, data: blob }); toast("Arquivo salvo."); }
    catch (e) { if (e?.code === "declined") toast("Download cancelado."); else if (e?.code === "rate_limited") toast("Já existe um download aguardando. Tente em instantes."); else toast("Não foi possível baixar aqui. Abra a versão para computador."); }
    return;
  }
  if (ENV.viewer) { toast("Download indisponível nesta visualização."); return; }
  const u = url || URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = u; a.download = nome; document.body.appendChild(a); a.click(); a.remove();
  if (!url) setTimeout(() => URL.revokeObjectURL(u), 4000);
}
/* ---- Backup: guarda todos os vídeos e a marca num arquivo ---- */
function baixarBackup() {
  const dados = { app: "estudio-de-videos", versao: 1, salvoEm: new Date().toISOString(), kit: KIT, projetos: projects };
  const blob = new Blob([JSON.stringify(dados)], { type: "application/json" });
  baixarArquivo(blob, "backup-estudio-de-videos-" + new Date().toISOString().slice(0, 10) + ".json");
}
async function restaurarBackup(file) {
  try {
    const d = JSON.parse(await file.text());
    if (!d || d.app !== "estudio-de-videos" || !Array.isArray(d.projetos)) throw new Error("Este arquivo não é um backup do Estúdio de Vídeos.");
    let n = 0;
    d.projetos.filter(p => p && p.id && Array.isArray(p.scenes)).forEach(p => { const i = projects.findIndex(x => x.id === p.id); if (i >= 0) projects[i] = p; else projects.push(p); n++; });
    if (d.kit && typeof d.kit === "object") { KIT = Object.assign({}, KIT_DEF, d.kit); saveKit(); }
    P = projects.find(p => p.id === P.id) || projects[0];
    P.scenes.forEach(loadSceneImage); loadPhoto(); save(); closeLayer(); renderStep();
    toast(`Backup restaurado: ${n} ${n === 1 ? "vídeo" : "vídeos"}${d.kit ? " e a sua marca" : ""}.`, 5000);
  } catch (e) { toast(e.message && e.message.includes("backup") ? e.message : "Não consegui ler esse arquivo de backup.", 6000); }
}
/* ---- Mesmo vídeo em outros idiomas ---- */
let traduzindo = "";
const IDIOMA_ALVO = { "pt-BR": ["português do Brasil", "Português", "🇧🇷"], "en-US": ["inglês (Estados Unidos)", "Inglês", "🇺🇸"], "es-ES": ["espanhol", "Espanhol", "🇪🇸"] };
async function traduzirProjeto(lang) {
  if (traduzindo || !IDIOMA_ALVO[lang]) return;
  traduzindo = lang; renderStep();
  try {
    const j = await aiJSON(`Traduza para ${IDIOMA_ALVO[lang][0]} o roteiro de um vídeo curto e o texto do post.
Mantenha o tom e adapte expressões para soar natural. NÃO traduza nomes de marcas, telefones, @ e sites. Títulos curtos (até 6 palavras).
Roteiro (${P.scenes.length} cenas): ${JSON.stringify(P.scenes.map(s => ({ title: s.title, text: s.text })))}
Post: ${JSON.stringify(P.post || null)}
Responda somente com JSON, com exatamente ${P.scenes.length} cenas na mesma ordem: {"scenes":[{"title":"...","text":"..."}],"post":{"legenda":"...","cta":"...","hashtags":["..."]}}`);
    const sc = Array.isArray(j.scenes) ? j.scenes : [];
    if (sc.length !== P.scenes.length) throw new Error("A tradução veio incompleta. Tente de novo.");
    const c = JSON.parse(JSON.stringify(P));
    c.id = uid(); c.name = `${P.name || "Vídeo"} (${IDIOMA_ALVO[lang][1]})`; c.updated = Date.now();
    c.voice = Object.assign({}, P.voice, { lang, voiceName: "" });
    c.scenes.forEach((s, i) => { s.title = String(sc[i].title || s.title).slice(0, 80); s.text = String(sc[i].text || ""); }); // mantém as mesmas cenas e clipes
    c.post = normPost(j.post) || null;
    projects.unshift(c); P = c; save();
    AI().tab = "voz";
    toast(`Versão em ${IDIOMA_ALVO[lang][1].toLowerCase()} criada! Gere a narração na aba 🎙️ Voz da IA para ouvir no novo idioma.`, 7000);
  } catch (e) { toast(e.message || String(e), 6000); }
  finally { traduzindo = ""; renderStep(); }
}
function idiomasCard() {
  return `<div class="gen-card" style="margin-top:16px">
    <h3>🌎 Este vídeo em outros idiomas</h3>
    <p class="mon-note" style="margin:0">A IA traduz o roteiro e o texto do post e cria uma cópia deste vídeo, com as mesmas cenas e clipes. Depois, gere a narração na aba <b>🎙️ Voz da IA</b> para ouvir no novo idioma.</p>
    <div style="display:flex;gap:8px;flex-wrap:wrap">${Object.entries(IDIOMA_ALVO).filter(([k]) => k !== P.voice.lang).map(([k, v]) => `<button class="btn" data-traduzir="${k}" ${traduzindo ? "disabled" : ""}>${traduzindo === k ? "Traduzindo…" : `${v[2]} Criar versão em ${v[1].toLowerCase()}`}</button>`).join("")}</div>
  </div>`;
}

/* ============ início ============ */
// roteiro entregue pelo servidor (ex.: app no Streamlit, que guarda a chave da Groq em segredo)
const INJ = window.__EVS_INJECT__;
if (INJ && INJ.engine) ENV.hostAI = INJ.engine;
if (INJ && INJ.ponte) { ENV.ponte = true; if (settings.xaiKey !== "__servidor__") settings.xaiKey = ""; } // no hub, a chave do Grok fica só no servidor
if (INJ && INJ.engine) bridgePing();
if (INJ && Array.isArray(INJ.scenes) && INJ.scenes.length && INJ.nonce && store.get("evs.injected", "") !== INJ.nonce) {
  try {
    const np = sampleProject();
    np.name = String(INJ.topic || "Novo vídeo").slice(0, 60); np.topic = INJ.topic || "";
    if (INJ.purpose) { np.purpose = INJ.purpose; const pp = PURPOSES.find(p => p.id === INJ.purpose); if (pp) { np.style = pp.style; np.music = pp.music; } }
    if (INJ.style && STYLES[INJ.style]) np.style = INJ.style;
    np.styleDesc = INJ.styleDesc || "";
    if (INJ.post) np.post = normPost(INJ.post);
    if (INJ.music && MUSIC[INJ.music]) np.music = INJ.music;
    np.brand = "";
    if (INJ.duration) np.duration = INJ.duration;
    if (INJ.format) np.format = INJ.format;
    if (INJ.lang) np.voice.lang = INJ.lang;
    np.scenes = normalizeScenes(INJ.scenes);
    projects.unshift(np); P = np; step = 5;
    store.set("evs.injected", INJ.nonce); store.set("evs.projects", projects); store.set("evs.current", P.id);
  } catch (e) {}
}
loadPhoto();
loadKitLogo();
P.scenes.forEach(s => s.clipUrl && loadClip(s.id, s.clipUrl));
P.scenes.forEach(loadSceneImage);
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
[data-baseweb="textarea"],[data-baseweb="textarea"]>div,.stApp textarea{background-color:#100e17!important;border-color:#332d45!important;color:#efeaf7!important;-webkit-text-fill-color:#efeaf7}
.stApp textarea::placeholder{color:#7d7592!important;-webkit-text-fill-color:#7d7592!important;opacity:1}
.stApp input::placeholder{color:#7d7592!important;-webkit-text-fill-color:#7d7592!important;opacity:1}
.stApp input{color:#efeaf7!important;-webkit-text-fill-color:#efeaf7}
[data-baseweb="select"] div{color:#efeaf7;background-color:#100e17!important}
[data-baseweb="select"] svg{fill:#a69fba}
[data-baseweb="input"] button svg{fill:#a69fba}
.stApp button[kind^="primary"]{background:#ff5a36;border-color:#ff5a36;color:#1a0b06;font-weight:700}
.stApp button[kind^="primary"]:hover{background:#ff7352;border-color:#ff7352;color:#1a0b06}
[data-testid="stExpander"] details{background:#1a1724;border:1px solid #332d45!important;border-radius:14px}
[data-testid="stExpander"] summary p{font-weight:700;font-size:16px}
[data-testid="stExpander"] summary,[data-testid="stExpander"] summary:hover,[data-testid="stExpander"] summary:focus{background:#231f30!important;color:#efeaf7!important;border-radius:14px}
[data-testid="stExpander"] summary *{color:#efeaf7!important}
[data-testid="stExpander"] summary svg{fill:#efeaf7!important}
[data-baseweb="input"] button{background:#100e17!important}
.stApp [data-baseweb="tab-list"]{gap:4px;flex-wrap:wrap}
.stApp [data-baseweb="tab"] p{color:#efeaf7!important}
.stApp [data-baseweb="tab-highlight"]{background:#ff5a36}
.stApp code{background:#231f30;color:#ffb39f}
.stApp pre,.stApp [data-testid="stCode"] pre{background:#100e17!important;border:1px solid #332d45;border-radius:12px}
.stApp pre code,.stApp pre code span{background:transparent!important;color:#efeaf7!important;font-family:"Figtree",system-ui,sans-serif!important;font-size:14.5px}
[data-testid="stLinkButton"] a{background:#1a1724!important;border:1px solid #4a4262!important;color:#efeaf7!important;font-weight:600}
[data-testid="stLinkButton"] a *{color:#efeaf7!important}
[data-testid="stLinkButton"] a:hover{border-color:#ff5a36!important}
[data-testid="stMarkdownContainer"] a{color:#ff8a6b!important;font-weight:700}
[data-testid="stLinkButton"] a[kind^="primary"],[data-testid="stLinkButton"] a[data-testid*="Primary"]{background:#ff5a36!important;border-color:#ff5a36!important}
[data-testid="stLinkButton"] a[kind^="primary"] *,[data-testid="stLinkButton"] a[data-testid*="Primary"] *{color:#1a0b06!important}
[data-testid="stChatMessage"]{background:transparent}
[data-testid="stChatInput"],[data-testid="stChatInput"]>div,[data-testid="stChatInput"] textarea{background-color:#100e17!important;color:#efeaf7!important;border-color:#332d45!important}
[data-testid="stVerticalBlockBorderWrapper"]{border-color:#332d45!important}
.stApp button[kind^="secondary"]{background:#1a1724;border-color:#332d45;color:#efeaf7}
</style>""", unsafe_allow_html=True)


PURPOSES = {
    "Anúncio / Vendas": "anuncio", "Aula / Tutorial": "aula", "Reels e Stories": "reels",
    "Receita": "receita", "Parabéns / Convite": "convite", "Empresa": "empresa",
    "História animada": "historia", "Imóvel / Obra": "imovel",
}
FORMATS = {"Vertical 9:16": "9:16", "Horizontal 16:9": "16:9", "Quadrado 1:1": "1:1"}
LANGS = {"Português": "pt-BR", "Inglês": "en-US", "Espanhol": "es-ES"}
VISUAIS = {
    "Automático (pela finalidade)": "", "Vibrante": "vibrante", "Neon": "neon", "Lousa e giz": "giz",
    "Aquarela": "aquarela", "Cinema": "cinema", "Infantil": "infantil", "Empresa": "empresa",
}


GROQ_MODELS = ["grok-4.3", "grok-4.20-0309-non-reasoning", "grok-4.7"]  # modelos de texto da xAI (Grok), do mais barato ao mais capaz
XAI_CREDITOS_URL = "https://console.x.ai/"
XAI_CHAVES_URL = "https://console.x.ai/"
MSG_SEM_CREDITOS = "Sua conta da xAI está sem créditos. Compre créditos (a partir de 5 dólares, sem mensalidade) para usar a IA."


def build_prompt(topic, purpose_name, duration, fmt, lang_name, style_desc="", visual_name=""):
    n = max(3, min(10, round(duration / 7)))
    return f"""Você é roteirista de vídeos curtos para redes sociais.
Crie o roteiro de um vídeo animado.
Finalidade: {purpose_name}
Tema / pedido do cliente: {topic}
Serviço ou produto do cliente (use estas informações reais: o que é, o que faz, para quem, diferenciais, preço e contato; NÃO invente dados que não estão aqui): {style_desc or "não informado"}
Duração total: {duration} segundos, em {n} cenas.
Formato: {fmt}.{(" Estilo visual da animação: " + visual_name + ".") if visual_name else ""}
Idioma da narração e dos títulos: {lang_name}.

Regras:
- "title": texto curto que aparece grande na tela (máx. 6 palavras).
- "text": a narração falada da cena. No total, cerca de {round(duration * 2.4)} palavras somando todas as cenas. Linguagem natural, como uma pessoa falando.
- "emoji": um único emoji que ilustra a cena.
- "visual": descrição EM INGLÊS de uma cena animada para um gerador de vídeo por IA (personagens, ambiente, câmera). Uma frase.
- A primeira cena prende a atenção. A última cena tem uma chamada para ação adequada à finalidade.

Também escreva o texto para postar junto com o vídeo (Instagram/TikTok), no mesmo idioma:
- "legenda": 2 a 4 frases, com emojis moderados.
- "cta": chamada para ação curta, usando o contato real se ele foi informado.
- "hashtags": 8 a 12 hashtags relevantes, sem o símbolo #.

Responda somente com JSON neste formato:
{{"scenes":[{{"title":"...","text":"...","emoji":"🙂","visual":"..."}}],"post":{{"legenda":"...","cta":"...","hashtags":["..."]}}}}"""


MSG_CHAVE_RECUSADA = (
    "A xAI recusou a sua chave (ela não é uma chave de API válida, foi apagada ou foi copiada pela metade). "
    "Clique em **Sair**, pegue uma chave nova no site da xAI → **API Keys** → **Create API key** "
    "e entre de novo com ela, copiada inteira."
)


def erro_xai_texto(code, msg):
    m = (msg or "").lower()
    if code in (402,) or any(w in m for w in ("credit", "billing", "balance", "spending limit", "insufficient")):
        return RuntimeError(MSG_SEM_CREDITOS)
    if code in (401, 403) or "api key" in m or "api-key" in m:
        return RuntimeError(MSG_CHAVE_RECUSADA)
    if code == 429:
        return RuntimeError("Muitos pedidos seguidos na xAI. Espere um minuto e tente de novo.")
    return RuntimeError(f"A xAI respondeu com erro ({code}): {msg or 'erro'}")


def groq_call(prompt, key, model):
    """Pede uma resposta em JSON ao Grok (IA de texto da xAI)."""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt + "\n\nResponda somente com o JSON, sem texto antes ou depois."}],
        "temperature": 0.8,
    }).encode("utf-8")
    req = urllib.request.Request(
        XAI_BASE + "chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "estudio-de-videos"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read().decode("utf-8") or "{}")
            msg = j.get("error", {}).get("message", "") if isinstance(j.get("error"), dict) else str(j.get("error") or j.get("message") or "")
        except Exception:
            msg = ""
        raise erro_xai_texto(e.code, msg or e.reason)
    except urllib.error.URLError as e:
        raise RuntimeError(f"Não consegui conectar à xAI: {e.reason}")
    content = data["choices"][0]["message"]["content"] or ""
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        raise RuntimeError("A IA não respondeu no formato esperado. Tente de novo.")
    try:
        parsed = json.loads(m.group(0))
    except ValueError:
        raise RuntimeError("A IA não respondeu no formato esperado. Tente de novo.")
    return parsed if isinstance(parsed, dict) else {"scenes": parsed}


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


groq_json = groq_script  # pede uma resposta em JSON ao Grok (xAI), com troca automática de modelo


# ---------- chat de dúvidas ----------
CONHECIMENTO = """
SOBRE O APP "Estúdio de Vídeos":
- Cria vídeos animados para redes sociais (Reels, Stories, TikTok, YouTube, WhatsApp, anúncios).
- É uma ponte entre a pessoa e IAs profissionais: cada um usa a própria chave, sem assinatura mensal.
- Uma chave só: a chave do Grok Imagine (xAI), que começa com grok_. (Contas antigas da xAI podem ter chave começando com xai-: ela também funciona, mas nas explicações fale só da chave grok_.) É obrigatória para entrar. Ela liga toda a IA: roteiros, calendário, chat de dúvidas, texto do post, tradução, clipes, imagens e voz. Criar a chave é grátis; a IA usa créditos pré-pagos da xAI (sem mensalidade).
- O topo do app tem duas abas: "🎬 Vídeos gratuitos" (modelos prontos por nicho, roteiro escrito pela pessoa, fundos animados, marca, música; não gasta créditos) e "⭐ Vídeos pagos (IA profissional)" (nota "Vídeos profissionais sem assinatura mensal", botão de comprar créditos e as sub-abas "✨ Roteiro com IA", "📅 Meu mês de conteúdo" e "🎥 Clipes, imagens e voz").
- Custos de texto: roteiro com IA menos de 1 centavo de dólar; calendário do mês cerca de 1 centavo; cada mensagem do chat frações de centavo.
- Sem créditos: os vídeos gratuitos funcionam; a IA mostra o aviso "Sua conta da xAI está sem créditos" com o botão de comprar.
- As chaves valem só na sessão; não ficam salvas no servidor. Ao clicar em Sair ou fechar, precisa colar de novo.

COMO CRIAR A CHAVE DA xAI (site em inglês): console.x.ai -> Sign up/Sign in (criar conta/entrar com X, Google ou e-mail; se pedir Create team, criar com qualquer nome) -> comprar créditos no menu Billing do site https://console.x.ai/ (ou Settings -> Team -> Billing) -> API spend management -> Purchase credits (cartão de crédito, entra na hora; 5 a 10 dólares dão vários vídeos; sem mensalidade; Auto top-up é recarga automática opcional). No app também há o botão "💳 Comprar créditos na xAI" na seção IA paga. -> Back (voltar) -> no menu principal da esquerda, API Keys -> Create API Key -> Name: appvideos -> Create/Save -> Copy (a chave começa com xai- e aparece uma vez). Criar a chave é grátis; só cobra ao gerar.
NÃO SERVEM para o app: "Management Keys" (chaves de gerenciamento da equipe). A chave certa é criada em console.x.ai -> API Keys e começa com grok_ (contas antigas podem ter xai-, que também funciona; não puxe esse assunto se a pessoa não perguntar). Cada equipe tem chaves e créditos separados: a chave gasta os créditos da equipe onde foi criada. O app confere a chave direto na xAI ao entrar ou ao salvar no passo 8; se a xAI recusar, aparece um aviso.
Tradução dos menus da xAI: Usage = uso/gastos, Models = modelos, Team members = membros, Security = segurança, Audit Log = registro de atividades, Domains = domínios, Observability = monitoramento.

DOIS CAMINHOS: (A) VÍDEO GRATUITO = aba "🎬 Vídeos gratuitos": modelo pronto por nicho (ou roteiro escrito à mão no passo 6), fundos animados do app, sem gastar créditos. (B) VÍDEO PAGO = aba "⭐ Vídeos pagos": gerar roteiro com IA, depois passo 8 Gerar > seção IA paga > escolher modo, modelo (Lite barato / 1.5 melhor), resolução (comece 480p), conferir custo, Gerar clipes de todas as cenas (ou só uma para testar), esperar Pronto, depois Finalizar vídeo e Baixar.
PASSO A PASSO DO VÍDEO:
1. Roteiro com IA (aba ⭐ Vídeos pagos → ✨ Roteiro com IA): Tema do vídeo + "Descreva o seu serviço ou produto" (o que é, o que faz, para quem, diferenciais, preço, contato).
2. Escolher Finalidade, Formato (Vertical 9:16 para Reels/Stories, Horizontal 16:9 para YouTube, Quadrado 1:1 para feed), Duração (15/30/60/90 s), Idioma e Estilo visual.
3. Clicar em "Gerar roteiro com IA". O roteiro abre no estúdio, passo Roteiro: cada cena tem título (texto grande) e fala. Pode editar, apagar, adicionar e reordenar cenas.
4. Passos do estúdio: 1 Finalidade, 2 Formato, 3 Estilo (Vibrante, Neon, Lousa e giz, Aquarela, Cinema, Infantil, Empresa), 4 Apresentador (sem, personagem/emoji, minha foto), 5 Voz, 6 Roteiro, 7 Música (Animada, Calma, Épica, sem música; legendas; marca/@ no canto), 8 Gerar.
5. Botão laranja "Finalizar vídeo" embaixo da prévia: grava em tempo real (30 s de vídeo levam 30 s). Deixar a aba aberta e visível. Depois clicar em "Baixar vídeo pronto". Sai em MP4 no Chrome/Edge (alguns navegadores: WebM).
6. Se mudar algo depois, clicar em Finalizar vídeo de novo.
- "Meus vídeos" (no estúdio) lista os projetos, salvos no navegador onde foram criados.

VOZ: Voz pronta (do navegador) só toca na prévia, NÃO entra no arquivo. Para ter voz no arquivo: "Enviar áudio" (gravar no celular e enviar mp3/m4a/wav; a duração segue o áudio) ou "Minha voz" (microfone, se o navegador liberar). "Sem voz": música e legendas.

IA PAGA (xAI), no passo 8 Gerar:
- Modos: Texto -> vídeo; Minha foto falando (boca sincronizada, modelo 1.5); Personagem fixo (mesma pessoa em todas as cenas, até 10 s por cena, 720p); Animar minhas imagens (enviar imagem por cena no botão câmera); Imagens com IA (uma imagem por cena, mais barato).
- Modelos: Lite (mais barato, ~US$0,02/s em 480p), 1.5 (melhor, fala sincronizada, ~US$0,08 a 0,25/s), Clássico (editar e estender clipes, ~US$0,05/s). Imagens: ~US$0,02 cada. Valores aproximados; o app mostra o custo antes de gerar.
- Resolução 480p/720p/1080p. Som do clipe: mudo (usa música e voz do app) ou som da IA.
- Depois de gerar os clipes, clicar em Finalizar vídeo.

RECURSOS COMPLETOS DA IA PAGA (abas Vídeo, Imagens, Voz da IA no passo 8):
- Vídeo, modos: Texto->vídeo; Minha foto falando (Lite ou 1.5; no 1.5 escolhe entre 26 vozes); Personagem fixo (1.5 ou Clássico; foto + até 6 referências; até 720p); Animar minhas imagens (botão câmera por cena); Início e fim (só 1.5; fotos de início, meio opcional e fim; ótimo para antes e depois); Imagens com IA.
- Som do clipe: mudo / sons e efeitos da IA / a IA fala a narração (não no Clássico).
- Editar clipe com uma frase (botão lápis, clipes até 8,7 s) e estender clipe 2 a 10 s (botão +), ambos pelo modelo Clássico.
- Imagens: gerar (Imagem 2.0 ou 1.0, qualidade normal/alta, 1K/2K), editar com uma frase, juntar com referências (até 5 imagens).
- Voz da IA: narração natural pt-BR, 26 vozes (Eve padrão, Ara, Leo, Rex, Sal e outras), velocidade 0,7 a 1,5; entra no arquivo; cenas ajustam ao tamanho da fala; custo ~US$ 15 por 1 milhão de letras.
- Opções apagadas = combinação que a xAI não aceita naquele modelo. O app mostra custo estimado e gasto real.
- Modo adulto do Grok não existe na API e não está no app.
RECURSOS DE ASSOCIADO (todos dentro do app):
1) KIT DA MARCA (botão "🎨 Minha marca", no topo do estúdio): a pessoa cadastra uma vez o nome do negócio, frase de efeito, logo (PNG com fundo transparente fica melhor), cor principal, cor de fundo da cena final, WhatsApp, Instagram, site e endereço. Opções: usar a marca nos vídeos; mostrar logo e @ no canto; cena final de contato no fim de todo vídeo (3 a 6 s); QR code na cena final que abre o WhatsApp (se não tiver WhatsApp, abre o site ou o Instagram). Botão "Ver a cena final" mostra como fica. A marca fica salva no navegador e entra no backup. Não custa nada.
2) MODELOS PRONTOS POR NICHO (aba "🎬 Vídeos gratuitos", no topo da página): 12 nichos (restaurante/pizzaria, salão/barbearia/estética, imobiliária/corretor, construção/reforma/engenharia, clínica/saúde, advocacia/contabilidade/consultoria, loja de roupas, academia/personal, cursos/mentoria, eventos/festas/igreja, pet shop/veterinária, outro negócio) e 3 tipos de vídeo em cada um (🔥 Oferta ou promoção, 🏪 Conheça o meu negócio, 💡 Dica de especialista). Preenche nome do negócio, produto ou serviço, oferta (opcional), cidade e WhatsApp (opcionais) e clica em "Criar vídeo com este modelo". Não usa IA, é instantâneo e grátis. Já vem com estilo, música e texto do post.
3) MEU MÊS DE CONTEÚDO (aba "⭐ Vídeos pagos" → "📅 Meu mês de conteúdo"; usa créditos, cerca de 1 centavo): descreve o negócio, escolhe nicho, objetivo (vender mais, ganhar seguidores, mostrar autoridade, lançar produto, trazer clientes para a loja), frequência (3 por semana, 5 por semana ou todo dia) e a data de início. A IA (Grok) monta até 30 ideias com data, tipo (oferta, dica, bastidores, depoimento, antes e depois, data comemorativa...), título, gancho (primeira frase) e o que mostrar. Em cada ideia: botão "🎬 Criar este vídeo" (gera o roteiro e abre no estúdio) e caixa "Feito" para acompanhar o progresso. Botão "Baixar calendário (planilha CSV)" abre no Excel/Google Planilhas. O calendário fica na sessão: baixe a planilha para guardar.
4) TEXTO DO POST: todo roteiro gerado (com IA ou modelo) vem com legenda, chamada para ação e hashtags. Aparece no topo ("📝 Texto do post para copiar", com ícone de copiar) e no estúdio, passo 8 · Gerar, no quadro "📝 Texto do post" (botões "Copiar texto" e "Gerar de novo", que escreve de novo com base no roteiro atual e nos contatos da marca).
5) UM VÍDEO, TRÊS FORMATOS: passo 8 · Gerar, botão "📐 Gerar nos 3 formatos": grava o mesmo vídeo em 9:16 (Reels/Stories/TikTok), 1:1 (feed) e 16:9 (YouTube), um depois do outro (leva 3 vezes a duração do vídeo; deixe a aba aberta). Depois aparecem 3 botões para baixar cada um.
6) BACKUP: em "Meus vídeos" (topo do estúdio): "💾 Baixar backup" salva um arquivo .json com todos os vídeos e a marca; "📂 Restaurar backup" abre esse arquivo em outro computador ou celular. Os projetos ficam salvos no navegador; o backup protege contra troca de aparelho ou limpeza do navegador. (Salvar na nuvem automaticamente ainda não existe.)
7) OUTROS IDIOMAS: passo 8 · Gerar, quadro "🌎 Este vídeo em outros idiomas": botões para criar versão em inglês ou espanhol (ou português, se o vídeo estiver em outro idioma). A IA traduz roteiro e texto do post e cria uma cópia do projeto com as mesmas cenas e clipes. Depois gere a narração na aba "🎙️ Voz da IA" (a voz da xAI fala inglês e espanhol). Nomes, telefones, @ e sites não são traduzidos.
PROBLEMAS COMUNS: chave recusada -> copiar de novo sem espaços ou criar outra. Vídeo com roteiro antigo -> gerar no topo, conferir no passo Roteiro, Finalizar de novo. Vídeo sem voz -> usar Enviar áudio. Gravação travando -> aba visível, Chrome/Edge, fechar abas pesadas. Sem créditos na xAI -> Billing em console.x.ai. Projetos sumiram -> só aparecem no mesmo navegador.
"""

SISTEMA_CHAT = (
    "Você é o assistente do app 'Estúdio de Vídeos'. Responda sempre em português do Brasil, "
    "com linguagem simples para leigos, frases curtas e passo a passo quando ajudar. "
    "Seja direto e simpático. Use as informações abaixo sobre o app; se algo não estiver nelas, diga que não tem certeza "
    "em vez de inventar. Você também pode ajudar com ideias de vídeos, roteiros, títulos, legendas e dicas de redes sociais. "
    "Nunca peça a chave da pessoa e, se ela tentar colar uma chave no chat, avise para não compartilhar chaves.\n\n"
    + CONHECIMENTO
)


def groq_chat(messages, key):
    last = None
    for model in GROQ_MODELS:
        body = json.dumps({"model": model, "messages": messages, "temperature": 0.5}).encode("utf-8")
        req = urllib.request.Request(
            XAI_BASE + "chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "estudio-de-videos"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read().decode("utf-8"))
            return (data["choices"][0]["message"].get("content") or "").strip() or "Não consegui responder agora. Tente perguntar de outro jeito."
        except urllib.error.HTTPError as e:
            try:
                j = json.loads(e.read().decode("utf-8") or "{}")
                msg = j.get("error", {}).get("message", "") if isinstance(j.get("error"), dict) else str(j.get("error") or j.get("message") or "")
            except Exception:
                msg = ""
            last = erro_xai_texto(e.code, msg or e.reason)
            if not (e.code in (400, 404) and "model" in (msg or "").lower()):
                raise last
        except urllib.error.URLError as e:
            raise RuntimeError(f"Não consegui conectar à xAI: {e.reason}")
    raise last


def chat_duvidas():
    st.divider()
    st.markdown(
        "<h3 style='margin-bottom:0'>💬 Tire suas dúvidas com a IA</h3>"
        "<p style='opacity:.75;margin-top:4px'>Pergunte qualquer coisa sobre o app, as chaves, os custos ou peça ideias de vídeo. "
        "A conversa continua: é só ir respondendo.</p>",
        unsafe_allow_html=True,
    )
    hist = st.session_state.setdefault("evs_chat", [])
    caixa = st.container(border=True)
    conversa = caixa.container()  # mensagens sempre acima do campo de digitar
    pergunta = caixa.chat_input("Digite a sua dúvida e aperte Enter…", key="evs_chat_input")
    if pergunta:
        hist.append({"role": "user", "content": pergunta})
    with conversa:
        if not hist:
            with st.chat_message("assistant", avatar="🎬"):
                st.markdown(
                    f"Oi, {html.escape(st.session_state['evs_user'])}! Sou o assistente do Estúdio de Vídeos. "
                    "Como posso ajudar? Exemplos: *Como pego a chave do Grok?*, *Quanto custa um vídeo de 30 segundos?*, "
                    "*Me dá 3 ideias de vídeo para uma pizzaria.*"
                )
        for m in hist:
            with st.chat_message(m["role"], avatar="🙂" if m["role"] == "user" else "🎬"):
                st.markdown(m["content"])
        if pergunta:
            with st.chat_message("assistant", avatar="🎬"):
                with st.spinner("Pensando…"):
                    try:
                        msgs = [{"role": "system", "content": SISTEMA_CHAT}] + hist[-12:]
                        resposta = groq_chat(msgs, st.session_state["evs_xai"])
                    except Exception as e:  # noqa: BLE001
                        resposta = f"⚠️ {e}" + (f"\n\n👉 [💳 Comprar créditos na xAI]({XAI_CREDITOS_URL})" if "crédito" in str(e) else "") + (
                            f"\n\n👉 [🔑 Pegar uma chave nova na xAI]({XAI_CHAVES_URL})" if "recusou" in str(e) else "")
                st.markdown(resposta)
            hist.append({"role": "assistant", "content": resposta})
    if hist and st.button("🧹 Limpar conversa"):
        st.session_state["evs_chat"] = []
        st.rerun()



# ---------- ponte estúdio ↔ servidor (IA paga pela xAI) ----------
# O estúdio (dentro do iframe) manda os pedidos para cá por postMessage. O servidor chama a xAI com a
# chave da pessoa (que nunca vai para o navegador), baixa os clipes prontos e devolve tudo para o estúdio.
PONTE_JS = r"""
export default function(component) {
  const { data, setTriggerValue } = component;
  const G = window.__evsPonte || (window.__evsPonte = { queue: [], inflight: false, seen: new Set(), src: null });
  G.set = setTriggerValue;
  if (!G.listening) {
    G.listening = true;
    window.addEventListener("message", (ev) => {
      const m = ev.data;
      if (!m || typeof m !== "object") return;
      if (m.evs === "ping") { try { ev.source.postMessage({ evs: "pong" }, "*"); } catch (e) {} return; }
      if (m.evs === "toast") {
        let t = document.getElementById("evsToast");
        if (!t) {
          t = document.createElement("div"); t.id = "evsToast"; t.setAttribute("role", "status");
          t.style.cssText = "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:999999;max-width:min(560px,calc(100% - 32px));background:#efeaf7;color:#100e17;padding:12px 18px;border-radius:12px;font:600 15px/1.4 system-ui,sans-serif;box-shadow:0 10px 30px rgba(0,0,0,.45);transition:opacity .2s";
          document.body.appendChild(t);
        }
        t.textContent = String(m.msg || "").slice(0, 400); t.style.opacity = "1"; t.style.display = "block";
        clearTimeout(G.toastTimer); G.toastTimer = setTimeout(() => { t.style.opacity = "0"; setTimeout(() => { t.style.display = "none"; }, 250); }, Math.min(Math.max(+m.ms || 3500, 2500), 9000));
        return;
      }
      if (m.evs !== "req" || !m.req) return;
      G.src = ev.source; G.queue.push(m.req); G.flush();
    });
    G.flush = () => {
      if (G.inflight || !G.queue.length) return;
      G.inflight = true;
      const lote = { id: String(Date.now()) + Math.random().toString(36).slice(2, 6), reqs: G.queue.splice(0, 6) };
      G.cur = lote;
      clearTimeout(G.timer);
      G.timer = setTimeout(() => {  // sem resposta: libera a fila e avisa o estúdio
        if (!G.cur || G.cur.id !== lote.id) return;
        for (const r of lote.reqs) { try { G.src && G.src.postMessage({ evs: "res", res: { reqId: r.reqId, ok: false, status: 0, error: "O servidor não respondeu a tempo. Tente de novo." } }, "*"); } catch (e) {} }
        G.inflight = false; G.cur = null; G.flush();
      }, 200000);
      G.set("lote", lote);
    };
  }
  const d = data || {};
  for (const r of (d.out || [])) {
    if (G.seen.has(r.reqId)) continue;
    G.seen.add(r.reqId);
    try { G.src && G.src.postMessage({ evs: "res", res: r }, "*"); } catch (e) {}
  }
  if (d.feito && G.cur && d.feito === G.cur.id) { clearTimeout(G.timer); G.inflight = false; G.cur = null; G.flush(); }
}
"""
ponte_xai = components_v2.component("evs_ponte_xai", js=PONTE_JS) if components_v2 else None

XAI_BASE = os.environ.get("EVS_XAI_BASE", "https://api.x.ai/v1/")  # só muda em testes
XAI_POST = {"videos/generations", "videos/extensions", "videos/edits", "images/generations", "images/edits", "tts"}
XAI_GET = re.compile(r"^videos/[A-Za-z0-9_-]{4,100}$")
MAX_CLIPE = 80 * 1024 * 1024


def xai_prefixo_ok(k):
    return k.startswith(("xai-", "grok_")) and 20 <= len(k) <= 300


def xai_check(key):
    """Confere a chave direto na xAI. Devolve None se estiver ok (ou se não der para conferir agora)."""
    try:
        status, j = xai_http("GET", "api-key", None, key)
    except Exception:  # noqa: BLE001
        return None
    err = j.get("error") if isinstance(j, dict) else None
    msg = (err.get("message", "") if isinstance(err, dict) else str(err or (j.get("message", "") if isinstance(j, dict) else ""))).lower()
    if status in (401, 403) or (status == 400 and ("api key" in msg or "api-key" in msg)):
        return ("A xAI recusou essa chave. Ela precisa ser uma chave de API criada no site da xAI → API Keys → "
                "Create API key. Confira se copiou a chave inteira e se ela não foi apagada.")
    return None


def xai_http(method, path, body, key):
    req = urllib.request.Request(
        XAI_BASE + path,
        data=json.dumps(body).encode("utf-8") if method == "POST" else None,
        method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "estudio-de-videos"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read().decode("utf-8") or "{}"
            return r.status, json.loads(txt)
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read().decode("utf-8") or "{}")
        except Exception:  # noqa: BLE001
            j = {}
        return e.code, j


def baixar_clipe(url):
    req = urllib.request.Request(url, headers={"User-Agent": "estudio-de-videos"})
    with urllib.request.urlopen(req, timeout=120) as r:
        tipo = (r.headers.get("Content-Type") or "video/mp4").split(";")[0].strip()
        dados = r.read(MAX_CLIPE + 1)
    if len(dados) > MAX_CLIPE:
        raise RuntimeError("clipe grande demais para juntar no navegador")
    if not tipo.startswith("video/"):
        tipo = "video/mp4"
    return f"data:{tipo};base64," + base64.b64encode(dados).decode("ascii")


def atender_lote(lote):
    saida = []
    for r in (lote.get("reqs") or [])[:6]:
        rid = str(r.get("reqId", ""))[:80]
        if r.get("method") == "STATUS":  # o estúdio pergunta se já tem chave do Grok
            saida.append({"reqId": rid, "ok": True, "status": 200, "json": {"hasXai": bool(st.session_state.get("evs_xai"))}})
            continue
        if r.get("method") == "GROQ":  # texto do post, tradução etc.: o Grok (xAI) é chamado pelo servidor
            prompt = str((r.get("body") or {}).get("prompt", ""))[:20000]
            try:
                saida.append({"reqId": rid, "ok": True, "status": 200, "json": groq_json(prompt, st.session_state.get("evs_xai", ""))})
            except Exception as e:  # noqa: BLE001
                saida.append({"reqId": rid, "ok": False, "status": 0, "error": str(e)})
            continue
        if r.get("method") == "KEY":  # a pessoa colou a chave dentro do estúdio: guarda só no servidor
            nova = str((r.get("body") or {}).get("key", "")).strip()
            erro = None if xai_prefixo_ok(nova) else "Essa chave não parece do Grok. Ela começa com grok_."
            erro = erro or xai_check(nova)
            if not erro:
                st.session_state["evs_xai"] = nova
                saida.append({"reqId": rid, "ok": True, "status": 200, "json": {"hasXai": True}})
            else:
                saida.append({"reqId": rid, "ok": False, "status": 400, "error": erro})
            continue
        chave = st.session_state.get("evs_xai", "")
        metodo = "POST" if r.get("method") == "POST" else "GET"
        caminho = str(r.get("path", ""))
        if not chave:
            saida.append({"reqId": rid, "ok": False, "status": 401, "error": "Entre no app com a chave do Grok para usar a IA paga (clique em Sair e entre de novo)."})
            continue
        permitido = caminho in XAI_POST if metodo == "POST" else (bool(XAI_GET.match(caminho)) and caminho not in XAI_POST)
        if not permitido:
            saida.append({"reqId": rid, "ok": False, "status": 400, "error": "Pedido não permitido."})
            continue
        try:
            status, j = xai_http(metodo, caminho, r.get("body") if metodo == "POST" else None, chave)
            video = j.get("video") if isinstance(j, dict) else None
            if metodo == "GET" and status < 300 and j.get("status") == "done" and isinstance(video, dict) and video.get("url"):
                try:
                    video["data"] = baixar_clipe(video["url"])
                except Exception as e:  # noqa: BLE001
                    video["data_error"] = str(e)
            saida.append({"reqId": rid, "ok": status < 300, "status": status, "json": j})
        except Exception as e:  # noqa: BLE001
            saida.append({"reqId": rid, "ok": False, "status": 0, "error": f"Não consegui falar com a xAI pelo servidor: {e}"})
    return saida


def montar_ponte():
    """Coloca a ponte na página e atende o lote de pedidos que o estúdio mandou."""
    if not ponte_xai:
        return False
    res = ponte_xai(
        data={"out": st.session_state.get("evs_ponte_out", []), "feito": st.session_state.get("evs_ponte_feito", "")},
        key="evs_ponte",
        on_lote_change=lambda: None,
    )
    lote = getattr(res, "lote", None) if res is not None else None
    if isinstance(lote, dict) and lote.get("id") and lote.get("id") != st.session_state.get("evs_ponte_ultimo"):
        st.session_state["evs_ponte_ultimo"] = lote["id"]
        st.session_state["evs_ponte_out"] = atender_lote(lote)
        st.session_state["evs_ponte_feito"] = lote["id"]
        st.rerun()
    return True


# ---------- tutorial para leigos ----------
GUIA_XAI = """
**Sua chave do Grok**: é ela que liga toda a IA do app (roteiros, calendário, chat, clipes, imagens e voz) · [abrir site](https://console.x.ai)

O site também é em inglês. Ao lado de cada botão está o que ele significa.

**Parte 1: criar a conta**

1. Clique aqui para abrir: 👉 **[console.x.ai](https://console.x.ai)** (abre em outra aba).
2. Clique em **Sign up** (criar conta) ou **Sign in** (entrar). Pode entrar com a conta do **X** (Twitter), do **Google** ou com e-mail.
3. Se aparecer **Create team** (criar equipe), escreva qualquer nome (por exemplo, o nome do seu negócio) e confirme.

**Parte 2: colocar créditos** (sem créditos a chave não gera nada)

4. Já logado na xAI, clique aqui: 👉 **[💳 Comprar créditos na xAI](https://console.x.ai/)** e, no menu da esquerda, clique em **Billing** (cobrança).
   Se preferir pelo menu: clique na engrenagem **Settings** (configurações) e, no menu **Team** (equipe), em **Billing** (cobrança).
5. Na parte **API spend management** (controle de gastos), clique em **Purchase credits** / **Buy credits** (comprar créditos).
6. Escolha o valor e pague com **cartão de crédito** (os créditos entram na hora). Pode pedir para salvar o cartão.
   Opcional: **Auto top-up** (recarga automática) compra créditos sozinho quando o saldo acaba. Se não quiser surpresas, deixe desligado.
   **5 a 10 dólares** já dão para vários vídeos. É pré-pago: **não tem mensalidade**.

**Parte 3: criar a chave**

7. Clique em **Back** (voltar), no topo à esquerda, para sair das configurações.
8. Clique aqui: 👉 **[🔑 Obter minha chave do Grok](https://console.x.ai/)** e, no menu da esquerda, clique em **API Keys** (chaves de API).
   Se preferir pelo menu: no menu principal da esquerda, clique em **API Keys**.
9. Clique em **Create API Key** (criar chave de API). Em **Name** (nome), escreva `appvideos`.
   Deixe as permissões como estão e clique em **Create** / **Save** (criar / salvar).
10. A chave aparece começando com **grok_**. Clique em **Copy** (copiar). Ela só aparece **uma vez**.
11. Cole a chave no campo **Sua chave do Grok**, na tela de entrada deste app, e clique em **Entrar no app**.
    Para trocar a chave depois: no estúdio, passo **8 · Gerar**, botão **Trocar chave**.

**Atenção, para não confundir:**
- **Management Keys** (chaves de gerenciamento), no menu de configurações, **não servem** para este app. Elas servem para administrar a equipe.
- Se você tiver **mais de uma equipe** (o nome aparece no topo do menu da esquerda), cada uma tem **chaves e créditos separados**. Use a chave da equipe onde estão os créditos.
- Crie a chave em **console.x.ai** → **API Keys**. O app confere a chave direto na xAI quando você coloca: se ela não servir, aparece um aviso na hora.
- Outros itens do menu: **Usage** (uso / quanto já gastou), **Models** (modelos), **Team members** (membros da equipe), **Security** (segurança).
"""


# Guia da tela de entrada: só a chave (sem falar de compra, para não assustar quem está chegando)
GUIA_ENTRADA = """
O site da xAI é em inglês. Ao lado de cada botão está o que ele significa. **Criar a conta e a chave é grátis.**

1. Clique aqui para abrir: 👉 **[console.x.ai](https://console.x.ai/)** (abre em outra aba).
2. Clique em **Sign up** (criar conta) ou **Sign in** (entrar). Pode entrar com a conta do **X** (Twitter), do **Google** ou com e-mail.
3. Se aparecer **Create team** (criar equipe), escreva qualquer nome (por exemplo, o nome do seu negócio) e confirme.
4. No menu da esquerda, clique em **API Keys** (chaves de API).
5. Clique em **Create API Key** (criar chave de API). Em **Name** (nome), escreva `appvideos` e clique em **Create** / **Save** (criar / salvar).
6. A chave aparece começando com **grok_**. Clique em **Copy** (copiar). Ela só aparece **uma vez**.
7. Volte aqui, cole a chave no campo **Sua chave do Grok** e clique em **Entrar no app**.

⚠️ **Management Keys** (chaves de gerenciamento) **não servem**. Use a chave de **API Keys**.
"""


def tutorial(aberto):
    with st.expander("📘 Tutorial: como usar o app (comece por aqui)", expanded=aberto):
        t1, ts, tp, ta, t2, t4, t5, t6 = st.tabs(
            ["1. O que é", "🎬 Vídeos gratuitos", "⭐ Vídeos pagos", "🎁 Recursos de associado", "As chaves", "Voz", "IA paga: detalhes", "Problemas comuns"]
        )
        with t1:
            st.markdown("""
**Este app cria vídeos animados para redes sociais**: Reels, Stories, TikTok, YouTube, WhatsApp e anúncios.

Você escreve o tema e descreve o seu serviço. A inteligência artificial escreve o roteiro, e o app monta o vídeo
com animação, títulos, legendas, música e, se quiser, a sua foto ou um personagem.

**Por que é diferente:** o app é uma **ponte** entre você e a IA profissional **Grok Imagine (xAI)**. Você usa a sua própria chave
e **não paga assinatura mensal**: paga só o que usar, direto na sua conta da xAI.

**Do que você precisa:**
- Um computador ou celular com **Chrome** ou **Edge** (é onde funciona melhor).
- A sua **chave do Grok Imagine (xAI)**. Criar a chave é grátis (veja a aba **As chaves**).
- **Créditos na xAI** só para os recursos de IA. Os vídeos gratuitos não gastam nada.

**Dois jeitos de criar:**
- **🎬 Vídeos gratuitos:** modelos prontos do seu nicho ou roteiro escrito por você, com fundos animados, sua marca, legendas e música.
- **⭐ Vídeos pagos (IA profissional):** roteiro e calendário com IA, cenas de vídeo feitas por IA, a sua foto falando, imagens e voz. Usa créditos da xAI.

Veja o passo a passo de cada um nas próximas abas.
""")
        with ta:
            st.markdown("""
### 🎁 Recursos de associado
**🎨 Minha marca** (botão no topo do estúdio)
Cadastre **uma vez** o nome do negócio, o logo, as cores, o WhatsApp, o Instagram e o site.
Todos os vídeos saem com o seu **logo e @ no canto** e uma **cena final de contato com QR code** que abre o seu WhatsApp.
Clique em **👀 Ver a cena final** para conferir. Não custa nada.

**📋 Modelos prontos por nicho** (aba **🎬 Vídeos gratuitos**, no topo da página)
12 nichos (restaurante, salão, imobiliária, construção, clínica, advocacia, loja, academia, cursos, eventos, pet shop e outros)
com 3 tipos de vídeo: **Oferta**, **Conheça o meu negócio** e **Dica de especialista**.
Preencha o nome do negócio e o produto e clique em **📋 Criar vídeo com este modelo**. É instantâneo e grátis.

**📅 Meu mês de conteúdo** (aba **⭐ Vídeos pagos**, no topo da página · usa créditos, cerca de 1 centavo)
Descreva o seu negócio, escolha o objetivo e quantos vídeos por semana. A IA monta o **calendário do mês** com até 30 ideias,
cada uma com data, tipo, título e a primeira frase. Clique em **🎬 Criar este vídeo** em cada ideia e marque **Feito**.
Baixe o calendário em planilha para guardar.

**📝 Texto do post**
Todo vídeo vem com **legenda, chamada e hashtags** prontas para copiar. Ficam no topo da página e no passo **8 · Gerar**.

**📐 Três formatos de uma vez** (passo 8 · Gerar)
O mesmo vídeo para **Reels/Stories (9:16)**, **feed (1:1)** e **YouTube (16:9)**. Leva 3 vezes o tempo do vídeo.

**💾 Backup** (botão **Meus vídeos**)
**Baixar backup** guarda todos os seus vídeos e a sua marca num arquivo. **Restaurar backup** abre esse arquivo em outro aparelho.
Faça um backup de vez em quando: os projetos ficam salvos no navegador.

**🌎 Outros idiomas** (passo 8 · Gerar)
A IA traduz o roteiro e o texto do post para **inglês** ou **espanhol** e cria uma cópia do vídeo.
Depois gere a narração na aba **🎙️ Voz da IA** para ouvir no novo idioma.
""")
        with t2:
            st.markdown("""
**O que é uma "chave"?** É como uma senha que liga o app à sua conta na empresa de IA.
Cada pessoa usa a sua. O uso fica na sua conta, e só você vê.
""")
            st.markdown(GUIA_XAI)
            st.markdown("""
**Cuidados importantes**
- Nunca mande a sua chave por WhatsApp, e-mail ou grupo. Quem tiver a chave pode usar a sua conta.
- Se achar que alguém viu a sua chave, apague ela no site (API Keys) e crie outra.
- Aqui no app a chave vale **só enquanto você está usando**. Ela não fica salva no servidor.
  Quando você clicar em **Sair** ou fechar, precisa colar de novo na próxima vez.
""")
        with ts:
            st.markdown("""
### 🎬 Criar vídeo **gratuito**
Vídeo animado com fundos coloridos, títulos, emojis, personagem ou a sua foto, legendas, música e a sua marca.
Ótimo para promoções, avisos, dicas e stories. **Não gasta créditos.**

1. **Entre no app** com o seu nome e a sua chave.
2. No topo da página, aba **🎬 Vídeos gratuitos**, escolha o **seu nicho** e o **tipo de vídeo** (Oferta, Conheça o meu negócio ou Dica).
3. Preencha o **nome do negócio**, o **produto ou serviço** e, se quiser, a oferta, a cidade e o WhatsApp.
4. Clique em **📋 Criar vídeo com este modelo**. O vídeo abre na hora no estúdio, logo abaixo.
5. Quer escrever do seu jeito? No estúdio, passo **6 · Roteiro**, mude os textos, apague ou adicione cenas.
6. Cada cena tem um **título** (texto grande na tela) e a **fala** (legenda e narração).
7. Se quiser, ajuste nos passos do estúdio: **Estilo**, **Apresentador** (sua foto ou um personagem), **Voz** e **Música**.
   Aperte **▶** na prévia para assistir.
8. Clique no botão laranja **🎬 Finalizar vídeo**, embaixo da prévia.
   Ele grava **em tempo real** (30 s de vídeo = 30 s de espera). **Deixe a aba aberta e na frente.**
9. Clique em **⬇ Baixar vídeo pronto** e pronto!

💡 Mudou algo depois? Clique em **🎬 Finalizar vídeo** de novo.
💡 Quer voz no arquivo baixado? Veja a aba **Voz** (use **Enviar áudio**).
""")
        with tp:
            st.markdown("""
### ⭐ Criar vídeo **pago** (IA profissional, sem assinatura)
Cada cena ganha **vídeo de verdade feito por IA**: pessoas, produtos, lugares e câmera em movimento,
ou **a sua foto falando**. Você paga só pelo que gerar, direto na sua conta da xAI,
**a partir de poucos reais por vídeo**. Precisa de **créditos na xAI** (botão **💳 Comprar créditos**).

**Parte 1: entrar e colocar créditos**
1. Entre com o seu nome e a sua **chave do Grok Imagine (xAI)**.
   Sem créditos? Clique em **💳 Comprar créditos** (5 a 10 dólares já dão para vários vídeos).

**Parte 2: fazer o roteiro com IA**

2. No topo da página, aba **⭐ Vídeos pagos** → **✨ Roteiro com IA**: preencha o **Tema** e **Descreva o seu serviço ou produto**, escolha formato e duração.
3. Clique em **✨ Gerar roteiro com IA** (menos de 1 centavo de dólar) e confira as cenas no passo **Roteiro** do estúdio.

Depois, siga os passos abaixo para gerar as cenas com a IA. No fim, é só clicar em **🎬 Finalizar vídeo**, embaixo da prévia (o mesmo botão dos vídeos gratuitos).

**Parte 3: gerar as cenas com a IA profissional**

4. No estúdio, clique no passo **8 · Gerar** e desça até **🤖 IA paga**.
5. Em **1. O que a IA vai fazer**, escolha:
   - **✍️ Texto → vídeo**: cenas de vídeo criadas pela IA (o mais comum).
   - **🗣️ Minha foto falando**: a sua foto vira um apresentador que fala. Antes, envie a foto no passo **Apresentador**.
   - **🖼️ Animar minhas imagens**: use o botão **📷** de cada cena para enviar a foto do produto, da loja ou do imóvel.
   - **🎨 Imagens com IA**: imagens desenhadas pela IA, a opção mais barata.
6. Em **2. Modelo**, escolha **Lite** (mais barato) ou **1.5** (melhor qualidade e fala sincronizada).
7. Em **3. Resolução**, comece com **480p**. Em **4. Som do clipe**, escolha **Mudo** para usar a sua música e voz.
8. Confira o **💰 custo estimado**.
9. Clique em **🤖 Gerar clipes de todas as cenas** e espere aparecer **Pronto** em cada cena (1 a 3 minutos por cena).

**Parte 4: finalizar e baixar**

10. Clique no botão laranja **🎬 Finalizar vídeo**. O app junta os clipes da IA com títulos, legendas, música e a sua marca.
11. Deixe a aba aberta até terminar e clique em **⬇ Baixar vídeo pronto**.

💡 **Primeiro teste barato:** em vez de gerar todas as cenas, clique em **Gerar** em **uma cena só**,
com o modelo **Lite** em **480p**. Assim você vê o resultado gastando centavos.
""")
        with t4:
            st.markdown("""
**Como colocar voz no vídeo** (passo **Voz** do estúdio)

- **Voz pronta:** uma voz do computador lê o roteiro. **Atenção:** ela toca só na prévia e **não vai para o arquivo baixado**.
- **✨ Voz da IA** (recomendado, precisa da chave do Grok): voz natural em português do Brasil, com 26 opções.
  Clique em **Gerar narração com a voz da IA**. A voz **entra no arquivo baixado** e as cenas se ajustam ao tamanho da fala.
- **Enviar áudio** (recomendado): grave a narração no celular, lendo o roteiro com calma, e envie o arquivo
  (mp3, m4a, wav). A duração do vídeo se ajusta ao áudio.
- **Minha voz:** grava pelo microfone do computador enquanto o vídeo passa como teleprompter.
  Funciona só se o navegador liberar o microfone.
- **Sem voz:** só música e legendas. Funciona muito bem no Reels, porque muita gente assiste sem som.

Com a **IA paga** no modo **Minha foto falando**, a própria IA faz a sua foto falar a narração.
""")
        with t5:
            st.markdown("""
**IA paga (xAI): para vídeos ainda mais profissionais.** Fica no passo **8 · Gerar**, na seção **IA paga**, com 3 abas.

**🎬 Aba Vídeo: o que dá para fazer**
- **✍️ Texto → vídeo:** cada cena vira um vídeo de verdade criado pela IA.
- **🗣️ Minha foto falando:** a sua foto vira um apresentador que fala, com a boca sincronizada. No modelo **1.5** você escolhe entre **26 vozes**.
- **🧸 Personagem fixo:** a mesma pessoa, produto ou lugar aparece em todas as cenas. Use a sua foto e até 6 imagens de referência.
- **🖼️ Animar minhas imagens:** envie a foto do produto, da loja ou do imóvel (botão **📷** da cena) e a IA dá movimento.
- **🎞️ Início e fim:** envie a foto do começo e do fim (e, se quiser, do meio). A IA cria o movimento entre elas. Perfeito para **antes e depois** de obra ou reforma.
- **🎨 Imagens com IA:** a IA desenha uma imagem por cena. É a opção mais barata.
- **Som do clipe:** mudo (usa a sua música e voz), sons e efeitos da IA, ou **a IA fala a narração**.
- **✂️ Editar e estender:** em cada clipe pronto, **✏️** muda o clipe com uma frase (ex.: "adicione neve") e **➕** estende o clipe de 2 a 10 segundos.

**🖼️ Aba Imagens**
- **🎨 Gerar** a imagem da cena, **✏️ Editar** com uma frase (ex.: "deixe noturno", "tire o fundo") e
  **🧩 Juntar** com as referências (ex.: "coloque o produto na mão da pessoa", até 5 imagens).

**🎙️ Aba Voz da IA**
- Narração com **voz natural em português do Brasil** (26 vozes, velocidade ajustável) que **entra no arquivo baixado**.
  A duração de cada cena se ajusta ao tamanho da fala. Custa quase nada (US$ 15 por 1 milhão de letras).

**Quanto custa (aproximado, em dólar, cobrado na sua conta da xAI):**
- Vídeo **Lite**: a partir de US$ 0,02 por segundo. Um vídeo de 30 s sai por menos de 1 dólar.
- Vídeo **1.5** (melhor, vozes, início e fim): de US$ 0,08 a US$ 0,25 por segundo, conforme a resolução.
- Vídeo **Clássico** (também usado para editar e estender): US$ 0,05 a 0,07 por segundo.
- Imagens: de US$ 0,02 a 0,08 cada. Voz da IA: menos de 1 centavo por vídeo.
- O app mostra o **custo estimado antes de gerar** e o **gasto real** registrado no projeto.

**Por que algumas opções ficam apagadas?** Cada modelo da xAI faz coisas diferentes (por exemplo, **Início e fim** só existe
no modelo 1.5). O painel só deixa escolher combinações que a xAI aceita, para nada dar erro.

**Dica para começar:** faça um teste barato em **uma cena só** (botão **Gerar** da cena), com o modelo **Lite** em **480p**.
""")
        with t6:
            st.markdown("""
**"A xAI recusou a sua chave"**: copie a chave de novo, inteira, sem espaços. Se não der certo, crie outra em console.x.ai → API Keys.

**"Sua conta da xAI está sem créditos"**: a IA (roteiro, calendário, chat, clipes, imagens e voz) só funciona com créditos.
Clique em **[💳 Comprar créditos na xAI](https://console.x.ai/)** (no menu da esquerda, **Billing**). Os vídeos gratuitos continuam funcionando sem créditos.

**O roteiro não mudou / o vídeo saiu com o roteiro antigo**: gere o roteiro no **topo da página**,
confira as cenas novas no passo **Roteiro** e clique em **🎬 Finalizar vídeo** de novo.

**O vídeo baixado ficou sem voz**: a **Voz pronta** não entra no arquivo. Use **Enviar áudio** no passo **Voz**.

**A gravação travou ou ficou falhando**: deixe a aba aberta e visível, feche outras abas pesadas e use o Chrome ou o Edge.

**O arquivo saiu em .webm**: alguns navegadores gravam em WebM. O Chrome e o Edge atuais gravam em MP4.
O WebM abre no computador e sobe no YouTube; para WhatsApp/Instagram, prefira o Chrome.

**Sumiram os meus projetos**: eles ficam salvos **no navegador** onde você criou. Em outro computador ou
navegador, eles não aparecem. Use **Meus vídeos** no estúdio para abrir os antigos.

**Erro na IA paga ("sem créditos")**: clique em **[💳 Comprar créditos na xAI](https://console.x.ai/)** (no menu da esquerda, **Billing**) e compre créditos. O mesmo botão aparece na seção **IA paga** do app.
""")


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
            st.markdown(
                f"Ainda não tem a chave? 👉 **[Clique aqui para pegar a sua chave do Grok]({XAI_CHAVES_URL})** "
                "(abre o site da xAI em outra aba: entre na sua conta, clique em **API Keys** no menu da esquerda, depois em **Create API Key**, copie e cole aqui embaixo)."
            )
            xai = st.text_input(
                "Sua chave do Grok",
                type="password",
                placeholder="grok_...",
                help="Crie em console.x.ai → API Keys (veja o passo a passo logo abaixo). Criar a conta e a chave é grátis.",
            )
            entrar = st.form_submit_button("Entrar no app", type="primary", use_container_width=True)
        st.link_button("🔑 Obter minha chave do Grok", XAI_CHAVES_URL, use_container_width=True)
        st.caption("🔒 Sua chave vale só nesta sessão. Ela não fica salva no servidor e ninguém mais vê.")
        with st.expander("🔑 Primeira vez? Veja como conseguir a sua chave"):
            st.markdown(GUIA_ENTRADA)

    if entrar:
        nome, xai = nome.strip(), xai.strip()
        if not nome:
            st.error("Digite o seu nome.")
        elif not xai:
            st.error("Cole a sua chave do Grok Imagine (xAI). Clique em 🔑 Obter minha chave se ainda não tiver.")
        elif not xai_prefixo_ok(xai):
            st.error("Essa não parece uma chave do Grok. Ela começa com grok_. Copie a chave inteira.")
        else:
            with st.spinner("Conferindo a sua chave com a xAI…"):
                erro = xai_check(xai)
            if erro:
                st.error(erro)
            else:
                st.session_state.update(evs_user=nome, evs_xai=xai)
                st.rerun()


if not st.session_state.get("evs_user") or not st.session_state.get("evs_xai"):
    tela_entrada()
    st.stop()



# ---------- modelos prontos por nicho (funcionam sem IA: é só preencher) ----------
# Campos: {negocio} nome do negócio · {produto} produto/serviço em destaque · {oferta} oferta ou diferencial
#         {em_cidade} " em Campinas" (se informado) · {contato} WhatsApp ou @ (se informado)
NICHOS = {
    "🍕 Restaurante, lanchonete ou pizzaria": dict(
        estilo="vibrante", musica="animada", publico="você que está com fome",
        area="comida feita com carinho, do jeito que você gosta",
        diferencial="Ingredientes frescos, receita da casa e entrega rapidinha.",
        gancho="Sabe aquela fome de fim de tarde? A gente resolve.",
        dica1="Peça com antecedência no fim de semana e fuja da fila.",
        dica2="Experimente {produto} com a bebida da casa. A combinação é perfeita.",
        visuais=["Delicious food close-up with steam, warm restaurant light, appetizing", "Chef preparing food in a busy kitchen, flames and sizzling pan", "Happy friends sharing a meal at a cozy table", "Delivery rider arriving with a food bag at a front door"],
        hashtags=["comida", "delivery", "fome", "gastronomia", "comidaboa", "promoção", "restaurante", "pedidoonline"],
        ex=dict(negocio="Pizzaria do Zé", produto="pizza de calabresa", oferta="2 pizzas grandes por R$ 79 às sextas"),
    ),
    "💇 Salão de beleza, barbearia ou estética": dict(
        estilo="aquarela", musica="calma", publico="você que quer se sentir ainda mais bonita",
        area="beleza, cuidado e autoestima",
        diferencial="Profissionais experientes, produtos de qualidade e um atendimento que faz você se sentir em casa.",
        gancho="Já reparou como um cabelo bem cuidado muda o seu dia?",
        dica1="Hidrate os fios pelo menos uma vez por semana.",
        dica2="Evite água muito quente no cabelo: ela resseca e tira o brilho.",
        visuais=["Elegant beauty salon interior with soft light and mirrors", "Hairdresser styling a client's shiny hair, close-up", "Barber giving a precise fade haircut, cinematic", "Smiling client looking at her new look in the mirror"],
        hashtags=["beleza", "cabelo", "salaodebeleza", "autoestima", "barbearia", "estetica", "cuidados", "transformação"],
        ex=dict(negocio="Studio Bela", produto="progressiva", oferta="20% de desconto na primeira visita"),
    ),
    "🏡 Imobiliária ou corretor de imóveis": dict(
        estilo="cinema", musica="epica", publico="você que sonha com o imóvel certo",
        area="compra, venda e aluguel de imóveis com segurança",
        diferencial="Atendimento personalizado, documentação em dia e as melhores oportunidades da região.",
        gancho="Imagine abrir a porta da sua casa nova.",
        dica1="Antes de visitar, defina quanto pode pagar por mês, com folga.",
        dica2="Peça a matrícula atualizada do imóvel antes de fechar negócio.",
        visuais=["Modern house exterior at golden hour, slow drone shot", "Bright living room with large windows, smooth camera dolly", "Couple receiving house keys, smiling", "Cozy bedroom with natural light, cinematic"],
        hashtags=["imoveis", "casapropria", "corretordeimoveis", "apartamento", "imobiliaria", "casanova", "investimento", "aluguel"],
        ex=dict(negocio="Lar Ideal Imóveis", produto="apartamento de 2 quartos", oferta="entrada facilitada e parcelas a partir de R$ 1.200"),
    ),
    "🏗️ Construção, reforma ou engenharia": dict(
        estilo="empresa", musica="epica", publico="você que quer construir ou reformar sem dor de cabeça",
        area="projetos, construção e reformas com qualidade e prazo",
        diferencial="Projeto bem feito, orçamento claro e obra entregue no prazo, com responsável técnico.",
        gancho="Sabia que a maioria dos problemas de obra começa antes do primeiro tijolo?",
        dica1="Tenha um projeto aprovado antes de começar: ele evita retrabalho e gasto extra.",
        dica2="Peça um cronograma por escrito e acompanhe cada etapa da obra.",
        visuais=["Construction site with workers and crane at sunrise, cinematic", "Architect reviewing blueprints on a table, close-up", "Before and after of a renovated modern kitchen", "Finished modern house facade, slow camera move"],
        hashtags=["construção", "reforma", "engenharia", "obra", "arquitetura", "projeto", "casanova", "construcaocivil"],
        ex=dict(negocio="HE Projeto Civil", produto="projeto e reforma residencial", oferta="orçamento sem compromisso e visita técnica grátis"),
    ),
    "🩺 Clínica, consultório ou saúde": dict(
        estilo="empresa", musica="calma", publico="você que quer cuidar da saúde com quem entende",
        area="saúde e bem-estar com atendimento humanizado",
        diferencial="Profissionais qualificados, estrutura moderna e atendimento com hora marcada.",
        gancho="Quando foi a última vez que você fez um check-up?",
        dica1="Faça consultas de rotina mesmo sem sintomas: prevenir é sempre melhor.",
        dica2="Anote suas dúvidas antes da consulta para não esquecer nada.",
        visuais=["Clean modern clinic reception with soft light", "Friendly doctor talking with a patient, warm tone", "Dentist smiling with a happy patient in a bright office", "Healthy person jogging in a park at sunrise"],
        hashtags=["saude", "bemestar", "clinica", "prevenção", "qualidadedevida", "consulta", "cuidese", "saudeemdia"],
        ex=dict(negocio="Clínica Vida", produto="check-up completo", oferta="agendamento rápido e condições especiais neste mês"),
    ),
    "⚖️ Advocacia, contabilidade ou consultoria": dict(
        estilo="empresa", musica="calma", publico="você que precisa de orientação de confiança",
        area="soluções seguras para você e para a sua empresa",
        diferencial="Atendimento próximo, linguagem simples e experiência para resolver o seu caso.",
        gancho="Você sabe quais são os seus direitos nessa situação?",
        dica1="Guarde todos os comprovantes e documentos: eles fazem diferença.",
        dica2="Procure orientação antes de assinar qualquer contrato importante.",
        visuais=["Professional office with bookshelves and warm light", "Consultant explaining documents to a client at a desk", "Handshake between professional and client, close-up", "Organized desk with laptop and documents, top view"],
        hashtags=["advocacia", "direito", "contabilidade", "consultoria", "empreendedorismo", "empresa", "orientação", "seusdireitos"],
        ex=dict(negocio="Silva Consultoria", produto="abertura de empresa", oferta="primeira conversa sem custo"),
    ),
    "👗 Loja de roupas, calçados ou acessórios": dict(
        estilo="neon", musica="animada", publico="você que ama se vestir bem",
        area="moda com estilo e preço justo",
        diferencial="Peças selecionadas, novidades toda semana e atendimento que entende o seu estilo.",
        gancho="Chegou coleção nova e ela está linda!",
        dica1="Invista em peças coringa: elas combinam com quase tudo.",
        dica2="Combine uma peça de destaque com básicos para um look equilibrado.",
        visuais=["Fashion store with colorful clothes on racks, stylish lighting", "Model walking in trendy outfit on city street, slow motion", "Close-up of shoes and accessories on display", "Shopping bags and happy customer leaving a boutique"],
        hashtags=["moda", "lookdodia", "estilo", "novacoleção", "loja", "fashion", "promoção", "tendência"],
        ex=dict(negocio="Boutique Aurora", produto="vestidos de verão", oferta="leve 3 e pague 2"),
    ),
    "🏋️ Academia, personal ou esportes": dict(
        estilo="neon", musica="animada", publico="você que quer mais saúde e disposição",
        area="treino, saúde e resultado",
        diferencial="Equipamentos modernos, professores atentos e um treino feito para você.",
        gancho="Falta só começar. O resto a gente te ajuda.",
        dica1="Constância vale mais do que intensidade: treine um pouco todo dia.",
        dica2="Durma bem: é no descanso que o músculo se recupera.",
        visuais=["Energetic gym with people training, dynamic lights", "Personal trainer motivating a student, high energy", "Close-up of running shoes on a treadmill", "Group workout class with music and smiles"],
        hashtags=["academia", "treino", "saude", "fitness", "foco", "vidasaudavel", "personaltrainer", "motivação"],
        ex=dict(negocio="Academia Força Total", produto="plano mensal", oferta="primeira semana grátis"),
    ),
    "🎓 Cursos, aulas ou mentoria": dict(
        estilo="giz", musica="calma", publico="você que quer aprender e crescer",
        area="ensino prático, do básico ao avançado",
        diferencial="Aulas objetivas, material completo e acompanhamento de perto.",
        gancho="E se em poucas semanas você dominasse esse assunto?",
        dica1="Estude um pouco todos os dias, em vez de muito uma vez por semana.",
        dica2="Ensine o que aprendeu para alguém: é o jeito mais rápido de fixar.",
        visuais=["Student studying with laptop and notebook, warm light", "Teacher explaining on a whiteboard, friendly", "Online class on a laptop screen, cozy home office", "Graduate celebrating with certificate, confetti"],
        hashtags=["educação", "curso", "aprender", "estudos", "mentoria", "conhecimento", "carreira", "desenvolvimento"],
        ex=dict(negocio="Escola Saber+", produto="curso de Excel", oferta="inscrições abertas com 30% de desconto"),
    ),
    "🎉 Eventos, festas ou igreja": dict(
        estilo="aquarela", musica="calma", publico="você e toda a sua família",
        area="momentos especiais para reunir quem a gente ama",
        diferencial="Tudo preparado com carinho para você viver esse momento.",
        gancho="Separe a data: vem aí um momento especial!",
        dica1="Confirme sua presença com antecedência.",
        dica2="Traga quem você ama: quanto mais gente, melhor.",
        visuais=["Festive event decoration with warm lights and flowers", "People celebrating together, joyful atmosphere", "Close-up of an elegant invitation on a table", "Community gathering with smiles and music"],
        hashtags=["evento", "festa", "convite", "celebração", "família", "comunidade", "encontro", "especial"],
        ex=dict(negocio="Igreja Esperança", produto="culto de celebração", oferta="domingo às 19h, entrada livre"),
    ),
    "🐾 Pet shop ou veterinária": dict(
        estilo="infantil", musica="animada", publico="você que ama o seu pet",
        area="saúde, banho e carinho para o seu melhor amigo",
        diferencial="Profissionais cuidadosos, produtos de qualidade e muito amor pelos animais.",
        gancho="O seu pet merece o melhor. E a gente sabe disso!",
        dica1="Mantenha as vacinas do seu pet sempre em dia.",
        dica2="Escove os dentes do seu pet: ajuda a evitar doenças.",
        visuais=["Happy dog after a bath with fluffy fur, cute", "Veterinarian gently examining a cat", "Puppies playing in a bright pet shop", "Owner hugging a happy dog in a park"],
        hashtags=["pet", "petshop", "cachorro", "gato", "veterinario", "amorpet", "banhoetosa", "cuidadoanimal"],
        ex=dict(negocio="Pet Feliz", produto="banho e tosa", oferta="pacote de 4 banhos com 15% de desconto"),
    ),
    "🛍️ Outro negócio": dict(
        estilo="vibrante", musica="animada", publico="você",
        area="soluções feitas para você",
        diferencial="Qualidade, atendimento de verdade e preço justo.",
        gancho="Você conhece o nosso trabalho?",
        dica1="Pesquise bem antes de escolher, e prefira quem tem boas avaliações.",
        dica2="Atendimento faz diferença: escolha quem responde rápido e com clareza.",
        visuais=["Friendly small business storefront, warm light", "Owner serving a happy customer", "Close-up of quality product on display", "Team working together with smiles"],
        hashtags=["empreendedorismo", "negociolocal", "qualidade", "atendimento", "promoção", "novidade", "compreDoPequeno", "sucesso"],
        ex=dict(negocio="Meu Negócio", produto="nosso serviço", oferta="condição especial nesta semana"),
    ),
}
MODELOS = {
    "🔥 Oferta ou promoção": "oferta",
    "🏪 Conheça o meu negócio": "apresentacao",
    "💡 Dica de especialista": "dica",
}


class _Campos(dict):
    def __missing__(self, k):
        return ""


def montar_modelo(nicho, modelo, negocio, produto, oferta, cidade, contato):
    n = NICHOS[nicho]
    c = _Campos(negocio=negocio.strip() or n["ex"]["negocio"], produto=produto.strip() or n["ex"]["produto"],
                oferta=oferta.strip(), em_cidade=(" em " + cidade.strip()) if cidade.strip() else "",
                contato=(" " + contato.strip()) if contato.strip() else "")
    f = lambda t: re.sub(r"\s+([.,!?])", r"\1", re.sub(r"\s{2,}", " ", t.format_map(c))).strip()
    v = n["visuais"]
    chamada = f("Chama no WhatsApp{contato} e garanta já!") if c["contato"] else "Chama no WhatsApp e garanta já!"
    if modelo == "oferta":
        cenas = [
            ("🔥", "Promoção imperdível!", f("Atenção, {publico}! Hoje tem {produto} com uma condição especial.".replace("{publico}", n["publico"])), v[0]),
            ("💰", (c["oferta"] or "Condição especial")[:80], f(("Isso mesmo: {oferta}. " if c["oferta"] else "Uma condição especial, por tempo limitado. ") + "Aproveite enquanto dura."), v[1]),
            ("⭐", f("Qualidade {negocio}"), n["diferencial"], v[2]),
            ("📲", "Garanta o seu!", f(chamada + " {negocio}{em_cidade}."), v[3]),
        ]
        topico = f("Promoção de {produto}")
    elif modelo == "apresentacao":
        cenas = [
            ("👋", f("Prazer, {negocio}!"), f("Oi! Nós somos {negocio}{em_cidade}, e cuidamos de " + n["area"] + "."), v[0]),
            ("✨", c["produto"][:80], f("Nosso destaque é {produto}, feito com atenção a cada detalhe."), v[1]),
            ("🏆", "Por que nos escolher?", f(n["diferencial"] + (" E tem mais: {oferta}." if c["oferta"] else "")), v[2]),
            ("📲", "Fale com a gente!", f(("Fale com a gente pelo WhatsApp{contato}. " if c["contato"] else "Fale com a gente pelo WhatsApp. ") + "Vai ser um prazer te atender!"), v[3]),
        ]
        topico = f("Conheça {negocio}")
    else:
        cenas = [
            ("💡", "Você sabia?", n["gancho"], v[0]),
            ("1️⃣", "Dica número 1", f(n["dica1"]), v[1]),
            ("2️⃣", "Dica número 2", f(n["dica2"]), v[2]),
            ("📲", "Precisa de ajuda?", f("Precisa de ajuda com {produto}? Fale com {negocio}{em_cidade}." + (" WhatsApp{contato}." if c["contato"] else "")), v[3]),
        ]
        topico = f("Dicas sobre {produto}")
    scenes = [{"emoji": e, "title": t[:80], "text": tx, "visual": vi} for e, t, tx, vi in cenas]
    tags = n["hashtags"] + ([re.sub(r"\W", "", cidade.strip().lower())] if cidade.strip() else [])
    post = {
        "legenda": f"{scenes[0]['title']} {scenes[0]['text']} {scenes[2]['text']}",
        "cta": scenes[-1]["text"],
        "hashtags": [t for t in tags if t][:12],
    }
    return dict(topic=topico, scenes=scenes, post=post, style=n["estilo"], music=n["musica"],
                purpose={"oferta": "anuncio", "apresentacao": "empresa", "dica": "aula"}[modelo])


DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
FREQ_DIAS = {"3 vídeos por semana": [0, 2, 4], "5 vídeos por semana": [0, 1, 2, 3, 4], "Todo dia": [0, 1, 2, 3, 4, 5, 6]}
OBJETIVOS = ["Vender mais", "Ganhar seguidores", "Mostrar autoridade", "Lançar um produto", "Trazer clientes para a loja"]


def calendario_datas(inicio, dias_semana, quantidade):
    datas, d = [], inicio
    while len(datas) < quantidade:
        if d.weekday() in dias_semana:
            datas.append(d)
        d += timedelta(days=1)
    return datas


def prompt_mes(negocio_desc, nicho, objetivo, n, mes_txt, lang_name):
    return f"""Você é estrategista de conteúdo para redes sociais de pequenos negócios no Brasil.
Monte um calendário com {n} ideias de vídeos curtos (Reels/TikTok) para o período de {mes_txt}.
Negócio: {negocio_desc or "não informado"}
Nicho: {nicho}
Objetivo principal: {objetivo}
Idioma: {lang_name}

Regras:
- Varie os tipos: Oferta, Dica, Bastidores, Depoimento, Pergunta, Antes e depois, Apresentação, Data comemorativa, Tendência.
- Considere datas comemorativas do Brasil nesse período, se fizer sentido para o negócio.
- "titulo": tema do vídeo em até 8 palavras.
- "gancho": a primeira frase do vídeo, que prende a atenção (até 15 palavras).
- "descricao": o que mostrar no vídeo, em uma frase.
- NÃO invente preços, telefones ou endereços.

Responda somente com JSON:
{{"ideias":[{{"tipo":"Dica","titulo":"...","gancho":"...","descricao":"..."}}]}}"""


def criar_roteiro_ia(topic, servico, purpose_name, duration, fmt_name, lang_name, visual_name, music=None):
    dados = groq_script(
        build_prompt(topic, purpose_name, duration, FORMATS[fmt_name], lang_name, servico, visual_name if VISUAIS.get(visual_name) else ""),
        st.session_state["evs_xai"],
    )
    scenes = dados.get("scenes") if isinstance(dados, dict) else dados
    if not scenes:
        raise RuntimeError("O roteiro veio vazio. Tente descrever melhor o tema.")
    post = dados.get("post") if isinstance(dados, dict) and isinstance(dados.get("post"), dict) else None
    injetar(topic, scenes, post, PURPOSES[purpose_name], VISUAIS.get(visual_name, ""), servico, duration, FORMATS[fmt_name], LANGS[lang_name], music)
    return len(scenes)


def injetar(topic, scenes, post, purpose, style, servico, duration, fmt, lang, music=None):
    st.session_state["evs_inject"] = {
        "nonce": f"{time.time():.3f}", "topic": topic, "purpose": purpose, "style": style or "",
        "styleDesc": servico, "duration": duration, "format": fmt, "lang": lang, "scenes": scenes,
        "post": post or None, "music": music or "",
    }
    st.session_state["evs_post"] = post or None


def mostrar_erro(e):
    st.error(str(e))
    if "crédito" in str(e):
        st.link_button("💳 Comprar créditos na xAI", XAI_CREDITOS_URL)


def avisar(msg):
    st.session_state["evs_msg"] = msg
    st.success(msg)


def mostrar_post():
    if st.session_state.get("evs_msg"):
        st.success(st.session_state["evs_msg"])
    post = st.session_state.get("evs_post")
    if not post:
        return
    with st.expander("📝 Texto do post para copiar (legenda, chamada e hashtags)", expanded=True):
        tags = " ".join("#" + str(h).lstrip("#").replace(" ", "") for h in (post.get("hashtags") or []))
        st.caption("Clique no ícone de copiar no canto de cada quadro.")
        st.code(f"{post.get('legenda', '').strip()}\n\n{post.get('cta', '').strip()}\n\n{tags}".strip(), language=None, wrap_lines=True)
        st.caption("O mesmo texto também fica no estúdio, no passo 8 · Gerar, para você copiar depois de baixar o vídeo.")


# ---------- topo: vídeos gratuitos · vídeos pagos ----------
NOTA_PAGOS = "<div style='border:1px solid #ff5a36;background:#ff5a3622;border-radius:12px;padding:12px 16px;display:flex;gap:12px;align-items:flex-start;margin-bottom:10px'><span style='font-size:22px;line-height:1.2'>💸</span><div style='display:flex;flex-direction:column;gap:6px'><b style='font-size:16px'>Vídeos profissionais sem assinatura mensal.</b><span>Este app é uma ponte entre você e uma IA de vídeo profissional (Grok Imagine, da xAI). Em vez de pagar uma assinatura todo mês, você usa a sua própria chave e paga só pelo vídeo que gerar, direto na sua conta da xAI, a partir de poucos reais por vídeo.</span><span style='opacity:.75;font-size:13px'>O custo exato aparece antes de você gerar.</span></div></div>"

ca, cb = st.columns([5, 1])
ca.markdown(
    f"<h2 style='margin-bottom:0'>🎬 Olá, {html.escape(st.session_state['evs_user'])}!</h2>"
    "<p style='opacity:.75;margin-top:4px'>Faça vídeos <b>gratuitos</b> com modelos prontos ou vídeos <b>pagos</b> com a IA profissional. "
    "Depois é só ajustar e clicar em <b>🎬 Finalizar vídeo</b>, embaixo da prévia.</p>",
    unsafe_allow_html=True,
)
if cb.button("Sair", use_container_width=True):
    for k in ("evs_user", "evs_xai", "evs_inject", "evs_chat", "evs_ponte_out", "evs_ponte_feito", "evs_ponte_ultimo", "evs_post", "evs_mes", "evs_msg"):
        st.session_state.pop(k, None)
    st.rerun()

tutorial(aberto=st.session_state.get("evs_tut_aberto", True))  # fica aberto na sessão; a pessoa fecha quando quiser

aba_gratis, aba_paga = st.tabs(["🎬 Vídeos gratuitos", "⭐ Vídeos pagos (IA profissional)"])
with aba_gratis:
    st.markdown(
        "<div style='font-size:14.5px;line-height:1.55;margin:4px 0 8px'><b>Sem gastar nada.</b> Escolha um <b>modelo pronto do seu nicho</b> abaixo "
        "(ou escreva o seu roteiro direto no estúdio, passo <b>6 · Roteiro</b>). O vídeo sai com fundos animados, a sua marca, "
        "música e legendas. No fim, clique em <b>🎬 Finalizar vídeo</b>, embaixo da prévia.</div>",
        unsafe_allow_html=True,
    )
aba_modelos = aba_gratis
with aba_paga:
    st.markdown(NOTA_PAGOS, unsafe_allow_html=True)
    lb1, lb2, _ = st.columns([1, 1, 2])
    lb1.link_button("💳 Comprar créditos na xAI", XAI_CREDITOS_URL, type="primary", use_container_width=True)
    lb2.link_button("🔑 Pegar ou trocar minha chave", XAI_CHAVES_URL, use_container_width=True)
    aba_ia, aba_mes, aba_pro = st.tabs(["✨ Roteiro com IA", "📅 Meu mês de conteúdo", "🎥 Clipes, imagens e voz"])
with aba_pro:
    st.markdown("""
**Deixe o vídeo com cara de produção profissional.** Tudo é feito no estúdio, logo abaixo:

- **Escolhendo cada detalhe:** no estúdio, passo **8 · Gerar**, seção **🤖 IA paga**, com 3 abas:
  - **🎬 Vídeo:** cenas de vídeo criadas pela IA, **sua foto falando** (26 vozes), personagem fixo, animar as suas fotos, **início e fim** (antes e depois), editar e estender clipes.
  - **🖼️ Imagens:** gerar, editar com uma frase e juntar imagens.
  - **🎙️ Voz da IA:** narração natural em português que **entra no arquivo baixado**.
- **Para terminar:** clique em **🎬 Finalizar vídeo**, embaixo da prévia. É o mesmo botão para vídeos gratuitos e pagos.

**Quanto custa (aproximado):** vídeo Lite a partir de US$ 0,02 por segundo (30 s por menos de 1 dólar) · vídeo 1.5 de US$ 0,08 a 0,25 por segundo ·
imagens de US$ 0,02 a 0,08 · voz menos de 1 centavo por vídeo. **Dica:** teste antes com **uma cena só**, modelo **Lite**, em **480p**.
""")

with aba_ia:
    st.caption("A IA escreve o roteiro e o texto do post a partir do seu tema. Usa créditos da xAI: menos de 1 centavo de dólar por roteiro.")
    with st.form("roteiro"):
        topic = st.text_input("Tema do vídeo", placeholder="Ex.: Promoção de pizza de sexta, 2 por R$ 79")
        style_desc = st.text_area(
            "Descreva o seu serviço ou produto",
            placeholder="O que é, o que faz, para quem é, diferenciais, preço e contato. Ex.: Pizzaria do Zé, delivery em Campinas, massa de fermentação natural, 2 pizzas grandes por R$ 79 às sextas, pedidos pelo WhatsApp (19) 99999-0000",
            height=110,
            help="Quanto mais detalhes reais você colocar, melhor o roteiro. A IA usa só o que estiver aqui, sem inventar preços ou contatos.",
            key="evs_servico",
        )
        c1, c2, c3, c4, c5 = st.columns(5)
        purpose_name = c1.selectbox("Finalidade", list(PURPOSES))
        fmt_name = c2.selectbox("Formato", list(FORMATS))
        duration = c3.selectbox("Duração", [15, 30, 60, 90], index=1, format_func=lambda d: f"{d} segundos")
        lang_name = c4.selectbox("Idioma", list(LANGS))
        visual_name = c5.selectbox("Estilo visual", list(VISUAIS))
        sent = st.form_submit_button("✨ Gerar roteiro com IA", type="primary")
    if sent:
        if not topic.strip():
            st.error("Escreva o tema do vídeo.")
        else:
            with st.spinner("Escrevendo o roteiro e o texto do post…"):
                try:
                    n = criar_roteiro_ia(topic.strip(), style_desc.strip(), purpose_name, duration, fmt_name, lang_name, visual_name)
                    st.session_state["evs_msg"] = f"✅ Roteiro pronto com {n} cenas. Ele já abriu no estúdio abaixo, no passo Roteiro."
                except Exception as e:  # noqa: BLE001
                    mostrar_erro(e)

with aba_modelos:
    st.markdown("**📋 Modelos prontos por nicho** · escolha o seu nicho e o tipo de vídeo, preencha 3 campos e pronto. Instantâneo e grátis.")
    with st.form("modelo"):
        m1, m2 = st.columns(2)
        nicho = m1.selectbox("Seu nicho", list(NICHOS), key="m_nicho")
        modelo_nome = m2.selectbox("Tipo de vídeo", list(MODELOS), key="m_tipo")
        exn = NICHOS[nicho]["ex"]
        f1, f2 = st.columns(2)
        # chaves fixas: o exemplo muda com o nicho, mas o que a pessoa digitou não pode se perder
        negocio = f1.text_input("Nome do negócio", placeholder=f"Ex.: {exn['negocio']}", key="m_negocio")
        produto = f2.text_input("Produto ou serviço em destaque", placeholder=f"Ex.: {exn['produto']}", key="m_produto")
        oferta = st.text_input("Oferta, preço ou diferencial (opcional)", placeholder=f"Ex.: {exn['oferta']}", key="m_oferta")
        f3, f4, f5 = st.columns(3)
        cidade = f3.text_input("Cidade ou bairro (opcional)", placeholder="Ex.: Campinas", key="m_cidade")
        contato = f4.text_input("WhatsApp ou @ (opcional)", placeholder="Ex.: (19) 99999-0000", key="m_contato")
        fmt_m = f5.selectbox("Formato", list(FORMATS), key="fmt_modelo")
        usar = st.form_submit_button("📋 Criar vídeo com este modelo", type="primary")
    if usar:
        if not negocio.strip() or not produto.strip():
            st.error("Preencha o nome do negócio e o produto ou serviço.")
        else:
            r = montar_modelo(nicho, MODELOS[modelo_nome], negocio, produto, oferta, cidade, contato)
            injetar(r["topic"], r["scenes"], r["post"], r["purpose"], r["style"], f"{negocio}. {produto}. {oferta}".strip(". "),
                    30, FORMATS[fmt_m], "pt-BR", r["music"])
            st.session_state["evs_msg"] = "✅ Vídeo montado com o modelo! Ele já abriu no estúdio abaixo, no passo Roteiro. Ajuste o que quiser."
    st.caption("Dica: cadastre o seu logo, cores e WhatsApp em 🎨 Minha marca, no topo do estúdio. Todo vídeo sai com a sua identidade e uma cena final de contato com QR code.")

with aba_mes:
    st.caption("A IA monta o seu calendário de vídeos para o mês. Depois é só clicar em 🎬 Criar este vídeo em cada ideia. Usa créditos da xAI: cerca de 1 centavo de dólar pelo mês inteiro.")
    with st.form("mes"):
        servico_mes = st.text_area("Descreva o seu negócio", value=st.session_state.get("evs_servico", ""), height=90, key="mes_servico",
                                   placeholder="O que você vende, para quem, diferenciais e cidade. Ex.: HE Projeto Civil, projetos e reformas residenciais em Campinas.")
        g1, g2, g3, g4 = st.columns(4)
        nicho_mes = g1.selectbox("Nicho", list(NICHOS), key="nicho_mes")
        objetivo = g2.selectbox("Objetivo", OBJETIVOS)
        freq = g3.selectbox("Frequência", list(FREQ_DIAS), index=1)
        inicio = g4.date_input("Começar em", value=datetime.now().date(), format="DD/MM/YYYY")
        gerar_mes = st.form_submit_button("📅 Montar meu mês de conteúdo", type="primary")
    if gerar_mes:
        if not servico_mes.strip():
            st.error("Descreva o seu negócio para a IA montar ideias que façam sentido.")
        else:
            n_ideias = min(30, len(FREQ_DIAS[freq]) * 4)
            datas = calendario_datas(inicio, FREQ_DIAS[freq], n_ideias)
            mes_txt = f"{datas[0].strftime('%d/%m/%Y')} a {datas[-1].strftime('%d/%m/%Y')}"
            with st.spinner(f"Montando {n_ideias} ideias de vídeo…"):
                try:
                    dados = groq_json(prompt_mes(servico_mes.strip(), nicho_mes, objetivo, n_ideias, mes_txt, "Português"), st.session_state["evs_xai"])
                    ideias = [i for i in (dados.get("ideias") or []) if isinstance(i, dict)][:n_ideias]
                    if not ideias:
                        raise RuntimeError("A IA não devolveu ideias. Tente de novo.")
                    st.session_state["evs_mes"] = {
                        "servico": servico_mes.strip(), "nicho": nicho_mes, "objetivo": objetivo,
                        "ideias": [dict(i, data=d.isoformat()) for i, d in zip(ideias, datas)],
                    }
                    for k in [k for k in st.session_state if str(k).startswith("mes_feito_")]:
                        del st.session_state[k]
                    st.success(f"Pronto! {len(ideias)} ideias no seu calendário.")
                except Exception as e:  # noqa: BLE001
                    mostrar_erro(e)
    mes = st.session_state.get("evs_mes")
    if mes:
        n_feitos = sum(1 for i in range(len(mes["ideias"])) if st.session_state.get(f"mes_feito_{i}"))
        st.markdown(f"**Seu calendário** · {n_feitos} de {len(mes['ideias'])} vídeos feitos")
        st.progress(n_feitos / max(1, len(mes["ideias"])))
        semana_atual = None
        for idx, ideia in enumerate(mes["ideias"]):
            d = datetime.fromisoformat(ideia["data"]).date()
            sem = d.isocalendar()[1]
            if sem != semana_atual:
                semana_atual = sem
                st.markdown(f"##### Semana de {(d - timedelta(days=d.weekday())).strftime('%d/%m')}")
            with st.container(border=True):
                k1, k2 = st.columns([4, 1.3])
                feito = bool(st.session_state.get(f"mes_feito_{idx}"))
                k1.markdown(
                    f"{'✅' if feito else '🗓️'} **{DIAS_SEMANA[d.weekday()]} {d.strftime('%d/%m')}** · "
                    f"`{html.escape(str(ideia.get('tipo', 'Vídeo')))}` · **{html.escape(str(ideia.get('titulo', '')))}**  \n"
                    f"🎣 *{html.escape(str(ideia.get('gancho', '')))}*  \n{html.escape(str(ideia.get('descricao', '')))}"
                )
                if k2.button("🎬 Criar este vídeo", key=f"mes_criar_{idx}", use_container_width=True):
                    with st.spinner("Escrevendo o roteiro e o texto do post…"):
                        try:
                            topico = f"{ideia.get('titulo', '')}. Comece com: {ideia.get('gancho', '')}. Mostrar: {ideia.get('descricao', '')}"
                            finalidade = "Anúncio / Vendas" if "ferta" in str(ideia.get("tipo", "")) else "Reels e Stories"
                            criar_roteiro_ia(topico, mes["servico"], finalidade, 30, "Vertical 9:16", "Português", "Automático (pela finalidade)")
                            st.session_state[f"mes_feito_{idx}"] = True  # já marca como feito
                            st.session_state["evs_msg"] = f"✅ Roteiro da ideia de {d.strftime('%d/%m')} pronto! Ele abriu no estúdio abaixo, no passo Roteiro."
                            st.rerun()
                        except Exception as e:  # noqa: BLE001
                            mostrar_erro(e)
                k2.checkbox("Feito", key=f"mes_feito_{idx}")
        linhas = ["data;dia;tipo;titulo;gancho;descricao"] + [
            ";".join([i["data"], DIAS_SEMANA[datetime.fromisoformat(i["data"]).weekday()]] + [str(i.get(c, "")).replace(";", ",").replace("\n", " ") for c in ("tipo", "titulo", "gancho", "descricao")])
            for i in mes["ideias"]
        ]
        st.download_button("⬇ Baixar calendário (planilha CSV)", ("﻿" + "\n".join(linhas)).encode("utf-8"),
                           file_name="meu-mes-de-conteudo.csv", mime="text/csv")

mostrar_post()


# ---------- estúdio ----------
inject = dict(st.session_state.get("evs_inject") or {})
inject["engine"] = "Grok"
inject["userName"] = st.session_state["evs_user"]
ponte_ok = montar_ponte()
if ponte_ok:
    inject["ponte"] = True  # pedidos à xAI passam pelo servidor; a chave nunca vai para o navegador
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

chat_duvidas()
