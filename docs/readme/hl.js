// Tiny Memesis highlighter for the README renders: colours every <pre class="meme"> in place.
(function () {
  const KW = /\b(pepe|npc|tfw|pikachu|grind|in|until|max|forever|bonk|nah|chad|virgin|F|thisisfine|feelsgood|feelsbad|and|or|not)\b/g;
  const TRUST = /\b(sus|sauce|trustmebro)\b/g;
  const PPL = /\b(apu|fren|wagmi|thonk|smoothbrain|bigbrain|galaxybrain)\b/g;
  const DATA = /\b(such|wow|doge|based|cringe|loss|stonks|touchgrass|copium)\b/g;
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  function line(src) {
    let out = '';
    // comments
    const c = src.search(/\bkek\b/);
    let code = src, cmt = '';
    if (c >= 0) { code = src.slice(0, c); cmt = src.slice(c); }
    // strings
    const parts = code.split(/("(?:[^"\\]|\\.)*")/);
    for (const p of parts) {
      if (!p) continue;
      if (p[0] === '"') { out += '<span class="c-str">' + esc(p) + '</span>'; continue; }
      let t = esc(p);
      t = t.replace(/\byolo\b/g, '<span class="c-yolo">yolo</span>');
      t = t.replace(KW, '<span class="c-kw">$1</span>');
      t = t.replace(TRUST, '<span class="c-trust">$1</span>');
      t = t.replace(PPL, '<span class="c-ppl">$1</span>');
      t = t.replace(DATA, '<span class="c-data">$1</span>');
      t = t.replace(/\b(\d+(?:\.\d+)?(?:ms|s|m|h)?)\b/g, '<span class="c-num">$1</span>');
      t = t.replace(/\b([a-z_][a-z0-9_]*)(?=\()/g, '<span class="c-fn">$1</span>');
      out += t;
    }
    if (cmt) out += '<span class="c-cmt">' + esc(cmt) + '</span>';
    return out;
  }
  window.memesisLine = line;
  document.querySelectorAll('pre.meme').forEach(pre => {
    pre.innerHTML = pre.textContent.split('\n').map(line).join('\n');
  });
})();
