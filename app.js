'use strict';
const $=s=>document.querySelector(s);
const normalize=s=>s.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const queryMatch=(text,query)=>normalize(query).split(/\s+/).filter(Boolean).every(term=>normalize(text).includes(term));

if(document.body.dataset.page==='albums'){
  const cards=[...document.querySelectorAll('.album-card')],grid=$('#album-grid');
  const search=$('#album-search'),year=$('#album-year'),sort=$('#album-sort');
  function update(){
    const visible=cards.filter(card=>queryMatch(card.dataset.search,search.value)&&(!year.value||card.dataset.year===year.value));
    cards.forEach(card=>{card.hidden=!visible.includes(card)});
    const ordered=[...cards].sort(sort.value==='az'?(a,b)=>a.dataset.title.localeCompare(b.dataset.title):sort.value==='oldest'?(a,b)=>a.dataset.date.localeCompare(b.dataset.date):(a,b)=>b.dataset.date.localeCompare(a.dataset.date));
    ordered.forEach(card=>grid.append(card));
    $('#album-count').textContent=visible.length+' of '+cards.length+' albums';
    $('#no-albums').hidden=visible.length>0;
    document.querySelectorAll('.jump-links a').forEach(a=>a.hidden=!visible.some(c=>a.hash==='#'+c.id));
  }
  search.addEventListener('input',update);year.addEventListener('change',update);sort.addEventListener('change',update);
  $('#reset-albums').addEventListener('click',()=>{search.value='';year.value='';sort.value='newest';update();search.focus()});
  document.querySelectorAll('.jump-links a').forEach(a=>a.addEventListener('click',()=>{$('#alphabetical-index').open=false}));
  function revealHash(){const target=document.getElementById(location.hash.slice(1));if(target?.classList.contains('album-card')){search.value='';year.value='';update();setTimeout(()=>target.scrollIntoView({block:'start'}),30)}}
  window.addEventListener('hashchange',revealHash);update();if(location.hash)revealHash();
}
if(document.body.dataset.page==='tracks'){
  const rows=[...document.querySelectorAll('#track-body tr')],body=$('#track-body');
  const search=$('#track-search'),artist=$('#track-artist'),sort=$('#track-sort');
  let page=1,filtered=[],pageSize=50;
  function render(reset=false){
    if(reset)page=1;
    filtered=rows.filter(r=>queryMatch(r.dataset.search,search.value)&&(!artist.value||(artist.value==='__blank__'?!r.dataset.artist:r.dataset.artist===artist.value)));
    filtered.sort(sort.value==='az'?(a,b)=>a.dataset.title.localeCompare(b.dataset.title):(a,b)=>b.dataset.date.localeCompare(a.dataset.date));
    const pages=Math.max(1,Math.ceil(filtered.length/pageSize));page=Math.min(page,pages);
    rows.forEach(r=>r.hidden=true);
    filtered.slice((page-1)*pageSize,page*pageSize).forEach(r=>{r.hidden=false;body.append(r)});
    $('#track-count').textContent=filtered.length.toLocaleString()+' of '+rows.length.toLocaleString()+' tracks';
    $('#page-number').textContent=filtered.length?'Page '+page+' of '+pages:'No matches';
    $('#previous-page').disabled=page<=1;$('#next-page').disabled=page>=pages;
    $('#no-tracks').hidden=filtered.length>0;
  }
  search.addEventListener('input',()=>render(true));artist.addEventListener('change',()=>render(true));sort.addEventListener('change',()=>render(true));
  $('#reset-tracks').addEventListener('click',()=>{search.value='';artist.value='';sort.value='newest';render(true);search.focus()});
  $('#previous-page').addEventListener('click',()=>{page--;render();$('#tracks-start').scrollIntoView({block:'start'})});
  $('#next-page').addEventListener('click',()=>{page++;render();$('#tracks-start').scrollIntoView({block:'start'})});
  const params=new URLSearchParams(location.search);if(params.get('q'))search.value=params.get('q');render(true);
}
