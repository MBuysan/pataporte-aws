#!/usr/bin/env python3
"""Generate the self-contained HTML guide. Requires mistune; pygments is optional."""

from pathlib import Path
import html
import json
import math
import re

import mistune

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "guia-despliegue-aws.md"
OUTPUT = SOURCE.with_suffix(".html")

try:
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name
    SYNTAX_CSS = HtmlFormatter(style="native").get_style_defs(".codeblock")
except ImportError:
    highlight = None
    SYNTAX_CSS = ""


PAW = '<svg viewBox="0 0 32 32" fill="currentColor" aria-hidden="true"><ellipse cx="8" cy="10" rx="3.2" ry="4.3" transform="rotate(-27 8 10)"/><ellipse cx="16" cy="6.8" rx="3.2" ry="4.3"/><ellipse cx="24" cy="10" rx="3.2" ry="4.3" transform="rotate(27 24 10)"/><path d="M16 13c-4 0-4.2 4.6-7.5 7.1-2.7 2-2.6 6.2.8 7.3 2.4.8 4.2-1 6.7-1s4.3 1.8 6.7 1c3.4-1.1 3.5-5.3.8-7.3C20.2 17.6 20 13 16 13Z"/></svg>'
CHEVRON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m8 5 7 7-7 7"/></svg>'
SEARCH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.5"/><path d="m16 16 4.5 4.5"/></svg>'
PRINT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M6 8V3h12v5M6 17H3V9h18v8h-3M6 14h12v7H6z"/><path d="M17 11h1"/></svg>'
MENU = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg>'

SERVICES = {
    "cloudfront": {"name": "CloudFront", "label": "Distribución global", "owner": "C", "stage": 8, "text": "Entrega la web cerca de los usuarios. Las rutas /api/* viajan al ALB sin cachear respuestas privadas. Acceso global y recuperación de una región son objetivos distintos."},
    "s3": {"name": "S3", "label": "Frontend privado", "owner": "C", "stage": 8, "text": "La web vive en un bucket privado accesible desde CloudFront mediante OAC. Las fotos y los certificados usan otro bucket y autorización con enlaces temporales."},
    "alb": {"name": "ALB", "label": "Entrada de la API", "owner": "A", "stage": 6, "text": "Recibe /api/* desde CloudFront y distribuye las solicitudes a tareas saludables. Su Target Group es de tipo ip cuando las tareas usan awsvpc."},
    "ecs": {"name": "ECS + EC2", "label": "FastAPI en 2 zonas", "owner": "A", "stage": 9, "text": "ECS mantiene las tareas de la API. Un capacity provider administra los hosts EC2 del Auto Scaling Group. Tareas y servidores tienen mecanismos de escalado distintos."},
    "rds": {"name": "RDS", "label": "PostgreSQL Multi-AZ", "owner": "A + B", "stage": 7, "text": "Es la fuente de datos clínicos. Multi-AZ permite recuperación ante fallos zonales; migraciones, backups y pruebas de restauración completan el diseño."},
    "outbox": {"name": "Outbox", "label": "Publicador en ECS", "owner": "B", "stage": 10, "text": "El cambio de negocio y su evento se guardan en la misma transacción PostgreSQL. El publicador entrega los pendientes a SQS y puede reintentar sin perder eventos."},
    "sqs": {"name": "SQS", "label": "Trabajos + DLQ", "owner": "B", "stage": 10, "text": "Amortigua picos y desacopla la API del procesamiento. Los trabajos pueden repetirse. Después de los intentos previstos, los fallidos terminan en una cola de errores."},
    "lambda": {"name": "Lambda", "label": "PDF y correo", "owner": "B", "stage": 11, "text": "Procesa trabajos acotados, guarda el PDF en S3 y envía el correo. Debe propagar fallos, limitar concurrencia y gestionar duplicados; SMTP no garantiza entrega exactamente una vez."},
    "dynamo": {"name": "DynamoDB", "label": "Estado e idempotencia", "owner": "B", "stage": 11, "text": "Coordina ejecuciones repetidas y guarda el estado operativo. No reemplaza PostgreSQL como historia clínica. Sus claves e índices responden a consultas concretas."},
}


def architecture():
    def node(key):
        item = SERVICES[key]
        return '<button type="button" class="service-node" data-service="' + key + '" aria-pressed="false"><b>' + item["name"] + '</b><span>' + item["label"] + '</span></button>'

    lanes = [
        ("Web global", ["cloudfront", "s3"]),
        ("API privada", ["alb", "ecs", "rds"]),
        ("Trabajo asíncrono", ["outbox", "sqs", "lambda", "dynamo"]),
    ]
    result = '<div class="architecture" aria-label="Mapa interactivo de la arquitectura"><div class="map-caption"><span>MAPA DEL SISTEMA</span><span>Seleccioná un servicio para explorarlo</span></div>'
    for label, keys in lanes:
        result += '<div class="flow-lane"><span class="lane-label">' + label + '</span><div class="flow-chain">'
        result += '<span class="flow-arrow" aria-hidden="true">→</span>'.join(node(key) for key in keys)
        result += '</div></div>'
    result += '<p class="flow-note">CloudFront envía /api/* al ALB. Outbox lee PostgreSQL; Lambda también guarda archivos en S3 y llama al proveedor de correo.</p>'
    result += '<div id="service-detail" class="service-detail" aria-live="polite"><span class="eyebrow">EXPLORÁ EL MAPA</span><p>Cada servicio tiene un trabajo concreto. Seleccioná uno para ver su propósito y quién lo implementa.</p></div></div>'
    return result


class Renderer(mistune.HTMLRenderer):
    def block_code(self, code, info=None):
        language = (info or "text").split()[0]
        if language == "mermaid":
            return architecture()
        result = html.escape(code)
        if highlight:
            try:
                result = highlight(code, get_lexer_by_name(language), HtmlFormatter(nowrap=True))
            except Exception:
                pass
        return '<div class="code-wrap"><div class="code-head"><span>' + html.escape(language) + '</span><button type="button" class="copy-code">Copiar código</button></div><pre class="codeblock"><code>' + result + '</code></pre></div>\n'


markdown = mistune.create_markdown(renderer=Renderer(escape=True), plugins=["table", "strikethrough"])
source = SOURCE.read_text()
parts = re.split(r"^## (.+)$", source, flags=re.M)
intro = parts[2]
chapters = []
for index in range(3, len(parts), 2):
    heading, body = parts[index], parts[index + 1]
    number = int(heading.split(".", 1)[0])
    title = heading.split(". ", 1)[1]
    chapters.append({"number": number, "title": title, "body": body})
assert len(chapters) == 20

ROLES = {
    1: "ABC", 2: "ABC", 3: "ABC", 4: "B", 5: "A",
    6: "A", 7: "AB", 8: "BC", 9: "AC", 10: "B",
    11: "B", 12: "B", 13: "C", 14: "AC", 15: "ABC",
    16: "ABC", 17: "ABC", 18: "ABC", 19: "AC", 20: "ABC",
}
SHORT_TITLES = [
    "La arquitectura", "Cuenta y permisos", "Repositorio y contratos", "Preparar la aplicación",
    "CloudFormation", "Red y permisos", "RDS y migraciones", "S3 y frontend", "ECS sobre EC2",
    "Outbox y SQS", "Lambda y DynamoDB", "Recordatorios y fotos", "GitHub Actions", "Observabilidad",
    "Pruebas y recuperación", "Segunda región", "Equipo y entrega", "Resolver problemas",
    "Apagar el laboratorio", "Fuentes del curso",
]
GROUPS = {1: "Preparar", 5: "Construir", 10: "Automatizar", 15: "Demostrar"}
nav, articles = [], []
read_minutes = math.ceil(len(source.split()) / 210)
for chapter in chapters:
    n, title = chapter["number"], chapter["title"]
    roles = ROLES[n]
    minute = max(1, math.ceil(len(chapter["body"].split()) / 210))
    if n in GROUPS:
        nav.append('<div class="nav-group">' + GROUPS[n] + '</div>')
    nav.append('<a class="nav-link" href="#etapa-' + str(n).zfill(2) + '" data-nav="' + str(n) + '"><span class="nav-number">' + str(n).zfill(2) + '</span><span>' + SHORT_TITLES[n - 1] + '</span><span class="nav-done" aria-hidden="true">✓</span></a>')
    role_label = "Equipo" if roles == "ABC" else " + ".join(roles)
    rendered = markdown(chapter["body"])
    articles.append(
        '<article class="chapter" id="etapa-' + str(n).zfill(2) + '" data-number="' + str(n) + '" data-roles="' + roles + '">'
        '<details class="chapter-details"><summary><span class="chapter-num">' + str(n).zfill(2) + '</span>'
        '<span class="chapter-heading"><span class="chapter-title">' + html.escape(title) + '</span>'
        '<span class="chapter-meta"><span class="owner-pill">' + role_label + '</span><span>' + str(minute) + ' min de lectura</span><span class="done-label">Completada</span></span></span>'
        '<span class="chapter-chevron">' + CHEVRON + '</span></summary>'
        '<div class="chapter-content prose">' + rendered + '</div>'
        '<div class="chapter-actions"><button type="button" class="complete-button" data-complete="' + str(n) + '" aria-pressed="false"><span aria-hidden="true">○</span> Marcar como completada</button>'
        '<button type="button" class="next-chapter" data-next="' + str(n) + '">Siguiente etapa <span aria-hidden="true">→</span></button></div>'
        '</details></article>'
    )

CSS = r"""
:root{--bg:#fafaf7;--paper:#fff;--ink:#24362f;--muted:#65716a;--line:#e0e5dc;--orange:#b5482a;--orange-soft:#f9eee7;--green:#416449;--green-soft:#edf3e9;--sidebar:#f1f3ec;--mono:"SFMono-Regular",Consolas,"Liberation Mono",monospace;--sans:"Avenir Next","Segoe UI","Trebuchet MS",sans-serif;--serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;--sidebar-width:268px}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:155px}body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.65}button,input{font:inherit}button,a,input{-webkit-tap-highlight-color:transparent}button{cursor:pointer}a{color:inherit}button:focus-visible,a:focus-visible,summary:focus-visible,input:focus-visible{outline:3px solid #b5482a;outline-offset:4px}button{color:inherit}svg{display:block}button svg{width:20px;height:20px}[hidden]{display:none!important}.skip-link{position:fixed;top:8px;left:280px;transform:translateY(-150%);background:var(--ink);color:#fff;padding:10px 18px;z-index:200}.skip-link:focus{transform:none}
.sidebar{position:fixed;inset:0 auto 0 0;width:var(--sidebar-width);background:var(--sidebar);border-right:1px solid var(--line);z-index:80;display:flex;flex-direction:column;padding:28px 19px 18px}.brand{display:flex;align-items:center;gap:11px;text-decoration:none;margin:0 11px 22px}.brand-icon{width:39px;height:43px;background:var(--orange);color:white;display:grid;place-items:center;border-radius:11px 11px 15px 15px;transform:rotate(-5deg)}.brand-icon svg{width:26px;height:26px}.brand b{font-size:18px;letter-spacing:-.7px;display:block;line-height:1.2}.brand small{font-size:10px;letter-spacing:2px;font-weight:700;color:var(--muted)}.guide-label{display:flex;justify-content:space-between;align-items:center;margin:0 11px 10px;padding-top:17px;border-top:1px solid var(--line);font-size:10px;letter-spacing:1.5px;font-weight:700;color:var(--muted)}.version-label{font-family:var(--mono);letter-spacing:0;font-size:10px;border:1px solid #d1d8cd;border-radius:4px;padding:1px 5px}.sidebar nav{overflow:auto;flex:1;scrollbar-width:thin;padding-right:4px}.nav-group{text-transform:uppercase;letter-spacing:1.7px;font-size:9px;font-weight:800;color:#73806d;padding:18px 12px 6px}.nav-link{display:flex;align-items:center;gap:10px;text-decoration:none;border-radius:6px;padding:8px 10px;font-size:12px;line-height:1.4;margin:2px 0;transition:background .15s}.nav-link:hover{background:#e4e9de}.nav-link.active{background:#e0e7da;color:#25442e;font-weight:700}.nav-number{font-size:10px;color:#7b8675;font-family:var(--mono)}.nav-link.active .nav-number{color:#416449}.nav-done{margin-left:auto;color:var(--green);opacity:0}.nav-link.completed .nav-done{opacity:1}.sidebar-foot{padding:18px 10px 0;margin-top:12px;border-top:1px solid var(--line)}.progress-label{display:flex;justify-content:space-between;font-size:11px;font-weight:700}.progress-label output{font-family:var(--mono);font-size:10px}.progress-track{height:4px;background:#dce3d5;border-radius:5px;margin:10px 0;overflow:hidden}.progress-fill{height:100%;width:0;background:var(--green);transition:width .3s}.progress-note{font-size:10px;line-height:1.5;color:var(--muted);margin:0}.reset-progress{border:0;background:none;padding:6px 0 0;text-decoration:underline;font-size:10px;color:var(--muted)}.close-sidebar{display:none}.backdrop{display:none}
.shell{margin-left:var(--sidebar-width)}.topbar{height:72px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:16px;padding:0 46px;background:rgba(250,250,247,.96);position:sticky;top:0;z-index:40}.breadcrumb{display:flex;gap:12px;align-items:center;min-width:0;font-size:11px;color:var(--muted)}.breadcrumb b{font-weight:600;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:390px}.breadcrumb .slash{color:#b3bcb0}.top-actions{display:flex;gap:9px;align-items:center;flex-shrink:0}.text-button{display:inline-flex;align-items:center;justify-content:center;gap:8px;background:none;border:1px solid var(--line);border-radius:7px;padding:8px 12px;font-size:11px;font-weight:600;text-decoration:none;transition:background .15s}.text-button:hover{background:#edf0e8}.text-button svg{width:15px;height:15px}.menu-toggle{display:none;background:none;border:0;padding:5px}
.content{max-width:1190px;margin:0 auto;padding:48px 60px 30px}.hero{position:relative;display:grid;grid-template-columns:minmax(0,1fr) 170px;gap:30px;padding:0 0 28px;animation:arrive .45s ease-out}.eyebrow{text-transform:uppercase;font-weight:750;font-size:9px;letter-spacing:2px;color:var(--muted)}.hero .eyebrow{display:flex;align-items:center;gap:10px}.little-dot{width:6px;height:6px;border-radius:50%;background:var(--orange);display:inline-block}.hero h1{font-family:var(--serif);font-size:clamp(49px,5.7vw,79px);font-weight:500;line-height:1.02;letter-spacing:-3.5px;margin:19px 0 18px;max-width:640px}.hero h1 em{font-weight:500;color:var(--orange)}.hero-description{font-size:14px;line-height:1.8;color:var(--muted);max-width:560px;margin:0}.hero-actions{display:flex;flex-wrap:wrap;gap:9px;margin-top:23px}.primary-button{display:inline-flex;align-items:center;gap:20px;border:0;border-radius:6px;background:var(--ink);color:#fff;font-size:11px;font-weight:700;padding:12px 17px;transition:background .2s}.primary-button:hover{background:var(--green)}.hero-art{align-self:center;position:relative;transform:rotate(7deg);margin-top:15px}.passport{height:214px;width:156px;border-radius:9px 14px 14px 9px;background:#e8eddf;border:1px solid #cad5bf;box-shadow:7px 9px 0 #edf0e7;display:flex;align-items:center;flex-direction:column;padding:20px 10px;position:relative}.passport:before{content:"";position:absolute;left:8px;top:0;bottom:0;border-left:1px solid #cbd5c0}.passport-top{font-size:8px;letter-spacing:2.7px;font-weight:800;color:var(--green)}.passport .paw-seal{width:66px;height:66px;border:1px solid #a1b092;border-radius:50%;display:grid;place-items:center;margin:18px 0 12px;color:var(--green)}.paw-seal svg{width:34px;height:34px}.passport strong{font-family:var(--serif);font-size:18px;font-weight:500;line-height:1}.passport small{font-family:var(--mono);font-size:7px;color:var(--green);margin-top:12px}.stamp{position:absolute;background:#f9f6ee;border:1px solid #c56a49;color:#a84122;border-radius:50%;width:64px;height:64px;display:grid;place-items:center;right:-16px;bottom:-9px;transform:rotate(-18deg);font-family:var(--mono);font-size:9px;text-align:center;line-height:1.25}.stamp b{font-size:19px}
.meta-strip{display:grid;grid-template-columns:1fr 1fr 1fr 1.3fr;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:17px 0;margin:0 0 28px}.meta-item{padding:0 18px;border-left:1px solid var(--line)}.meta-item:first-child{padding-left:0;border:0}.meta-item span{display:block;font-size:8px;letter-spacing:1.5px;font-weight:700;color:var(--muted);text-transform:uppercase}.meta-item b{display:block;font-size:12px;font-weight:650;margin-top:4px}.meta-item .status{color:var(--orange)}
.usage{border:1px solid var(--line);border-radius:8px;background:var(--paper);margin-bottom:31px}.usage summary{cursor:pointer;list-style:none;font-size:12px;font-weight:650;padding:14px 18px;display:flex;justify-content:space-between;align-items:center}.usage summary:after{content:"+";font-size:17px;color:var(--muted)}.usage[open] summary:after{content:"−"}.usage .prose{padding:0 20px 10px;font-size:12px}
.route-label{display:flex;justify-content:space-between;align-items:center;margin-bottom:11px}.route-label span:last-child{font-size:10px;color:var(--muted)}.roadmap{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));margin-bottom:33px}.roadmap button{position:relative;text-align:left;border:0;background:none;padding:12px 12px 10px 0;display:flex;align-items:center;gap:10px;color:var(--ink)}.roadmap button:before{content:"";height:1px;background:var(--line);position:absolute;top:28px;left:38px;right:6px}.roadmap .step-dot{z-index:1;background:var(--bg);border:1px solid #b6c1ac;width:32px;height:32px;border-radius:50%;display:grid;place-items:center;font-family:var(--mono);font-size:10px;flex-shrink:0}.roadmap button:hover .step-dot{background:var(--ink);color:#fff}.roadmap button b{font-size:11px;background:var(--bg);padding:0 7px;position:relative}.roadmap button small{display:block;font-weight:400;color:var(--muted);font-size:9px;margin-top:1px}
.guide-heading{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:15px;gap:16px}.guide-heading h2{font-family:var(--serif);font-size:30px;letter-spacing:-.8px;font-weight:500;margin:0}.guide-heading p{font-size:11px;color:var(--muted);margin:4px 0 0}.guide-tools{display:flex;align-items:center;gap:6px;flex-shrink:0}.quiet-button{border:0;background:none;font-size:10px;color:var(--muted);padding:8px;text-decoration:underline;text-underline-offset:3px}
.search-area{position:sticky;top:72px;z-index:30;padding:12px 0 10px;background:var(--bg);border-bottom:1px solid var(--line);margin-bottom:8px}.search-row{display:flex;gap:10px;align-items:center}.search-box{display:flex;align-items:center;gap:10px;background:#fff;border:1px solid var(--line);border-radius:7px;padding:9px 12px;flex:1;min-width:0}.search-box:focus-within{border-color:var(--green);box-shadow:0 0 0 2px #41644915}.search-box svg{width:16px;height:16px;flex-shrink:0;color:var(--muted)}.search-box input{outline:none!important;border:0;width:100%;background:none;font-size:12px;color:var(--ink);min-width:0;padding:1px}.search-box kbd{font-family:var(--mono);font-size:9px;color:#7a8572;border:1px solid var(--line);padding:0 4px;border-radius:3px}.clear-search{border:0;background:none;font-size:17px;padding:0 4px;color:var(--muted)}.search-count{font-family:var(--mono);font-size:10px;color:var(--muted);white-space:nowrap;min-width:61px;text-align:right}.role-filters{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}.role-filter{display:inline-flex;gap:7px;align-items:center;border:1px solid transparent;background:none;border-radius:5px;font-size:10px;padding:5px 9px;color:var(--muted)}.role-filter[aria-pressed=true]{background:var(--green-soft);border-color:#cbd7c2;color:#31533a;font-weight:700}.role-letter{display:grid;place-items:center;font-family:var(--mono);font-size:8px;width:17px;height:17px;border-radius:4px;background:#e5e9df;color:#3b513c}.filter-note{font-size:10px;color:var(--muted);margin:7px 0 0}.empty-state{padding:44px 20px;text-align:center;border:1px dashed var(--line);border-radius:8px;margin:20px 0}.empty-state h3{font-family:var(--serif);font-size:26px;font-weight:500;margin:0 0 8px}.empty-state p{font-size:12px;color:var(--muted)}
.chapter{border-bottom:1px solid var(--line);scroll-margin-top:195px}.chapter-details>summary{list-style:none;display:flex;gap:19px;align-items:center;padding:20px 6px 20px 2px;cursor:pointer;transition:background .15s}.chapter-details>summary:hover{background:#f3f5ee}.chapter-details[open]>summary{padding-top:25px;padding-bottom:23px}.chapter-num{font-family:var(--serif);font-size:29px;font-style:italic;color:#8a9a82;line-height:1;min-width:36px}.chapter-details[open] .chapter-num{color:var(--orange)}.chapter-heading{flex:1;min-width:0}.chapter-title{font-size:14px;font-weight:650;line-height:1.4;display:block}.chapter-meta{display:flex;gap:12px;align-items:center;font-size:9px;color:var(--muted);margin-top:7px;line-height:1.5}.owner-pill{font-family:var(--mono);color:#5b7053;background:#edf0e6;border-radius:3px;padding:1px 5px;font-size:8px}.chapter-chevron{color:#87947e;flex-shrink:0;width:18px;transition:transform .2s}.chapter-chevron svg{width:17px;height:17px}.chapter-details[open] .chapter-chevron{transform:rotate(90deg)}.chapter.completed .chapter-num{color:var(--green)}.done-label{display:none;color:var(--green)}.chapter.completed .done-label{display:inline}.chapter.completed .done-label:before{content:"✓ ";font-weight:700}.chapter-content{padding:0 3px 12px 57px;min-width:0}.chapter-actions{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:0 3px 29px 57px;padding-top:16px;border-top:1px solid var(--line)}.complete-button{border:1px solid #c9d4c1;border-radius:6px;background:#fff;font-size:11px;display:flex;align-items:center;gap:9px;padding:9px 13px}.complete-button[aria-pressed=true]{background:var(--green);border-color:var(--green);color:white}.complete-button span{font-size:15px;line-height:1}.next-chapter{font-size:11px;background:none;border:0;display:flex;align-items:center;gap:18px;padding:9px 0;font-weight:650}.next-chapter span{color:var(--orange);font-size:17px}
.prose{font-size:13px;line-height:1.85;overflow-wrap:break-word}.prose h3{font-family:var(--serif);font-size:25px;font-weight:500;letter-spacing:-.5px;line-height:1.3;margin:31px 0 13px}.prose h3:first-child{margin-top:0}.prose p{margin:0 0 15px}.prose ul,.prose ol{padding-left:24px;margin:0 0 20px}.prose li{margin:6px 0;padding-left:2px}.prose li::marker{color:var(--green);font-weight:600}.prose strong{font-weight:700}.prose a{color:var(--orange);text-decoration:underline;text-underline-offset:3px;overflow-wrap:anywhere}.prose code:not(pre code){font-family:var(--mono);font-size:.86em;background:#edf0e7;border-radius:3px;padding:2px 4px;color:#304d36;overflow-wrap:anywhere}.prose blockquote{border-left:2px solid var(--green);margin:20px 0;padding:8px 18px;background:var(--green-soft)}.prose .table-scroll{overflow-x:auto;width:100%;margin:22px 0;border:1px solid var(--line);border-radius:7px;scrollbar-width:thin}.prose table{width:100%;border-collapse:collapse;font-size:11px;line-height:1.7;min-width:470px;background:#fff}.prose th{text-align:left;background:#edf1e8;color:#496344;font-weight:700;vertical-align:top;padding:11px 13px;font-size:10px;border-bottom:1px solid var(--line)}.prose td{padding:11px 13px;vertical-align:top;border-bottom:1px solid #e8ece4;min-width:105px}.prose tr:last-child td{border:0}.prose td:first-child{font-weight:550}.prose tbody tr:nth-child(even){background:#fbfcf8}.code-wrap{margin:21px 0;border-radius:8px;overflow:hidden;background:#1e2925;color:#e1e9dd}.code-head{display:flex;justify-content:space-between;align-items:center;background:#29372f;padding:7px 13px;gap:16px}.code-head>span{font-family:var(--mono);font-size:9px;color:#c0d3b3;text-transform:uppercase;letter-spacing:1.3px}.copy-code{border:1px solid #53614f;border-radius:4px;background:none;color:#d7e0d2;font-size:9px;padding:3px 8px}.copy-code:hover{background:#3c4d3d}.codeblock{margin:0;padding:17px;overflow:auto;font-family:var(--mono);font-size:11px;line-height:1.85;background:#1e2925!important;tab-size:2}.codeblock code{font:inherit}.codeblock .c1,.codeblock .c,.codeblock .cm{color:#a9b8a3!important}.prose mark{background:#f7d8a8;color:#4a371c;border-radius:2px;padding:1px}.milestone{background:#edf3e9;border:1px solid #dce6d3;border-radius:7px;padding:14px 17px!important;color:#36513c;margin-top:23px!important}
.architecture{border:1px solid var(--line);border-radius:8px;background:#f4f6ef;padding:20px;margin:24px 0}.map-caption{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;font-size:8px;letter-spacing:1.4px;font-weight:750;color:var(--muted);margin-bottom:23px}.map-caption span:last-child{letter-spacing:0;text-transform:none;font-size:10px;font-weight:400}.flow-lane{display:grid;grid-template-columns:100px minmax(0,1fr);align-items:center;gap:13px;margin:14px 0}.lane-label{font-size:9px;color:var(--muted);font-weight:650}.flow-chain{display:flex;align-items:center;gap:7px;min-width:0}.service-node{display:flex;flex:1;min-width:0;flex-direction:column;align-items:flex-start;background:white;border:1px solid #d5decf;border-radius:6px;padding:11px;text-align:left;line-height:1.4;transition:background .15s,border .15s;max-width:210px}.service-node b{font-size:10px;white-space:nowrap}.service-node span{font-size:8px;color:var(--muted);margin-top:3px}.service-node:hover,.service-node[aria-pressed=true]{border-color:#8ba17c;background:#e6eedf}.flow-arrow{color:#7d9270;font-size:15px}.flow-note{font-size:10px!important;line-height:1.6;margin:18px 0!important;color:var(--muted)}.service-detail{border-top:1px solid #d5decf;padding-top:15px;font-size:11px;line-height:1.7}.service-detail p{margin:7px 0 0}.service-detail button{border:0;background:none;color:var(--orange);padding:6px 0 0;font-size:10px;text-decoration:underline}.service-detail strong{font-size:12px}
.closing{margin-top:42px;display:flex;justify-content:space-between;gap:20px;align-items:center;padding:26px 0;border-top:1px solid var(--line);color:var(--muted);font-size:10px}.closing b{display:block;color:var(--ink);font-family:var(--serif);font-size:21px;font-weight:500;letter-spacing:-.4px;margin-bottom:2px}.closing a{text-underline-offset:3px}.toast{position:fixed;bottom:25px;left:calc(50% + 100px);transform:translate(-50%,20px);background:var(--ink);color:#fff;border-radius:7px;padding:12px 20px;font-size:11px;z-index:100;opacity:0;pointer-events:none;transition:.2s;max-width:90vw;text-align:center}.toast.show{opacity:1;transform:translate(-50%,0)}.back-top{position:fixed;right:23px;bottom:22px;width:37px;height:37px;border:1px solid var(--line);background:white;border-radius:50%;z-index:35;font-size:17px;box-shadow:0 3px 12px #24362f0a}.chapter:target>details>summary{background:#f0f3e9}summary::-webkit-details-marker{display:none}.no-js-note{padding:12px 20px;background:#fff3d6;color:#624819;font-size:12px}
@keyframes arrive{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
@media(min-width:1600px){.content{padding-top:60px}.hero h1{font-size:86px}}
@media(max-width:1200px){:root{--sidebar-width:242px}.sidebar{padding-left:12px;padding-right:12px}.content{padding:35px 32px 24px}.topbar{padding:0 32px}.hero{grid-template-columns:minmax(0,1fr) 140px;gap:20px}.passport{width:132px;height:189px;padding:16px 8px}.passport .paw-seal{width:55px;height:55px;margin:15px 0 10px}.passport strong{font-size:16px}.stamp{width:58px;height:58px}.hero h1{font-size:64px}.service-node{padding:9px 7px}.flow-lane{grid-template-columns:78px minmax(0,1fr);gap:7px}.flow-chain{gap:5px}}
@media(max-width:1000px){.hero{grid-template-columns:1fr}.hero-art{display:none}.hero h1{font-size:67px}.meta-strip{grid-template-columns:1fr 1fr 1fr}.meta-item:last-child{display:none}.flow-lane{grid-template-columns:1fr;gap:5px}.lane-label{font-size:9px}.service-node{padding:10px}.role-filter{font-size:9px;padding:5px 7px}.chapter-content{padding-left:20px}.chapter-actions{margin-left:20px}.roadmap button{gap:2px}.roadmap button b{font-size:10px;padding:0 4px}}
@media(max-width:760px){:root{--sidebar-width:268px}.shell{margin:0}.sidebar{transform:translateX(-100%);transition:transform .2s ease;padding-top:23px;box-shadow:none}.sidebar.open{transform:translateX(0);box-shadow:15px 0 60px #152a2a22}.close-sidebar{display:block;position:absolute;right:12px;top:16px;background:none;border:0;font-size:24px;padding:2px 8px;color:var(--muted)}.backdrop.open{display:block;position:fixed;inset:0;background:#172b2455;backdrop-filter:blur(2px);z-index:70}.menu-toggle{display:block}.topbar{height:61px;padding:0 20px;gap:10px}.breadcrumb{flex:1;gap:9px;font-size:10px}.breadcrumb>span:first-child{display:none}.breadcrumb .slash{display:none}.breadcrumb b{max-width:215px}.top-actions{gap:3px}.top-actions .text-button{border:0;padding:7px}.top-actions .text-button span{display:none}.content{padding:29px 23px 20px}.hero{padding-bottom:25px}.hero .eyebrow{font-size:8px;letter-spacing:1.5px}.hero h1{font-size:64px;margin:17px 0;letter-spacing:-2.7px}.hero-description{font-size:13px;max-width:540px}.hero-actions{margin-top:20px}.meta-strip{padding:14px 0;margin-bottom:22px}.meta-item{padding:0 10px}.meta-item span{font-size:7px;letter-spacing:1px}.meta-item b{font-size:11px}.usage{margin-bottom:24px}.usage summary{padding:13px;font-size:11px}.route-label span:last-child{font-size:9px}.roadmap{margin-bottom:25px}.roadmap button{align-items:flex-start;flex-direction:column;gap:8px;padding:8px 5px 8px 0}.roadmap button:before{top:24px;left:35px}.roadmap button b{padding:0;font-size:10px;line-height:1.5}.roadmap button small{font-size:8px}.guide-heading{gap:8px}.guide-heading h2{font-size:28px}.guide-tools{gap:0}.quiet-button{font-size:9px;padding:7px 4px}.guide-heading p{font-size:10px}.search-area{top:61px;padding:9px 0 8px}.role-filters{gap:1px;margin-top:8px}.role-filter{font-size:9px;padding:5px 6px;gap:4px}.role-letter{width:14px;height:14px;font-size:7px}.filter-note{font-size:9px}.search-box{padding:8px 9px}.search-box input{font-size:11px}.search-box kbd{display:none}.search-count{font-size:9px;min-width:53px}.chapter-details>summary{padding:18px 0;gap:12px}.chapter-num{font-size:27px;min-width:30px}.chapter-title{font-size:13px}.chapter-meta{font-size:8px;gap:9px}.chapter-content{padding-left:0;padding-right:0}.chapter-actions{margin-left:0;margin-right:0;gap:10px}.prose{font-size:12px;line-height:1.9}.prose h3{font-size:23px}.prose table{font-size:10px}.codeblock{font-size:10px;padding:13px}.architecture{padding:13px}.flow-chain{gap:4px}.service-node{padding:9px 6px}.service-node b{font-size:9px}.service-node span{font-size:7px}.flow-arrow{font-size:12px}.closing{align-items:flex-start;font-size:9px}.closing b{font-size:18px}.toast{left:50%;font-size:10px}.skip-link{left:10px}.chapter{scroll-margin-top:189px}}
@media(max-width:390px){.content{padding-left:17px;padding-right:17px}.hero h1{font-size:58px}.role-filter{font-size:8px;padding:5px 4px}.chapter-title{font-size:12px}.complete-button{font-size:10px}.next-chapter{font-size:10px;gap:9px}.service-node span{font-size:7px}.service-node b{font-size:8px}.topbar{padding:0 15px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{animation:none!important;transition:none!important}}
@media print{@page{margin:16mm 15mm}.sidebar,.topbar,.search-area,.guide-tools,.hero-actions,.usage,.roadmap,.route-label,.chapter-actions,.code-head button,.back-top,.closing,.toast,.skip-link,.next-chapter{display:none!important}.shell{margin:0}.content{padding:0;max-width:none}.hero{display:block;padding-bottom:14px;animation:none}.hero h1{font-size:47px;letter-spacing:-1px}.hero-description{max-width:none}.hero-art{display:none}.meta-strip{margin-bottom:18px}.chapter{break-inside:auto;scroll-margin:0}.chapter-details>summary{padding:20px 0 12px;cursor:default}.chapter-content{padding:0}.chapter-chevron{display:none}.chapter-title{font-size:17px}.chapter-num{font-size:27px}.prose{font-size:10pt;line-height:1.6}.prose h3{font-size:16pt;break-after:avoid}.prose table{font-size:8pt;min-width:0}.prose th,.prose td{min-width:0;padding:7px;overflow-wrap:anywhere}.table-scroll{overflow:visible!important}.code-wrap{break-inside:avoid;background:#f1f3ed!important;color:#1e2925!important;border:1px solid #d7dfd0}.code-head{background:#e7ecdf!important}.code-head>span{color:#24362f!important}.codeblock{white-space:pre-wrap!important;overflow-wrap:anywhere;font-size:8pt;color:#1e2925!important;background:#f1f3ed!important}.codeblock span{color:#1e2925!important}.architecture{break-inside:avoid}.service-node,.service-detail button{pointer-events:none}.prose a{color:#75321e}.chapter[hidden]{display:block!important}.owner-pill{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""

JS = r"""
(function(){
  'use strict';
  var key = 'pataporte-aws-guide-v1';
  var chapters = Array.from(document.querySelectorAll('.chapter'));
  var navLinks = Array.from(document.querySelectorAll('[data-nav]'));
  var search = document.getElementById('guide-search');
  var roleButtons = Array.from(document.querySelectorAll('.role-filter'));
  var activeRole = 'all', done = new Set(), searchTimer, beforeSearch = null, printing = false;
  var sidebar = document.querySelector('.sidebar'), backdrop = document.querySelector('.backdrop');
  var menu = document.getElementById('menu-toggle'), mobile = window.matchMedia('(max-width:760px)');
  var lastFocus;
  var storageOK = true;
  try{
    var stored = JSON.parse(localStorage.getItem(key) || '{}');
    if(Array.isArray(stored.completed)) stored.completed.forEach(function(n){ if(n >= 1 && n <= 20) done.add(Number(n)); });
  }catch(e){ storageOK = false; }
  function save(){
    try{ localStorage.setItem(key, JSON.stringify({completed:Array.from(done),updatedAt:new Date().toISOString()})); }
    catch(e){ storageOK = false; }
    if(!storageOK) document.querySelector('.progress-note').textContent = 'Progreso disponible durante esta sesión. El navegador no permite guardarlo.';
  }
  function toast(message){
    var el = document.getElementById('toast');
    el.textContent = message; el.classList.add('show');
    clearTimeout(toast.timer); toast.timer = setTimeout(function(){el.classList.remove('show');},2800);
  }
  function updateProgress(){
    chapters.forEach(function(ch){
      var n = Number(ch.dataset.number), completed = done.has(n);
      ch.classList.toggle('completed',completed);
      var button = ch.querySelector('[data-complete]');
      button.setAttribute('aria-pressed',String(completed));
      button.innerHTML = completed ? '<span aria-hidden="true">✓</span> Etapa completada' : '<span aria-hidden="true">○</span> Marcar como completada';
    });
    navLinks.forEach(function(a){a.classList.toggle('completed',done.has(Number(a.dataset.nav)));});
    document.getElementById('progress-text').textContent = done.size + ' / 20';
    document.querySelector('.progress-fill').style.width = (done.size * 5) + '%';
    document.getElementById('progress-meter').setAttribute('aria-valuenow',String(done.size));
  }
  function normalize(value){ return value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase(); }
  chapters.forEach(function(ch){ch.searchText=normalize(ch.textContent);});
  function removeHighlights(){
    document.querySelectorAll('mark[data-search-hit]').forEach(function(mark){
      var parent=mark.parentNode; mark.replaceWith(document.createTextNode(mark.textContent)); parent.normalize();
    });
  }
  function highlightMatches(root,query){
    var walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{
      acceptNode:function(node){
        if(!node.nodeValue.trim() || node.parentElement.closest('pre,code,button,svg,mark')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var nodes=[], count=0;
    while(walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function(node){
      if(count>80) return;
      var text=node.nodeValue, norm=normalize(text), index=0, cursor=0, fragment=document.createDocumentFragment(), hit=false;
      while((index=norm.indexOf(query,cursor)) !== -1 && count<80){
        fragment.appendChild(document.createTextNode(text.slice(cursor,index)));
        var mark=document.createElement('mark'); mark.dataset.searchHit='true'; mark.textContent=text.slice(index,index+query.length);
        fragment.appendChild(mark); cursor=index+query.length; count++; hit=true;
      }
      if(hit){fragment.appendChild(document.createTextNode(text.slice(cursor)));node.replaceWith(fragment);}
    });
  }
  function applyFilters(){
    var query=normalize(search.value.trim());
    removeHighlights();
    if(query && beforeSearch===null) beforeSearch = new Set(chapters.filter(function(ch){return ch.querySelector('details').open;}).map(function(ch){return ch.dataset.number;}));
    var visible=0;
    chapters.forEach(function(ch){
      var matchRole=activeRole==='all'||ch.dataset.roles.indexOf(activeRole)!==-1;
      var matchQuery=!query||ch.searchText.indexOf(query)!==-1;
      ch.hidden=!(matchRole&&matchQuery);
      var link=document.querySelector('[data-nav="'+ch.dataset.number+'"]');
      link.hidden=ch.hidden;
      if(!ch.hidden){visible++; if(query){ch.querySelector('details').open=true;highlightMatches(ch.querySelector('.chapter-content'),query);}}
      if(!query && beforeSearch!==null) ch.querySelector('details').open=beforeSearch.has(ch.dataset.number);
    });
    if(!query) beforeSearch=null;
    document.getElementById('search-count').textContent=visible+' / 20';
    document.getElementById('empty-state').hidden=visible!==0;
    document.getElementById('clear-search').hidden=!search.value;
    document.getElementById('filter-note').textContent=activeRole==='all' ? 'Abrí una etapa para leerla. Tu avance se guarda en este navegador.' : 'Se muestran las etapas de '+activeRole+' y las compartidas con el equipo.';
    document.querySelectorAll('.nav-group').forEach(function(group){
      var next=group.nextElementSibling, hasVisible=false;
      while(next && !next.classList.contains('nav-group')){if(!next.hidden)hasVisible=true;next=next.nextElementSibling;}
      group.hidden=!hasVisible;
    });
  }
  function setActive(n){
    navLinks.forEach(function(a){
      var active=Number(a.dataset.nav)===Number(n);
      a.classList.toggle('active',active);
      if(active) a.setAttribute('aria-current','location'); else a.removeAttribute('aria-current');
    });
    var target=document.querySelector('[data-nav="'+n+'"]');
    if(target) document.getElementById('current-chapter').textContent=target.children[1].textContent;
  }
  function closeMenu(){
    sidebar.classList.remove('open');backdrop.classList.remove('open');menu.setAttribute('aria-expanded','false');
    document.body.style.overflow=''; sidebar.inert=mobile.matches;
  }
  function jump(n){
    var ch=chapters.find(function(item){return Number(item.dataset.number)===Number(n);});
    if(!ch)return;
    if(ch.hidden){
      search.value='';activeRole='all';roleButtons.forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.role==='all'));});applyFilters();
    }
    closeMenu();ch.querySelector('details').open=true;setActive(n);
    history.replaceState(null,'','#'+ch.id);
    ch.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion:reduce)').matches?'instant':'smooth',block:'start'});
  }
  search.addEventListener('input',function(){clearTimeout(searchTimer);searchTimer=setTimeout(applyFilters,140);});
  document.getElementById('clear-search').addEventListener('click',function(){search.value='';applyFilters();search.focus();});
  roleButtons.forEach(function(button){button.addEventListener('click',function(){
    activeRole=button.dataset.role;
    roleButtons.forEach(function(b){b.setAttribute('aria-pressed',String(b===button));});
    applyFilters();
  });});
  document.getElementById('reset-filters').addEventListener('click',function(){
    search.value='';activeRole='all';roleButtons.forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.role==='all'));});applyFilters();
  });
  navLinks.forEach(function(link){link.addEventListener('click',function(e){e.preventDefault();jump(link.dataset.nav);});});
  document.querySelectorAll('[data-jump]').forEach(function(button){button.addEventListener('click',function(){jump(button.dataset.jump);});});
  document.querySelectorAll('[data-complete]').forEach(function(button){button.addEventListener('click',function(){
    var n=Number(button.dataset.complete); if(done.has(n))done.delete(n);else done.add(n);save();updateProgress();
    if(done.size===20) toast('Las 20 etapas están marcadas como completadas.');
  });});
  document.querySelectorAll('[data-next]').forEach(function(button){button.addEventListener('click',function(){
    var next=chapters.find(function(ch){return !ch.hidden&&Number(ch.dataset.number)>Number(button.dataset.next);});
    if(next)jump(next.dataset.number);else toast('Llegaste al final de las etapas visibles.');
  });});
  document.getElementById('reset-progress').addEventListener('click',function(){
    if(window.confirm('¿Reiniciar las etapas completadas en este navegador?')){done.clear();save();updateProgress();toast('Progreso reiniciado.');}
  });
  document.getElementById('expand-all').addEventListener('click',function(){chapters.filter(function(ch){return !ch.hidden;}).forEach(function(ch){ch.querySelector('details').open=true;});});
  document.getElementById('collapse-all').addEventListener('click',function(){chapters.forEach(function(ch){ch.querySelector('details').open=false;});});
  chapters.forEach(function(ch){ch.querySelector('details').addEventListener('toggle',function(){if(this.open&&!printing)setActive(ch.dataset.number);});});
  document.querySelectorAll('.prose table').forEach(function(table){
    var wrapper=document.createElement('div');wrapper.className='table-scroll';wrapper.tabIndex=0;
    wrapper.setAttribute('role','region');wrapper.setAttribute('aria-label','Tabla de referencia; desplazamiento horizontal disponible');
    table.parentNode.insertBefore(wrapper,table);wrapper.appendChild(table);
  });
  document.querySelectorAll('.prose p').forEach(function(p){if(p.textContent.trim().indexOf('Etapa terminada:')===0)p.classList.add('milestone');});
  document.querySelectorAll('.prose a[href^="https://"]').forEach(function(a){a.target='_blank';a.rel='noopener noreferrer';});
  function fallbackCopy(text){
    var input=document.createElement('textarea');input.value=text;input.style.position='fixed';input.style.left='-9999px';document.body.appendChild(input);input.select();
    var success=document.execCommand('copy');input.remove();return success;
  }
  document.querySelectorAll('.copy-code').forEach(function(button){button.addEventListener('click',async function(){
    var text=button.closest('.code-wrap').querySelector('code').textContent, success=false;
    try{if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(text);success=true;}else success=fallbackCopy(text);}catch(e){success=fallbackCopy(text);}
    var original=button.textContent;button.textContent=success?'Copiado ✓':'Seleccioná el código';
    setTimeout(function(){button.textContent=original;},1800);
  });});
  var serviceInfo=JSON.parse(document.getElementById('service-data').textContent);
  document.querySelectorAll('[data-service]').forEach(function(button){button.addEventListener('click',function(){
    document.querySelectorAll('[data-service]').forEach(function(b){b.setAttribute('aria-pressed',String(b===button));});
    var item=serviceInfo[button.dataset.service], panel=document.getElementById('service-detail');
    panel.replaceChildren();
    var eyebrow=document.createElement('span');eyebrow.className='eyebrow';eyebrow.textContent='RESPONSABLE '+item.owner+' · ETAPA '+String(item.stage).padStart(2,'0');
    var title=document.createElement('strong');title.textContent=item.name;title.style.display='block';title.style.marginTop='7px';
    var description=document.createElement('p');description.textContent=item.text;
    var go=document.createElement('button');go.type='button';go.textContent='Ir a la implementación →';go.addEventListener('click',function(){jump(item.stage);});
    panel.append(eyebrow,title,description,go);
  });});
  var printState;
  window.addEventListener('beforeprint',function(){
    if(printing)return;printing=true;
    printState=chapters.map(function(ch){return {open:ch.querySelector('details').open,hidden:ch.hidden};});
    chapters.forEach(function(ch){ch.hidden=false;ch.querySelector('details').open=true;});
  });
  window.addEventListener('afterprint',function(){
    if(!printState)return;
    chapters.forEach(function(ch,i){ch.hidden=printState[i].hidden;ch.querySelector('details').open=printState[i].open;});
    setTimeout(function(){printing=false;},0);
  });
  document.getElementById('print-guide').addEventListener('click',function(){window.print();});
  menu.addEventListener('click',function(){
    lastFocus=document.activeElement;sidebar.inert=false;sidebar.classList.add('open');backdrop.classList.add('open');menu.setAttribute('aria-expanded','true');document.body.style.overflow='hidden';document.getElementById('close-sidebar').focus();
  });
  document.getElementById('close-sidebar').addEventListener('click',function(){closeMenu();if(lastFocus)lastFocus.focus();});
  backdrop.addEventListener('click',function(){closeMenu();menu.focus();});
  mobile.addEventListener('change',function(){closeMenu();});
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'&&sidebar.classList.contains('open')){closeMenu();menu.focus();}
    if((e.key==='k'&&(e.metaKey||e.ctrlKey)) || (e.key==='/'&&!/INPUT|TEXTAREA/.test(document.activeElement.tagName))){e.preventDefault();search.focus();}
    if(e.key==='Tab'&&mobile.matches&&sidebar.classList.contains('open')){
      var focusable=Array.from(sidebar.querySelectorAll('a[href],button:not([disabled])')).filter(function(el){return !el.hidden&&el.offsetParent!==null;});
      var first=focusable[0],last=focusable[focusable.length-1];
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
      if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
    }
  });
  document.getElementById('back-top').addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'});});
  window.addEventListener('hashchange',function(){var match=location.hash.match(/^#etapa-(\d+)$/);if(match)jump(Number(match[1]));});
  updateProgress();applyFilters();closeMenu();
  var match=location.hash.match(/^#etapa-(\d+)$/);
  if(match)setTimeout(function(){jump(Number(match[1]));},80);
  else document.getElementById('current-chapter').textContent='Tu hoja de ruta';
  window.addEventListener('scroll',function(){
    if(printing)return;
    var closest=null;
    chapters.forEach(function(ch){if(!ch.hidden&&ch.getBoundingClientRect().top<230)closest=ch;});
    if(closest)setActive(closest.dataset.number);
  },{passive:true});
})();
"""

PAGE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Guía interactiva para desplegar PATAPORTE en AWS: 20 etapas, arquitectura explicada, trabajo en equipo y pruebas para la defensa.">
<meta name="theme-color" content="#24362f">
<title>PATAPORTE · Guía de campo AWS</title>
<style>__CSS__
__SYNTAX_CSS__</style>
</head>
<body>
<a class="skip-link" href="#main-content">Saltar al contenido</a>
<div class="backdrop" aria-hidden="true"></div>
<aside class="sidebar" id="sidebar" aria-label="Índice de la guía">
  <button type="button" class="close-sidebar" id="close-sidebar" aria-label="Cerrar índice">×</button>
  <a class="brand" href="#main-content"><span class="brand-icon">__PAW__</span><span><b>pataporte</b><small>GUÍA DE CAMPO</small></span></a>
  <div class="guide-label"><span>EL RECORRIDO</span><span class="version-label">AWS / 2026</span></div>
  <nav aria-label="Etapas de implementación">__NAV__</nav>
  <div class="sidebar-foot">
    <div class="progress-label"><span>Tu avance</span><output id="progress-text">0 / 20</output></div>
    <div class="progress-track" id="progress-meter" role="progressbar" aria-label="Etapas marcadas como completadas" aria-valuemin="0" aria-valuemax="20" aria-valuenow="0"><div class="progress-fill"></div></div>
    <p class="progress-note">Se guarda solo en este navegador.<br>No se sincroniza entre integrantes.</p>
    <button type="button" class="reset-progress" id="reset-progress">Reiniciar avance</button>
  </div>
</aside>
<div class="shell">
  <header class="topbar">
    <button type="button" class="menu-toggle" id="menu-toggle" aria-expanded="false" aria-controls="sidebar" aria-label="Abrir índice">__MENU__</button>
    <div class="breadcrumb"><span>Ingeniería · AWS</span><span class="slash">/</span><b id="current-chapter">Tu hoja de ruta</b></div>
    <div class="top-actions">
      <button type="button" class="text-button" data-jump="17"><span>El equipo</span><span aria-hidden="true">↗</span></button>
      <button type="button" class="text-button" id="print-guide">__PRINT__<span>Imprimir guía</span></button>
    </div>
  </header>
  <main class="content" id="main-content">
    <noscript><p class="no-js-note">Podés leer todas las etapas desplegándolas. La búsqueda, los filtros y el avance necesitan JavaScript.</p></noscript>
    <section class="hero" aria-labelledby="page-title">
      <div>
        <div class="eyebrow"><span class="little-dot"></span>DE LA FACULTAD A LA NUBE · PASO A PASO</div>
        <h1 id="page-title">Un pasaporte<br>hacia <em>AWS.</em></h1>
        <p class="hero-description">Toda la ruta para llevar PATAPORTE a la nube. Qué construir, por qué elegirlo y cómo demostrar que funciona. Una guía para trabajar de a tres.</p>
        <div class="hero-actions"><button type="button" class="primary-button" data-jump="1">Empezar el recorrido <span aria-hidden="true">↗</span></button><button type="button" class="text-button" data-jump="17">Dividir el trabajo <span aria-hidden="true">→</span></button></div>
      </div>
      <div class="hero-art" aria-hidden="true"><div class="passport"><span class="passport-top">PATAPORTE</span><span class="paw-seal">__PAW__</span><strong>Guía de campo</strong><small>CLOUD EDITION · 2026</small><span class="stamp"><span>AWS<br><b>20</b><br>ETAPAS</span></span></div></div>
    </section>
    <div class="meta-strip" aria-label="Datos de la guía">
      <div class="meta-item"><span>Entrega del informe</span><b>09 noviembre 2026</b></div>
      <div class="meta-item"><span>Equipo</span><b>3 personas · 1 proyecto</b></div>
      <div class="meta-item"><span>Lectura completa</span><b>~__MINUTES__ min · a tu ritmo</b></div>
      <div class="meta-item"><span>Estado del documento</span><b class="status">Plan de implementación</b></div>
    </div>
    <details class="usage"><summary>Antes de empezar · cómo usar esta guía</summary><div class="prose"><p><strong>Esta guía describe trabajo por implementar.</strong> No se creó infraestructura AWS al prepararla. Los comandos y archivos propuestos requieren los permisos y parámetros de su laboratorio.</p>__INTRO__</div></details>
    <div class="route-label"><span class="eyebrow">CUATRO MOMENTOS, UN MISMO RECORRIDO</span><span>Diseñar → construir → comprobar</span></div>
    <div class="roadmap" aria-label="Momentos de implementación">
      <button type="button" data-jump="1"><span class="step-dot">01</span><b>Preparar<small>Contexto y acuerdos</small></b></button>
      <button type="button" data-jump="5"><span class="step-dot">02</span><b>Construir<small>Infra y aplicación</small></b></button>
      <button type="button" data-jump="10"><span class="step-dot">03</span><b>Automatizar<small>Eventos y releases</small></b></button>
      <button type="button" data-jump="15"><span class="step-dot">04</span><b>Demostrar<small>Pruebas y defensa</small></b></button>
    </div>
    <section id="the-guide" aria-labelledby="guide-title">
      <div class="guide-heading"><div><h2 id="guide-title">La hoja de ruta.</h2><p>20 etapas explicadas, del primer acuerdo a la defensa.</p></div><div class="guide-tools"><button type="button" class="quiet-button" id="expand-all">Expandir</button><button type="button" class="quiet-button" id="collapse-all">Contraer</button></div></div>
      <div class="search-area">
        <div class="search-row"><label class="search-box" for="guide-search">__SEARCH__<input id="guide-search" type="search" placeholder="Buscar un servicio, una decisión o un problema…" autocomplete="off" aria-label="Buscar en toda la guía"><button type="button" class="clear-search" id="clear-search" aria-label="Limpiar búsqueda" hidden>×</button><kbd aria-hidden="true">/</kbd></label><output class="search-count" id="search-count" aria-live="polite">20 / 20</output></div>
        <div class="role-filters" role="group" aria-label="Filtrar etapas por integrante">
          <button type="button" class="role-filter" data-role="all" aria-pressed="true">Todo el equipo</button>
          <button type="button" class="role-filter" data-role="A" aria-pressed="false"><span class="role-letter">A</span>Plataforma y datos</button>
          <button type="button" class="role-filter" data-role="B" aria-pressed="false"><span class="role-letter">B</span>Aplicación y eventos</button>
          <button type="button" class="role-filter" data-role="C" aria-pressed="false"><span class="role-letter">C</span>Entrega y operación</button>
        </div>
        <p class="filter-note" id="filter-note">Abrí una etapa para leerla. Tu avance se guarda en este navegador.</p>
      </div>
      <div id="empty-state" class="empty-state" hidden><h3>No encontramos esa ruta.</h3><p>Probá con otra palabra o cambiá el filtro del equipo.</p><button type="button" class="text-button" id="reset-filters">Mostrar todas las etapas</button></div>
      <div class="chapters">__CHAPTERS__</div>
    </section>
    <footer class="closing"><div><b>Construir. Entender. Poder explicarlo.</b><span>PATAPORTE · AWS · Universidad de Montevideo · Octubre 2026</span></div><div>Documento local, sin dependencias de red.<br><a href="guia-despliegue-aws.md">Consultar el texto fuente</a></div></footer>
  </main>
</div>
<button type="button" class="back-top" id="back-top" aria-label="Volver al comienzo">↑</button>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
<script type="application/json" id="service-data">__SERVICE_DATA__</script>
<script>__JS__</script>
</body>
</html>
"""

replacements = {
    "__CSS__": CSS, "__SYNTAX_CSS__": SYNTAX_CSS, "__JS__": JS,
    "__NAV__": "\n".join(nav), "__CHAPTERS__": "\n".join(articles),
    "__INTRO__": markdown(intro), "__MINUTES__": str(read_minutes),
    "__PAW__": PAW, "__MENU__": MENU, "__PRINT__": PRINT, "__SEARCH__": SEARCH,
    "__SERVICE_DATA__": json.dumps(SERVICES, ensure_ascii=False),
}
for marker, value in replacements.items():
    PAGE = PAGE.replace(marker, value)
OUTPUT.write_text(PAGE)
print("HTML generado:", OUTPUT)
print("Etapas:", len(chapters), "| Lectura estimada:", read_minutes, "min | Bytes:", OUTPUT.stat().st_size)
