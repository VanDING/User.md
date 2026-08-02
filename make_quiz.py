#!/usr/bin/env python3
"""从 questionnaire.json 生成自包含 HTML 问卷（v3：i18n + 可选补充字段 + 重设计）。

用法: python3 make_quiz.py [questionnaire.json] [-o quiz.html]
特性:
- LANG 语言题实时切换界面语言（zh / en / bilingual，静态双语 span + CSS 切换）
- 末尾可选自由补充字段 EXT（百分号编码进答案串，parse_answers.py 原样解码）
- 设计: "校准标尺"主题——顶部 60 刻度进度尺（测度仪器隐喻），等宽刻度数字与
  答案串输出；衬线标题 + 无衬线正文；单列卡片带左侧刻度轨。
"""
import argparse
import json


def esc(s):
    import html as _html
    return _html.escape(str(s), quote=True)


def dual(zh, en):
    """双语 span 对：由 body[data-lang] 的 CSS 决定显示哪个。"""
    return (f'<span class="tzh" lang="zh">{esc(zh)}</span>'
            f'<span class="ten" lang="en">{esc(en)}</span>')


def render_item(it, idx, anchors_zh, anchors_en):
    oid = it["id"]
    t = it["type"]
    dom_type = "yn" if t in ("yn", "check") else t
    text = dual(it["text"], it.get("text_en", it["text"]))
    if t == "slider":
        opts = "".join(
            f'<label class="opt"><input type="radio" name="{oid}" value="{v}">'
            f'<span class="num">{v}</span><span class="lab">{dual(anchors_zh[v], anchors_en[v])}</span></label>'
            for v in anchors_zh
        )
        inner = f'<div class="qtext">{text}</div><div class="optrow">{opts}</div>'
    else:  # yn / check —— 渲染一致，DOM 统一标 yn
        inner = (f'<div class="qtext">{text}</div><div class="ynrow">'
                 f'<label class="yn"><input type="radio" name="{oid}" value="yes">{dual("是", "Yes")}</label>'
                 f'<label class="yn"><input type="radio" name="{oid}" value="no">{dual("否", "No")}</label>'
                 f'</div>')
    return (f'<div class="q" data-id="{oid}" data-type="{dom_type}">'
            f'<div class="rail"><i class="tick"></i><span class="no">{idx}</span></div>'
            f'<div class="qbody">{inner}</div></div>')


def build(q):
    items = sorted(q["items"], key=lambda it: it["order"])
    meta = q.get("meta", {})
    en = meta.get("en", {})
    anchors_zh = {str(v): meta["anchors"][str(v)] for v in sorted(meta["anchors"], key=int)}
    anchors_en = {str(v): en["anchors"][str(v)] for v in sorted(en["anchors"], key=int)}
    start = meta.get("start_items", [{}])[0]
    lang_opts = "".join(
        f'<label class="yn"><input type="radio" name="LANG" value="{v}">{esc(t)}</label>'
        for v, t in zip(["zh", "en", "bilingual"], start.get("options", ["中文", "English", "双语"]))
    )
    lang_card = (f'<div class="q lang" data-id="LANG" data-type="language">'
                 f'<div class="rail"><i class="tick done"></i><span class="no">●</span></div>'
                 f'<div class="qbody"><div class="qtext">{dual(start.get("text_zh"), start.get("text_en"))}</div>'
                 f'<div class="ynrow">{lang_opts}</div></div></div>')

    items_html = "".join(render_item(it, i + 1, anchors_zh, anchors_en) for i, it in enumerate(items))
    ids = [it["id"] for it in items]
    ticks = "".join('<i></i>' for _ in range(len(ids) + 1))  # LANG + 59

    i18n = {
        "zh": {
            "title": "AI 协作用户认知测评",
            "sub": "共 60 题 · 打分题 1-5（1 完全不同意 → 5 完全同意）· 其余 是/否 · 预计 8-10 分钟",
            "intro": "下面是一组关于你如何与 AI 协作的陈述。凭第一反应作答即可，没有对错。全部答完后会生成一个答案串——把它粘贴回对话，AI 将据此生成你的协作画像。",
            "ext_label": "还有要补充的吗？（可选）",
            "ext_placeholder": "例如：常用的工具、正在做的项目、希望 AI 特别注意的情境……（选填，不超过 500 字）",
            "submit": "生成答案串",
            "copy": "复制答案串",
            "done": "完成！把下面的答案串粘贴回对话发给 AI：",
            "miss": "还有 {n} 题未作答（{list}）",
            "copied": "已复制，粘贴回对话即可",
            "privacy": "答案仅用于生成你的个人协作画像，不会上传到任何服务器。",
            "optional_tag": "可选"
        },
        "en": {
            "title": "AI Collaboration User Assessment",
            "sub": en.get("subtitle", "A ~60-item questionnaire on a 5-point scale. Takes about 8–10 minutes."),
            "intro": "Below are statements about how you like to work with an AI. Go with your first reaction — there are no right answers. When you finish, an answer string is generated: paste it back into the chat and the AI will build your collaboration profile from it.",
            "ext_label": "Anything else? (optional)",
            "ext_placeholder": "e.g. tools you use, projects you work on, situations where AI should behave differently… (optional, max 500 chars)",
            "submit": "Generate answer string",
            "copy": "Copy answer string",
            "done": "Done! Paste the answer string below back into the chat:",
            "miss": "{n} unanswered items ({list})",
            "copied": "Copied — paste it back into the chat",
            "privacy": "Your answers are used only to build your personal profile; nothing is uploaded to any server.",
            "optional_tag": "Optional"
        }
    }

    html_doc = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 协作用户认知测评</title>
<style>
:root{
  --paper:#F4F5F1; --ink:#1F2A37; --muted:#6B7A87;
  --accent:#147D74; --accent-soft:#E3EFED; --line:#DDE2DC; --warn:#B3402E;
  --serif:"Songti SC","Noto Serif CJK SC",Georgia,"Times New Roman",serif;
  --sans:-apple-system,"PingFang SC","Segoe UI","Microsoft YaHei",sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font:15px/1.7 var(--sans);background:var(--paper);color:var(--ink);-webkit-font-smoothing:antialiased}
body[data-lang="zh"] .ten{display:none}
body[data-lang="en"] .tzh{display:none}
body[data-lang="en"] .ten{display:inline}
body[data-lang="en"] .qtext .ten,body[data-lang="en"] .opt .lab .ten{display:block}
body[data-lang="bilingual"] .tzh{display:block}
body[data-lang="bilingual"] .ten{display:block;font-size:13px;color:var(--muted);margin-top:2px}
body[data-lang="bilingual"] .opt .lab .ten{display:block;margin-top:0}
.ten{display:none}

header{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--paper) 88%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:14px 0 12px}
.wrap{max-width:680px;margin:0 auto;padding:0 20px}
.brand{display:flex;align-items:baseline;gap:10px}
.diamond{width:9px;height:9px;background:var(--accent);transform:rotate(45deg);display:inline-block;flex:0 0 auto;align-self:center}
h1{font:700 22px/1.3 var(--serif);letter-spacing:.01em}
.sub{font-size:12.5px;color:var(--muted);margin-top:3px}
.ruler{position:relative;height:22px;margin-top:10px}
.ruler .track{position:absolute;left:0;right:0;top:9px;height:4px;background:var(--line);border-radius:2px;overflow:hidden}
.ruler .fill{position:absolute;left:0;top:0;bottom:0;width:0;background:var(--accent);transition:width .35s cubic-bezier(.2,.8,.2,1)}
.ruler .ticks{position:absolute;left:0;right:0;top:2px;display:flex;justify-content:space-between;height:18px}
.ruler .ticks i{width:1px;height:6px;background:var(--line)}
.ruler .ticks i.on{background:var(--accent);height:10px}
.ruler .num{position:absolute;right:0;top:0;font:600 11px var(--mono);color:var(--muted)}

main{padding:22px 0 120px}
.intro{font-size:14px;color:#3A4856;background:#fff;border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:10px;padding:14px 16px;margin-bottom:18px}
.q{display:flex;gap:14px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 18px 16px 8px;margin:0 0 12px}
.q .rail{flex:0 0 40px;display:flex;flex-direction:column;align-items:center;gap:6px;position:relative}
.q .rail::before{content:"";position:absolute;left:50%;top:-12px;bottom:-12px;width:1px;background:var(--line)}
.q:first-of-type .rail::before{display:none}
.q .rail .tick{width:7px;height:7px;border:1.5px solid var(--line);border-radius:50%;background:var(--paper);z-index:1;margin-top:8px;transition:all .2s}
.q.answered .rail .tick{background:var(--accent);border-color:var(--accent)}
.q .rail .no{font:600 11px var(--mono);color:var(--muted);z-index:1;background:var(--paper);padding:0 3px}
.q.lang .rail .tick{background:var(--accent);border-color:var(--accent)}
.q.lang .rail .no{color:var(--accent)}
.qbody{flex:1}
.qtext{font-weight:500;margin-bottom:12px}
.q.miss{border-color:var(--warn);box-shadow:0 0 0 3px color-mix(in srgb,var(--warn) 14%,transparent)}
.optrow{display:flex;gap:8px;flex-wrap:wrap}
.opt{flex:1 1 104px;display:flex;flex-direction:column;align-items:center;gap:3px;border:1px solid var(--line);border-radius:9px;padding:9px 6px 7px;cursor:pointer;user-select:none;text-align:center;transition:border-color .15s,background .15s}
.opt input{position:absolute;opacity:0;pointer-events:none}
.opt:has(input:checked){border-color:var(--accent);background:var(--accent-soft)}
.opt .num{font:700 17px var(--mono);color:var(--ink)}
.opt:has(input:checked) .num{color:var(--accent)}
.opt .lab{font-size:11px;color:var(--muted);line-height:1.35}
.opt:has(input:checked) .lab{color:var(--accent);font-weight:600}
.ynrow{display:flex;gap:10px}
.yn{border:1px solid var(--line);border-radius:8px;padding:7px 18px;cursor:pointer;user-select:none;font-size:14px;transition:all .15s}
.yn:has(input:checked){border-color:var(--accent);background:var(--accent-soft);color:var(--accent);font-weight:600}
.yn input{margin-right:6px;accent-color:var(--accent)}

.ext{border-style:dashed;background:color-mix(in srgb,var(--paper) 40%,#fff)}
.ext .qtext{margin-bottom:6px}
.ext .tag{display:inline-block;font:600 10px var(--mono);color:var(--accent);border:1px solid var(--accent);border-radius:99px;padding:0 8px;margin-left:8px;vertical-align:middle;letter-spacing:.05em}
textarea{width:100%;min-height:90px;font:13px/1.6 var(--mono);border:1px solid var(--line);border-radius:9px;padding:10px 12px;resize:vertical;background:#fff;color:var(--ink)}
textarea:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
textarea::placeholder{color:#9AA7B0}

.act{position:fixed;bottom:0;left:0;right:0;background:color-mix(in srgb,var(--paper) 90%,transparent);backdrop-filter:blur(8px);border-top:1px solid var(--line);padding:12px 20px;text-align:center}
button{font:600 15px var(--sans);padding:11px 34px;border:none;border-radius:10px;background:var(--ink);color:#fff;cursor:pointer;transition:background .15s,transform .1s}
button:hover{background:var(--accent)}
button:active{transform:scale(.98)}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.result{display:none;margin:18px 0 0;background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px}
.result .hint{color:var(--muted);font-size:13px;margin-bottom:8px}
#out{height:120px}
.privacy{text-align:center;color:var(--muted);font-size:12px;margin-top:10px}
.privacy .tzh,.privacy .ten{display:inline}
@media (prefers-reduced-motion: reduce){
  *{transition:none!important;animation:none!important}
  html{scroll-behavior:auto}
}
@media (max-width:560px){
  .opt{flex:1 1 30%}
  .q{gap:10px}
}
@media (min-width:561px){
  .q:not(.answered) .rail .tick{border-color:#C9D2CC}
}
</style>
</head>
<body data-lang="bilingual">
<div class="wrap">
<header>
  <div class="brand"><i class="diamond"></i><h1>__H1__</h1></div>
  <p class="sub">__SUB__</p>
  <div class="ruler">
    <div class="num" id="rulerNum">0/60</div>
    <div class="track"><div class="fill" id="rulerFill"></div></div>
    <div class="ticks" id="rulerTicks">__TICKS__</div>
  </div>
</header>
<main>
  <div class="intro">__INTRO__</div>
  __LANG_CARD__
  __ITEMS__
  <div class="q ext" data-id="EXT" data-type="ext">
    <div class="rail"><i class="tick"></i><span class="no">+</span></div>
    <div class="qbody">
      <div class="qtext">__EXT_LABEL__<span class="tag">__OPTIONAL__</span></div>
      <textarea id="ext" maxlength="500"></textarea>
    </div>
  </div>
  <div class="result" id="result">
    <div class="hint">__DONE__</div>
    <textarea id="out" readonly></textarea>
    <div class="hint" style="text-align:center;margin-top:10px;margin-bottom:0">
      <button id="copy" type="button" style="font-size:14px;padding:9px 26px">__COPY__</button>
    </div>
  </div>
</main>
</div>
<div class="act">
  <button id="submit" type="button">__SUBMIT__</button>
</div>
<p class="privacy">__PRIVACY__</p>
<script>
(function(){
  var N = __N__;
  var TICKS = document.getElementById('rulerTicks').children;
  var IDS = __IDS__;            // 59 个题号（顺序 = 尺刻度 1..59；刻度 0 = LANG）
  var I18N = __I18N__;

  function primary(){ var l = document.body.getAttribute('data-lang'); return l === 'en' ? 'en' : 'zh'; }
  function pick(k){ return I18N[primary()][k]; }

  document.getElementById('rulerNum').textContent = '0/' + N;

  function setLang(lang){
    document.body.setAttribute('data-lang', lang);
    document.title = pick('title');
    document.getElementById('ext').placeholder = pick('ext_placeholder');
  }
  document.querySelectorAll('input[name="LANG"]').forEach(function(r){
    r.addEventListener('change', function(){ setLang(r.value); });
  });

  function answered(id){
    if (id === 'EXT') return false;
    return !!document.querySelector('input[name="'+id+'"]:checked');
  }
  function mark(ids){
    TICKS[0].classList.toggle('on', !!document.querySelector('input[name="LANG"]:checked'));
    ids.forEach(function(id, i){
      var on = answered(id);
      TICKS[i + 1].classList.toggle('on', on);
      var card = document.querySelector('[data-id="'+id+'"]');
      if (card) card.classList.toggle('answered', on);
    });
  }
  function count(){
    var c = 0, i;
    for (i = 0; i < IDS.length; i++) if (answered(IDS[i])) c++;
    var l = document.querySelector('input[name="LANG"]:checked') ? 1 : 0;
    c += l;
    document.getElementById('rulerFill').style.width = (100 * c / N) + '%';
    document.getElementById('rulerNum').textContent = c + '/' + N;
    return c;
  }
  document.querySelectorAll('.q input').forEach(function(inp){
    inp.addEventListener('change', function(){ mark(IDS); count(); });
  });

  document.getElementById('submit').addEventListener('click', function(){
    var miss = [];
    if (!document.querySelector('input[name="LANG"]:checked')) miss.push('LANG');
    IDS.forEach(function(id){ if (!answered(id)) miss.push(id); });
    if (miss.length){
      var el = document.querySelector('[data-id="'+miss[0]+'"]');
      el.classList.add('miss');
      el.scrollIntoView({behavior:'smooth', block:'center'});
      setTimeout(function(){ el.classList.remove('miss'); }, 1600);
      alert(pick('miss').replace('{n}', miss.length).replace('{list}',
        miss.slice(0,6).join(', ') + (miss.length > 6 ? ' …' : '')));
      return;
    }
    var parts = ['LANG=' + document.querySelector('input[name="LANG"]:checked').value];
    IDS.forEach(function(id){
      parts.push(id + '=' + document.querySelector('input[name="'+id+'"]:checked').value);
    });
    var ext = document.getElementById('ext').value.trim();
    if (ext) parts.push('EXT=' + encodeURIComponent(ext));
    document.getElementById('out').value = parts.join(';');
    document.getElementById('result').style.display = 'block';
    document.getElementById('submit').style.display = 'none';
    document.getElementById('out').focus();
    document.getElementById('out').select();
  });
  document.getElementById('copy').addEventListener('click', function(){
    var ta = document.getElementById('out');
    ta.select(); ta.setSelectionRange(0, 99999);
    try{
      navigator.clipboard.writeText(ta.value).then(function(){ alert(pick('copied')); },
        function(){ document.execCommand('copy'); alert(pick('copied')); });
    }catch(e){ document.execCommand('copy'); alert(pick('copied')); }
  });

  mark(IDS); count();
  // 滚动浮现（尊重 reduced-motion）
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches){
    var io = new IntersectionObserver(function(es){
      es.forEach(function(e){ if (e.isIntersecting){ e.target.style.animation = 'in .4s ease both'; io.unobserve(e.target); } });
    }, {rootMargin:'0px 0px -40px 0px'});
    document.querySelectorAll('.q').forEach(function(el){ io.observe(el); });
  }
  var st = document.createElement('style');
  st.textContent = '@keyframes in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}';
  document.head.appendChild(st);
})();
</script>
</body>
</html>"""

    html_doc = (html_doc
        .replace("__H1__", dual(i18n["zh"]["title"], i18n["en"]["title"]))
        .replace("__SUB__", dual(i18n["zh"]["sub"], i18n["en"]["sub"]))
        .replace("__INTRO__", dual(i18n["zh"]["intro"], i18n["en"]["intro"]))
        .replace("__LANG_CARD__", lang_card)
        .replace("__ITEMS__", items_html)
        .replace("__EXT_LABEL__", dual(i18n["zh"]["ext_label"], i18n["en"]["ext_label"]))
        .replace("__OPTIONAL__", dual(i18n["zh"]["optional_tag"], i18n["en"]["optional_tag"]))
        .replace("__DONE__", dual(i18n["zh"]["done"], i18n["en"]["done"]))
        .replace("__COPY__", dual(i18n["zh"]["copy"], i18n["en"]["copy"]))
        .replace("__SUBMIT__", dual(i18n["zh"]["submit"], i18n["en"]["submit"]))
        .replace("__PRIVACY__", dual(i18n["zh"]["privacy"], i18n["en"]["privacy"]))
        .replace("__TICKS__", ticks)
        .replace("__N__", str(len(ids) + 1))
        .replace("__IDS__", json.dumps(ids))
        .replace("__I18N__", json.dumps(i18n, ensure_ascii=False)))
    return html_doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("questionnaire", nargs="?", default="questionnaire.json")
    ap.add_argument("-o", "--out", default="quiz.html")
    args = ap.parse_args()
    q = json.load(open(args.questionnaire, encoding="utf-8"))
    open(args.out, "w", encoding="utf-8").write(build(q))
    n = len(q["items"]) + 1
    size = len(open(args.out, encoding="utf-8").read())
    print(f"✓ {args.out}（{n} 题，{size} 字节）")


if __name__ == "__main__":
    main()
