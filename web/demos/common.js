// 关系图演示页共用：读 graph.json、顶部搜索、图例、底部面板（词卡 / 两个词一起出现的歌词）
const Demo = (() => {
  const COLORS = ["#ffd166", "#ef476f", "#06d6a0", "#4cc9f0", "#b388ff", "#ff9f1c", "#f72585", "#90e0ef", "#c3f73a", "#ff8fab"];
  const OTHER = "#5b6488";
  // 假名 → 罗马音（和主页面同一套规则：拗音、促音、长音）
  const R = {あ:"a",い:"i",う:"u",え:"e",お:"o",か:"ka",き:"ki",く:"ku",け:"ke",こ:"ko",さ:"sa",し:"shi",す:"su",せ:"se",そ:"so",た:"ta",ち:"chi",つ:"tsu",て:"te",と:"to",な:"na",に:"ni",ぬ:"nu",ね:"ne",の:"no",は:"ha",ひ:"hi",ふ:"fu",へ:"he",ほ:"ho",ま:"ma",み:"mi",む:"mu",め:"me",も:"mo",や:"ya",ゆ:"yu",よ:"yo",ら:"ra",り:"ri",る:"ru",れ:"re",ろ:"ro",わ:"wa",ゐ:"i",ゑ:"e",を:"wo",ん:"n",が:"ga",ぎ:"gi",ぐ:"gu",げ:"ge",ご:"go",ざ:"za",じ:"ji",ず:"zu",ぜ:"ze",ぞ:"zo",だ:"da",ぢ:"ji",づ:"zu",で:"de",ど:"do",ば:"ba",び:"bi",ぶ:"bu",べ:"be",ぼ:"bo",ぱ:"pa",ぴ:"pi",ぷ:"pu",ぺ:"pe",ぽ:"po",ゔ:"vu",ぁ:"a",ぃ:"i",ぅ:"u",ぇ:"e",ぉ:"o",ゃ:"ya",ゅ:"yu",ょ:"yo",ゎ:"wa"};
  const toHira = s => s.replace(/[ァ-ヶ]/g, c => String.fromCharCode(c.charCodeAt(0) - 0x60));
  const P = {"、": ",", "。": ".", "？": "?", "！": "!", "　": " ", "ー": "-"};
  function morae(s) { const out = []; for (const c of s) { const last = out[out.length - 1];
    if (last !== undefined && (/[ゃゅょぁぃぅぇぉゎャュョァィゥェォヮ]/.test(c) || c === "ー") && !/[っッ]$/.test(last)) out[out.length - 1] += c;
    else if (last !== undefined && /[っッ]$/.test(last)) out[out.length - 1] += c; else out.push(c); } return out; }
  function unit(u) { const h = toHira(u);
    if (/^っ/.test(h)) { const r = unit(h.slice(1)); return r ? (r.startsWith("ch") ? "t" + r : r[0] + r) : ""; }
    if (h.endsWith("ー")) { const r = unit(h.slice(0, -1)); return r + ((r.match(/[aeiou](?!.*[aeiou])/) || [""])[0]); }
    const r = R[h[0]]; if (r === undefined) return P[h[0]] !== undefined ? P[h[0]] : u;
    const sm = h.slice(1); if (!sm) return r; const sr = R[sm] || "";
    if (/[ゃゅょ]/.test(sm)) return /^(shi|chi|ji)$/.test(r) ? r.slice(0, -1) + sr.slice(1) : r.slice(0, -1) + sr;
    return r.replace(/[aeiou]$/, "") + sr; }
  const romaji = s => s.split(" ").map(w => { const us = morae(w); return us.map((u, i) => { const r = unit(u);
    return r === "n" && i + 1 < us.length && /^[aeiouy]/.test(unit(us[i + 1])) ? "n'" : r; }).join(""); }).join(" ");
  const $ = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

  async function load() {
    const d = await (await fetch("graph.json")).json();
    d.nodes.forEach(n => { n.color = n.g >= 0 ? COLORS[n.g] : OTHER; n.edges = []; });
    d.edges.forEach((e, i) => { e.id = i; d.nodes[e.s].edges.push(e); d.nodes[e.t].edges.push(e); });
    d.nodes.forEach(n => n.edges.sort((a, b) => b.w - a.w));
    d.other = (e, n) => d.nodes[e.s === n.id ? e.t : e.s];
    // 只画最大的一张连通网络：没有连线的词、和主体不相连的几小撮词不画（面板里照样能看到它们）
    const comp = new Map(); let best = null, bestSize = 0;
    d.nodes.forEach(n => {
      if (comp.has(n.id) || !n.edges.length) return;
      const stack = [n], ids = []; comp.set(n.id, n.id);
      while (stack.length) { const x = stack.pop(); ids.push(x.id); x.edges.forEach(e => { const o = d.other(e, x); if (!comp.has(o.id)) { comp.set(o.id, n.id); stack.push(o); } }); }
      if (ids.length > bestSize) { bestSize = ids.length; best = n.id; }
    });
    d.linked = d.nodes.filter(n => comp.get(n.id) === best);
    d.links = d.edges.filter(e => comp.get(e.s) === best);
    return d;
  }

  // 一句歌词：两个词分别高亮
  function lyric(d, key, spansA, spansB, colA, colB, times) {
    const [ja, zh, song, album, rd] = d.lines[key];
    const box = $("div", "lyric"), p = $("div", "ja");
    const cls = [...ja].map((_, i) => spansA.some(([a, b]) => a <= i && i < b) ? "a" : (spansB || []).some(([a, b]) => a <= i && i < b) ? "b" : "");
    let run = "", cur = null;
    const flush = () => { if (!run) return; if (cur) { const m = $("mark", cur === "b" ? "b" : "", run); p.appendChild(m); } else p.appendChild(document.createTextNode(run)); run = ""; };
    [...ja].forEach((ch, i) => { if (cls[i] !== cur) { flush(); cur = cls[i]; } run += ch; }); flush();
    box.style.setProperty("--a", colA); box.style.setProperty("--b", colB || colA);
    box.appendChild(p);
    if (rd) box.appendChild($("div", "ro", romaji(rd)));
    if (zh) box.appendChild($("div", "zh", zh));
    box.appendChild($("div", "src", "《" + song + "》· " + album + (times > 1 ? " · 这句唱了 " + times + " 遍" : "")));
    const s = $("button", "spk", "▶ 朗读这句"); s.onclick = () => speak(ja); box.appendChild(s);
    return box;
  }
  function speak(t) { try { speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(t); u.lang = "ja-JP"; u.rate = .85; speechSynthesis.speak(u); } catch (e) {} }

  function setup(d, opt) {
    const top = $("div", "top");
    const back = $("a", "back", "‹ 方案列表"); back.href = "./";
    const title = $("div", "title", opt.title);
    const sw = $("div", "search"), inp = $("input"); inp.placeholder = "找一个词：汉字、假名或中文"; inp.type = "search";
    const sugg = $("div", "sugg"); sugg.hidden = true; sw.append(inp, sugg);
    const ib = $("button", "infob", "i"); ib.type = "button"; ib.setAttribute("aria-label", "说明和图例");
    top.append(back, title, sw, ib); document.body.appendChild(top);
    inp.addEventListener("input", () => {
      const q = inp.value.trim(); sugg.innerHTML = ""; sugg.hidden = !q; if (!q) return;
      d.linked.filter(n => n.full.includes(q) || n.k.includes(q) || n.m.includes(q)).sort((a, b) => b.n - a.n).slice(0, 6).forEach(n => {
        const b = $("button"); b.append($("b", null, n.w), $("span", null, n.m)); b.onclick = () => { inp.value = ""; sugg.hidden = true; opt.focus(n); }; sugg.appendChild(b);
      });
      if (!sugg.children.length) sugg.appendChild($("button", null, "没有找到（只有和别的词有连线的词才在图里）"));
    });

    // 说明和图例：点右上角的 i 才出现，平时不挡图
    const info = $("div", "infobox"); info.hidden = true;
    info.appendChild($("h3", null, "怎么看这张图"));
    const hint = $("p", "howto", opt.hint || "点一个词看它的关系；点一条线看两个词一起出现的歌词。");
    info.appendChild(hint);
    info.appendChild($("p", null, "每个点是一个词，点越大，出现在越多首歌里。两个词在同一句歌词里一起出现过 2 次以上，就连一条线；线越粗，一起出现得越多。"));
    info.appendChild($("h3", null, "颜色：经常一起出现的词分成一组"));
    info.appendChild($("p", null, "程序按连线把「经常在同一句里出现」的词自动分成 10 组，同一组用同一种颜色，往往是同一类场景或情绪。每组用组里最常见的 3 个词命名；没分进这 10 组的是灰色。"));
    d.groups.forEach((g, i) => { const r = $("div", "gi"); const c = $("i"); c.style.background = c.style.color = COLORS[i]; r.append(c, g); info.appendChild(r); });
    const r = $("div", "gi"); const c = $("i"); c.style.background = c.style.color = OTHER; r.append(c, "其他"); info.appendChild(r);
    document.body.appendChild(info);
    ib.onclick = e => { e.stopPropagation(); info.hidden = !info.hidden; ib.classList.toggle("on", !info.hidden); };
    document.addEventListener("pointerdown", e => { if (!info.hidden && !info.contains(e.target) && e.target !== ib) { info.hidden = true; ib.classList.remove("on"); } });

    const panel = $("div", "panel"); panel.hidden = true; document.body.appendChild(panel);
    const close = () => { panel.hidden = true; opt.onClose && opt.onClose(); };
    // 面板可以收起成一行标题，不挡住图；收起状态在换词时保持
    let mini = false;
    const head = () => { panel.innerHTML = ""; panel.hidden = false; panel.classList.toggle("min", mini);
      const bar = $("div", "pbtns"), m = $("button", "pmin", mini ? "展开" : "收起"), x = $("button", "px", "×");
      m.onclick = () => { mini = !mini; panel.classList.toggle("min", mini); m.textContent = mini ? "展开" : "收起"; };
      x.onclick = close; bar.append(m, x); panel.appendChild(bar); };

    function showNode(n) {
      head();
      panel.append($("div", "pw", n.w), $("div", "pk", n.k + " · " + n.r), $("div", "pm", n.m),
        $("div", "pmeta", "出现在 " + n.n + " 首歌 · " + (n.g >= 0 ? "词群「" + d.groups[n.g] + "」" : "其他") + (n.band === "both" ? " · 两个乐队都唱过" : " · " + d.bands[n.band])));
      if (n.ex && d.lines[n.ex[0]]) { panel.appendChild($("div", "ph", "歌词例句")); panel.appendChild(lyric(d, n.ex[0], n.ex[1], [], n.color)); }
      panel.appendChild($("div", "ph", "常和它在同一句歌词里出现的词（数字是一起出现了几句，点一个看这些歌词）"));
      const ch = $("div", "chips");
      n.edges.slice().sort((a, b) => b.n - a.n || b.w - a.w).forEach(e => { const o = d.other(e, n); const b = $("button", "chip"); b.append(o.w, $("small", null, e.n + " 句")); b.onclick = () => showEdge(e, n);
        b.onmouseenter = () => opt.onPreview && opt.onPreview(e); b.onmouseleave = () => opt.onPreview && opt.onPreview(null); ch.appendChild(b); });
      panel.appendChild(ch);
    }
    function showEdge(e, from) {
      const a = from && from.id === e.t ? d.nodes[e.t] : d.nodes[e.s], b = d.other(e, a), flip = a.id !== e.s;
      head();
      const pr = $("div", "pair"); pr.append(a.w, $("em", null, "×"), b.w); panel.appendChild(pr);
      panel.appendChild($("div", "pk", a.r + " × " + b.r));
      panel.appendChild($("div", "pmeta", a.m + " × " + b.m));
      const shown = e.refs.reduce((x, r) => x + (r[3] || 1), 0);
      panel.appendChild($("div", "ph", "这两个词在 " + e.n + " 句歌词里一起出现过" + (shown < e.n ? "（下面是前 " + shown + " 句）" : "") + "，重复的句子只列一次："));
      e.refs.forEach(([key, sa, sb, times]) => panel.appendChild(lyric(d, key, flip ? sb : sa, flip ? sa : sb, a.color, b.color, times)));
      const ch = $("div", "chips"); ch.style.marginTop = "12px";
      [a, b].forEach(n => { const x = $("button", "chip", "看「" + n.w + "」的关系"); x.onclick = () => opt.focus(n);
        x.onmouseenter = () => opt.onPreviewNode && opt.onPreviewNode(n); x.onmouseleave = () => opt.onPreviewNode && opt.onPreviewNode(null); ch.appendChild(x); });
      panel.appendChild(ch);
      opt.onEdge && opt.onEdge(e);
    }
    return { showNode, showEdge, close, hint, romaji, panel };
  }
  return { load, setup, romaji, COLORS, OTHER, $ };
})();
