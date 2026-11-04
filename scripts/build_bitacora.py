#!/usr/bin/env python3
"""Generar la bitácora HTML offline desde Markdown. Requiere mistune."""
import html
from pathlib import Path
import re

import mistune

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "docs/bitacora.md").read_text()
markdown = mistune.create_markdown(escape=True, plugins=["table"])
parts = re.split(r"^## (.+)$", source, flags=re.M)
entries, links = [], []
labels = {"aws": "Verificado en AWS", "local": "Verificado en local", "pendiente": "Pendiente"}
for index in range(1, len(parts), 2):
    number = (index + 1) // 2
    title, body = parts[index], parts[index + 1]
    meta = re.search(r"<!-- estado: (\w+); area: (\w+) -->", body)
    status, area = meta.groups()
    body = body.replace(meta.group(0), "")
    date, _, heading = title.partition(" · ")
    target = "registro-" + str(number).zfill(2)
    entries.append(f'''<article class="entry" id="{target}" data-status="{status}" data-area="{area}">
      <div class="entry-margin"><span>{html.escape(date)}</span><b>{str(number).zfill(2)}</b></div>
      <div class="entry-body"><header><span class="badge {status}">{labels[status]}</span>
      <h2>{html.escape(heading)}</h2></header><div class="prose">{markdown(body)}</div></div></article>''')
    links.append(f'<a href="#{target}" data-entry="{target}"><small>{str(number).zfill(2)}</small>{html.escape(heading)}</a>')

page = r'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PATAPORTE · Bitácora de implementación</title>
<style>
:root{--paper:#f7f5ef;--ink:#263d32;--muted:#6b756a;--line:#d7ddce;--orange:#ac5936;--green:#2d5c43;--white:#fffefa}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:150px}body{margin:0;background:var(--paper);color:var(--ink);font-family:"Avenir Next","Trebuchet MS",sans-serif;line-height:1.65}a{color:var(--green);text-underline-offset:3px}button,input{font:inherit}button,a,input{outline-offset:5px}button{cursor:pointer}.layout{display:grid;grid-template-columns:240px minmax(0,1fr);max-width:1500px;margin:auto}.sidebar{padding:32px 23px;position:sticky;top:0;height:100vh;overflow:auto;border-right:1px solid var(--line);background:#eef1e7}.brand{font-size:12px;font-weight:800;letter-spacing:2px}.sidebar>p{font-family:Georgia,serif;font-size:25px;line-height:1.2;margin:10px 0 23px}.sidebar nav a{display:flex;align-items:baseline;gap:9px;font-size:11px;padding:8px 0;text-decoration:none;color:var(--muted);border-bottom:1px solid #dfe3d8}.sidebar nav a:hover{color:var(--green)}nav small{font-family:monospace;font-size:10px;color:var(--orange)}.back{display:block;font-size:11px;margin-top:24px}main{min-width:0}.masthead{padding:47px 54px 28px}.kicker{font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:var(--orange)}h1{font-family:Georgia,serif;font-weight:400;font-size:clamp(42px,5vw,66px);line-height:1.08;letter-spacing:-2px;margin:16px 0 21px}.lead{max-width:710px;font-size:14px;color:var(--muted)}.masthead .branch{font:10px monospace;overflow-wrap:anywhere;margin-top:23px}.rule{display:flex;gap:24px;flex-wrap:wrap;border-top:1px solid var(--line);padding-top:17px;margin-top:25px;font-size:11px}.rule b{color:var(--orange)}.toolbar{position:sticky;top:0;z-index:10;padding:14px 54px;background:rgba(247,245,239,.97);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.searchline{display:flex;gap:15px;align-items:center}.searchline label{font-size:10px;text-transform:uppercase;letter-spacing:1px;font-weight:800}.searchline input{min-width:0;flex:1;padding:9px 13px;border:1px solid var(--line);border-radius:4px;background:var(--white);color:var(--ink);font-size:12px}.filters{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:12px}.filters button{border:1px solid var(--line);background:none;color:var(--muted);padding:5px 10px;font-size:10px;border-radius:20px}.filters button[aria-pressed=true]{background:var(--green);border-color:var(--green);color:white}.filters output{font:10px monospace;color:var(--muted);margin-left:auto}.journal{padding:0 54px 45px}.entry{display:grid;grid-template-columns:96px minmax(0,1fr);gap:22px;padding:35px 0 38px;border-bottom:1px solid var(--line)}.entry[hidden],nav a[hidden]{display:none}.entry-margin span{display:block;font:9px monospace;white-space:nowrap;color:var(--muted);margin-top:5px}.entry-margin b{display:block;font:44px Georgia,serif;color:#b3bda8;margin-top:17px;font-weight:400}.badge{font-size:9px;font-weight:700;border:1px solid var(--line);padding:4px 8px;border-radius:3px}.badge.aws{color:var(--green);background:#e6eddf}.badge.local{color:#6e663c;background:#f1edda}.badge.pendiente{color:#9c4c2d;background:#f6e8dd}.entry h2{font:400 30px/1.17 Georgia,serif;letter-spacing:-.6px;margin:16px 0 20px}.prose{font-size:12px;line-height:1.85;overflow-wrap:anywhere}.prose p{margin:0 0 14px}.prose strong{font-weight:750;color:var(--ink)}code{font-size:.92em;background:#e9ece2;border-radius:3px;padding:2px 4px;overflow-wrap:anywhere}pre{overflow:auto;background:#e9ece2;padding:15px}pre code{padding:0}table{border-collapse:collapse;width:100%;font-size:11px}td,th{padding:9px;border:1px solid var(--line);text-align:left}footer{padding:23px 54px 36px;font-size:11px;color:var(--muted);display:flex;gap:20px;flex-wrap:wrap}.empty{padding:35px 0;color:var(--muted);font-size:13px}.print{margin-left:auto;background:none;border:0;text-decoration:underline;color:var(--muted);font-size:11px}@media(max-width:1000px){.layout{grid-template-columns:190px minmax(0,1fr)}.sidebar{padding:25px 18px}.masthead{padding:35px 32px 24px}.toolbar{padding:13px 32px}.journal{padding:0 32px 25px}.entry{grid-template-columns:80px minmax(0,1fr);gap:16px}footer{padding:23px 32px}}@media(max-width:720px){.layout{display:block}.sidebar{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line);padding:15px 22px;display:flex;justify-content:space-between;align-items:center}.sidebar nav,.sidebar>p{display:none}.sidebar .back{margin:0}.masthead{padding:30px 22px 22px}.toolbar{padding:12px 22px}.journal{padding:0 22px 25px}.entry{display:block;padding:28px 0}.entry-margin{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.entry-margin b{font:13px monospace;margin:0}.entry-margin span{margin:0}.entry h2{font-size:27px}.filters{gap:6px}.filters output{width:100%;margin:5px 0 0}.searchline label{display:none}footer{padding:22px}.rule{gap:12px}h1{letter-spacing:-1.4px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{body{background:white}.layout{display:block}.sidebar,.toolbar,.print{display:none}.entry[hidden]{display:grid}.entry{break-inside:avoid}.masthead,.journal,footer{padding-left:20px;padding-right:20px}a{color:inherit}.badge{background:white!important}.entry h2{font-size:24px}h1{font-size:42px}.prose{font-size:10px}}
</style></head><body><div class="layout">
<aside class="sidebar"><a class="brand" href="guia-despliegue-aws.html">PATAPORTE</a><p>Registro de<br>implementación.</p><nav aria-label="Entradas de la bitácora">__NAV__</nav><a class="back" href="guia-despliegue-aws.html">← Volver a la guía AWS</a></aside>
<main><header class="masthead"><div class="kicker">Cuaderno de proyecto · AWS Academy</div><h1>Lo que hicimos.<br>Por qué lo hicimos.</h1><p class="lead">La historia del despliegue, con decisiones, pruebas y límites. Cada registro distingue lo comprobado en AWS, lo verificado en local y lo que todavía requiere trabajo.</p><div class="branch">feature/preparacion-despliegue-aws</div><div class="rule"><span>Actualización <b>04 noviembre 2026</b></span><span>Última verificación AWS <b>04 noviembre 2026</b></span><span><b>__TOTAL__</b> registros</span></div></header>
<section class="toolbar" aria-label="Buscar y filtrar"><div class="searchline"><label for="search">Buscar</label><input id="search" type="search" placeholder="Fotos, migraciones, decisiones, pruebas…" autocomplete="off"></div><div class="filters" role="group" aria-label="Estado de verificación"><button type="button" data-filter="all" aria-pressed="true">Todos</button><button type="button" data-filter="aws" aria-pressed="false">En AWS</button><button type="button" data-filter="local" aria-pressed="false">En local</button><button type="button" data-filter="pendiente" aria-pressed="false">Pendientes</button><output id="count" aria-live="polite">__TOTAL__ registros</output></div></section>
<div class="journal">__ENTRIES__<p class="empty" id="empty" hidden>No hay registros con ese filtro. Probá otra búsqueda.</p></div><footer><a href="bitacora.md">Fuente Markdown</a><a href="evidencias/preparacion-cloud-2026-11-03.json">Resultados de esta sesión</a><span>Los hitos anteriores se consolidaron a partir de sus evidencias.</span><button type="button" class="print" id="print">Imprimir / guardar PDF</button></footer></main></div>
<script>
(function(){
  const entries=Array.from(document.querySelectorAll('.entry'));
  const search=document.getElementById('search');
  const buttons=Array.from(document.querySelectorAll('[data-filter]'));
  const count=document.getElementById('count');
  let filter='all';
  const normalize=text=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const texts=new Map(entries.map(entry=>[entry,normalize(entry.textContent)]));
  function update(){
    const words=normalize(search.value).split(/\s+/).filter(Boolean);
    let visible=0;
    entries.forEach(entry=>{
      const match=(filter==='all'||entry.dataset.status===filter)&&words.every(word=>texts.get(entry).includes(word));
      entry.hidden=!match;
      document.querySelector('[data-entry="'+entry.id+'"]').hidden=!match;
      if(match)visible++;
    });
    count.textContent=visible+' de '+entries.length+' registros';
    document.getElementById('empty').hidden=visible!==0;
  }
  search.addEventListener('input',update);
  buttons.forEach(button=>button.addEventListener('click',()=>{
    filter=button.dataset.filter;
    buttons.forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
    update();
  }));
  document.getElementById('print').addEventListener('click',()=>window.print());
  update();
})();
</script></body></html>'''

page = page.replace("__NAV__", "\n".join(links)).replace("__ENTRIES__", "\n".join(entries)).replace("__TOTAL__", str(len(entries)))
target = ROOT / "docs/bitacora.html"
target.write_text(page)
print(f"Generated {target.name}: {len(entries)} entries")
