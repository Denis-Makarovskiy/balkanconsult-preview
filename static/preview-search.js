(function(){
  const q=(new URLSearchParams(location.search).get('q')||'').trim();
  const field=document.getElementById('preview-q'); if(!field) return;
  field.value=q; if(!q) return;
  const words=q.toLocaleLowerCase().split(/\s+/).filter(w=>w.length>2);
  let shown=0;
  document.querySelectorAll('article.hit[data-kind="dossier"]').forEach(hit=>{
    const text=(hit.textContent||'').toLocaleLowerCase();
    const visible=words.length===0||words.some(w=>text.includes(w));
    hit.hidden=!visible; if(visible) shown++;
  });
  const empty=document.getElementById('preview-empty'); if(empty) empty.hidden=shown!==0;
})();
