"""Local, real-search engineering dashboard. This is not the future LLM API."""

from __future__ import annotations

import io
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .schemas import RetrievalRequest

MAX_REQUEST_BYTES = 15 * 1024 * 1024

PAGE = r'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>КТ-2 · RAG / Search</title>
<style>
:root{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#eee9e1;background:#151514;font-synthesis:none}
*{box-sizing:border-box}body{margin:0}main{max-width:1440px;margin:auto;padding:28px}header{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:26px}h1{font-size:28px;margin:7px 0;font-weight:550}h2{font-size:18px;margin:0 0 14px}h3{margin:0 0 10px;font-size:16px}p{line-height:1.55}small,.muted{color:#aaa497}.eyebrow{letter-spacing:.18em;text-transform:uppercase;font-size:11px;color:#bca68c}.pill{border:1px solid #49463f;border-radius:50px;padding:8px 12px;font-size:12px;white-space:nowrap}.panel{background:#1e1e1c;border:1px solid #3a3934;border-radius:14px;padding:22px}.layout{display:grid;grid-template-columns:350px 1fr;gap:22px;align-items:start}.controls{position:sticky;top:18px}label{font-size:12px;display:block;margin:15px 0 7px;color:#cbc4b9}textarea,select,input[type=file]{font:inherit;color:inherit;border:1px solid #4b4941;background:#171715;border-radius:8px;width:100%;padding:10px}textarea{resize:vertical;min-height:115px}input[type=range]{width:100%;accent-color:#d3b48b}button{font:inherit;cursor:pointer;border:1px solid #5b5143;background:#2b2722;color:#eee9e1;border-radius:8px;padding:9px 12px}button:hover{background:#393126}button:disabled{cursor:wait;opacity:.55}.primary{background:#d6b78e;color:#1c1915;width:100%;margin-top:19px;font-weight:650}.primary:hover{background:#edcca0}.scenarios{display:grid;gap:7px;margin-top:15px}.scenarios button{text-align:left;font-size:12px}.summary{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 16px}.stat{border:1px solid #454137;padding:10px 12px;border-radius:8px;font-size:12px}.stat strong{display:block;font-size:18px;margin:4px 0}.slot{margin:22px 0}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.card{border:1px solid #464239;border-radius:10px;overflow:hidden;background:#24231f}.card.selected{border-color:#d5b386}.card img{width:100%;height:175px;object-fit:contain;background:#e9e3da;display:block}.card-body{padding:12px}.title{font-size:13px;min-height:36px;line-height:1.4}.meta{font-size:11px;color:#b9b1a5;margin:6px 0;line-height:1.5;overflow-wrap:anywhere}.bar{display:flex;height:8px;border-radius:9px;overflow:hidden;background:#49443b;margin:10px 0 6px}.bm{background:#e4aa64}.dense{background:#8cbca8}.visual{background:#a89acb}.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:11px;color:#c4bcb0}.dot{display:inline-block;width:8px;height:8px;margin-right:4px;border-radius:2px}.notice{padding:12px;border:1px solid #63543a;background:#30291f;border-radius:9px;font-size:13px;margin-bottom:15px}.success{border-color:#557c66;background:#203128}.error{border-color:#b97768;background:#3d2520;color:#ffd2c5}.warnings{font-size:11px;line-height:1.6;color:#c5b8a5;overflow-wrap:anywhere}pre{overflow:auto;max-height:430px;font-size:11px;background:#11110f;padding:14px;border-radius:8px}details{margin-top:18px}summary{cursor:pointer;font-size:13px}#status{font-size:12px;margin-top:10px;line-height:1.5;overflow-wrap:anywhere}.empty{padding:35px;color:#afa89d;text-align:center}.time-grid{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.time-grid span{font-size:11px;border:1px solid #464239;padding:6px 8px;border-radius:6px}.idline{font-family:ui-monospace,monospace;font-size:10px;color:#8f887d;overflow-wrap:anywhere}.upload-note{font-size:11px;line-height:1.5;margin-top:7px;color:#aaa497}.file-row{display:flex;gap:8px;align-items:center}.file-row input{min-width:0}.file-row button{font-size:11px}.assembly-list{font-size:13px;line-height:1.8}#fingerprint{font-size:10px;overflow-wrap:anywhere;color:#999184;max-width:850px}.headnote{font-size:12px;margin:8px 0;color:#b6ad9e}
@media(max-width:1000px){.layout{grid-template-columns:300px 1fr}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:760px){main{padding:16px}.layout{display:block}.controls{position:static;margin-bottom:18px}header{display:block}.pill{display:inline-block;margin-top:10px}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.panel{padding:16px}h1{font-size:24px}}
</style></head><body><main>
<header><div><div class="eyebrow">12 STOREEZ · КТ-2 · Матвей</div><h1>RAG / Search · инженерная демонстрация</h1><p class="headnote">Настоящие эмбеддинги, BM25 и Chroma. Сборка кандидатов и проверка слотов. Генерация LLM подключается в backend Егора.</p><div id="fingerprint"></div></div><div class="pill" id="health">Проверка локального движка…</div></header>
<div class="layout"><section class="panel controls"><h2>Запрос к гардеробу</h2>
<form id="search-form"><label for="query">Текст, погода, повод</label><textarea id="query">Москва: +6°C, ветрено, деловая встреча</textarea>
<label for="image">Изображение для визуального поиска</label><div class="file-row"><input id="image" type="file" accept="image/png,image/jpeg,image/webp"><button id="clear-image" type="button">Убрать</button></div><div class="upload-note">PNG / JPEG / WebP, до 10 МБ. Visual: похожие изображения или текст → изображения. Multimodal: BM25 + текст + изображение. Если загружено фото, визуальный канал использует его.</div>
<label for="mode">Режим поиска</label><select id="mode"><option value="hybrid">Hybrid · BM25 + Dense</option><option value="multimodal">Multimodal · BM25 + Dense + Visual</option><option value="visual">Visual · изображения</option><option value="dense">Dense · текстовые эмбеддинги</option><option value="bm25">BM25 · лексика</option></select>
<label for="alpha">α · вес группы Dense: <strong id="alpha-label">65%</strong></label><input id="alpha" type="range" min="0" max="1" step=".05" value=".65">
<label for="beta">β · доля Visual внутри Dense: <strong id="beta-label">35%</strong></label><input id="beta" type="range" min="0" max="1" step=".05" value=".35">
<button class="primary" id="submit" type="submit">Выполнить настоящий поиск</button><div id="status" aria-live="polite"></div></form>
<div class="scenarios"><button type="button" data-query="Москва: +6°C, ветрено, деловая встреча">Москва, +6°C, встреча</button><button type="button" data-query="Вечернее открытие выставки в галерее, элегантный минимализм и шелковый акцент">Вечер в галерее</button><button type="button" data-query="Удобный повседневный образ для прогулки">Проверка текущего гардероба</button></div>
<p class="upload-note">Для сценария «3 вещи» запусти демо с ограниченным JSON-гардеробом. Здесь показываются только вещи выбранного пользователя. Нехватка категорий выводится явно.</p>
<div class="legend"><span><i class="dot bm"></i>BM25</span><span><i class="dot dense"></i>Dense text</span><span><i class="dot visual"></i>Visual</span></div></section>
<section class="panel"><div id="output"><div class="empty">Выбери режим и выполни запрос. Здесь появятся реальные кандидаты, вклады RRF и задержки.</div></div></section></div>
</main><script>
const $=id=>document.getElementById(id);const slotNames={tops:'Верх',bottoms:'Низ',shoes:'Обувь',outerwear:'Верхняя одежда',accessories:'Аксессуары'};let queryImage=null,imageVersion=0,imageLoading=false;
const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n};
const number=(value,digits=4)=>value==null?'—':Number(value).toFixed(digits);
for(const [slider,label] of [['alpha','alpha-label'],['beta','beta-label']])$(slider).addEventListener('input',()=>$(label).textContent=Math.round($(slider).value*100)+'%');
function syncModeControls(){
  const mode=$('mode').value;
  $('alpha').disabled=!['hybrid','multimodal'].includes(mode);
  $('beta').disabled=mode!=='multimodal';
}
$('mode').addEventListener('change',syncModeControls);
syncModeControls();
document.querySelectorAll('[data-query]').forEach(button=>button.addEventListener('click',()=>{$('query').value=button.dataset.query;$('search-form').requestSubmit()}));
$('clear-image').addEventListener('click',()=>{imageVersion++;queryImage=null;imageLoading=false;$('image').value='';$('status').textContent='Изображение убрано.'});
$('image').addEventListener('change',()=>{const version=++imageVersion;queryImage=null;imageLoading=false;const file=$('image').files[0];if(!file)return;if(!['image/png','image/jpeg','image/jpg','image/webp'].includes(file.type.toLowerCase())){$('status').textContent='Поддерживаются PNG, JPEG и WebP.';$('image').value='';return}if(file.size>10*1024*1024){$('status').textContent='Размер изображения должен быть не больше 10 МБ.';$('image').value='';return}imageLoading=true;$('status').textContent='Чтение изображения…';const reader=new FileReader();reader.onload=()=>{if(version!==imageVersion)return;imageLoading=false;queryImage=reader.result;$('mode').value=$('query').value.trim()?'multimodal':'visual';syncModeControls();$('status').textContent='Изображение готово к поиску.'};reader.onerror=()=>{if(version!==imageVersion)return;imageLoading=false;queryImage=null;$('status').textContent='Не удалось прочитать изображение.'};reader.readAsDataURL(file)});
function card(candidate,selected){const item=candidate.item;const node=el('article','card'+(selected.has(item.id)?' selected':''));const image=el('img');image.alt=item.title;const source=item.imagePath||item.imageUrl;if(source){image.src='/images?id='+encodeURIComponent(item.id)}image.loading='lazy';node.append(image);const body=el('div','card-body');body.append(el('div','title',item.title),el('div','meta',item.color+(item.material?' · '+item.material:'')),el('div','idline',item.id));if(candidate.fallback){body.append(el('div','notice','Без рангов: заполнение слота из доступного гардероба.'))}else{const bar=el('div','bar');for(const [key,cls]of[['bm25_contribution','bm'],['dense_contribution','dense'],['visual_contribution','visual']]){const part=el('span',cls);part.style.width=(candidate.score>0?candidate[key]/candidate.score*100:0)+'%';bar.append(part)}body.append(bar,el('div','meta','RRF '+number(candidate.score,6)),el('div','meta','BM25: '+number(candidate.bm25_score)+' / ранг '+(candidate.bm25_rank??'—')),el('div','meta','Dense distance: '+number(candidate.dense_distance)+' / ранг '+(candidate.dense_rank??'—')),el('div','meta','Visual distance: '+number(candidate.visual_distance)+' / ранг '+(candidate.visual_rank??'—')),el('div','meta','Вклады B / D / V: '+[candidate.bm25_contribution,candidate.dense_contribution,candidate.visual_contribution].map(v=>number(v,6)).join(' / ')))}if(candidate.anchored)body.append(el('div','meta','Обязательная якорная вещь'));node.append(body);return node}
function renderVisualMatches(result,out){
  const matches=Object.values(result.candidates_by_slot).flat().filter(c=>c.visual_distance!=null&&c.visual_contribution>0);
  const nearest=matches.sort((a,b)=>a.visual_distance-b.visual_distance||a.item.id.localeCompare(b.item.id)).slice(0,3);
  if(!nearest.length)return;
  const section=el('section','slot');
  section.append(el('h3','','Ближайшие изображения'));
  const cards=el('div','cards');
  nearest.forEach(candidate=>cards.append(card(candidate,new Set())));
  section.append(cards);
  out.append(section);
}
function render(data){const result=data.retrieval,assembly=data.assembly,out=$('output');out.replaceChildren();const selected=new Set(assembly.selected_items.map(item=>item.id));const summary=el('div','summary');for(const[label,value]of[['Режим',result.mode],['Кандидаты',Object.values(result.candidates_by_slot).reduce((sum,rows)=>sum+rows.length,0)],['Поиск, мс',number(result.timings_ms.total,1)],['Обязательные слоты',result.required_slots.length]]){const stat=el('div','stat',label);stat.append(el('strong','',String(value)));summary.append(stat)}out.append(summary);if(['hybrid','multimodal'].includes(result.mode)){out.append(el('p','muted','α '+number(result.alpha,2)+(result.mode==='multimodal'?' · β '+number(result.visual_weight,2):'')+' · RRF c='+result.rrf_c))}const state=el('div','notice '+(assembly.complete?'success':''),assembly.complete?'Полный комплект собран и проверен по слотам.':'Комплект неполный. Не хватает: '+assembly.missing_slots.map(slot=>slotNames[slot]).join(', '));out.append(state);const list=el('div','assembly-list',assembly.selected_items.map(item=>slotNames[item.category]+': '+item.title).join(' · '));out.append(list,el('p','muted','Это детерминированная сборка найденных кандидатов. Текст LLM и процент совместимости здесь не генерируются.'));const times=el('div','time-grid');Object.entries(result.timings_ms).forEach(([key,value])=>times.append(el('span','',key+': '+number(value,1)+' мс')));out.append(times);if(result.mode==='visual')renderVisualMatches(result,out);for(const[slot,candidates]of Object.entries(result.candidates_by_slot)){if(!candidates.length)continue;const section=el('section','slot');section.append(el('h3','',slotNames[slot]+(result.required_slots.includes(slot)?' · обязательный слот':'')));const cards=el('div','cards');candidates.forEach(candidate=>cards.append(card(candidate,selected)));section.append(cards);out.append(section)}if(result.warnings.length){const details=el('details');details.append(el('summary','','Ограничения и диагностика · '+result.warnings.length));const warnings=el('ul','warnings');result.warnings.forEach(warning=>warnings.append(el('li','',warning)));details.append(warnings);out.append(details)}if(assembly.violations.length)out.append(el('div','notice error',assembly.violations.join('; ')));const raw=el('details');raw.append(el('summary','','Полный JSON результата'),el('pre','',JSON.stringify(data,null,2)));out.append(raw);out.append(el('p','idline','Гардероб: '+result.wardrobe_revision));}
$('search-form').addEventListener('submit',async event=>{event.preventDefault();if(imageLoading){$('status').textContent='Дождись чтения выбранного изображения.';return}if($('submit').disabled)return;const query=$('query').value.trim();if(!query&&!queryImage){$('status').textContent='Введи запрос или загрузи изображение.';return}let mode=$('mode').value;if(queryImage&&!['visual','multimodal'].includes(mode)){mode=query?'multimodal':'visual';$('mode').value=mode;syncModeControls()}$('submit').disabled=true;$('status').textContent='Выполняется поиск. Первый запрос может загружать модели…';const started=performance.now();try{const response=await fetch('/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,query_image:queryImage,mode,alpha:Number($('alpha').value),visual_weight:Number($('beta').value)})});const data=await response.json();if(!response.ok)throw new Error(data.error||response.statusText);render(data);$('status').textContent='Готово. UI → результат: '+Math.round(performance.now()-started)+' мс. Ответ получен от настоящего локального RAG.'}catch(error){$('status').textContent='Ошибка: '+error.message}finally{$('submit').disabled=false}});
fetch('/health').then(response=>{if(!response.ok)throw new Error(response.statusText);return response.json()}).then(data=>{$('health').textContent='RAG Online · без LLM · '+data.item_count+' вещей';$('fingerprint').textContent='Источник: реальные модели · '+data.model_fingerprint}).catch(()=>{$('health').textContent='Локальный RAG недоступен'});
</script></body></html>'''


def serve_demo(service, user_id: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    """Serve a local real-retrieval dashboard until Ctrl+C; never fabricate an answer."""

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _json(self, status: int, payload: dict) -> None:
            self._send(status, json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self) -> None:
            route = urlsplit(self.path)
            if route.path == "/":
                self._send(HTTPStatus.OK, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif route.path == "/health":
                self._json(HTTPStatus.OK, {
                    "status": "ok", "service": "Matvey local RAG/Search demo", "llm": False,
                    "source": "real_models", "user_id": user_id,
                    "item_count": len(service.retriever.store.get_items(user_id)),
                    "model_fingerprint": service.retriever.embedder.fingerprint,
                })
            elif route.path == "/images":
                item_id = parse_qs(route.query).get("id", [""])[0]
                item = next((item for item in service.retriever.store.get_items(user_id) if item.id == item_id), None)
                source = (item.imagePath or item.imageUrl) if item else None
                if not source:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "Wardrobe image not found"})
                    return
                try:
                    image = service.retriever.image_loader(source)
                    try:
                        buffer = io.BytesIO()
                        image.save(buffer, format="PNG")
                    finally:
                        image.close()
                    self._send(HTTPStatus.OK, buffer.getvalue(), "image/png")
                except (OSError, ValueError) as exc:
                    self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "Unknown route"})

        def do_POST(self) -> None:
            if urlsplit(self.path).path != "/search":
                self._json(HTTPStatus.NOT_FOUND, {"error": "Unknown route"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_REQUEST_BYTES:
                    self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "JSON request must be between 1 byte and 15 MB"})
                    return
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("JSON object is required")
                payload["user_id"] = user_id  # Browser cannot select another tenant.
                result = service.retrieve(RetrievalRequest.model_validate(payload))
                assembly = service.assemble(result)
                self._json(HTTPStatus.OK, {
                    "retrieval": result.model_dump(mode="json"),
                    "assembly": assembly.model_dump(mode="json"),
                    "source": "real_models", "llm": False,
                })
            except (ValueError, OSError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"{type(exc).__name__}: {exc}"})

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Matvey RAG/Search demo (real encoders, no LLM): http://{host}:{server.server_port}", flush=True)
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
