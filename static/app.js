const $=id=>document.getElementById(id);let data=null,filtered=[],page=0;const size=50;
const encode=file=>new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(file)});
const expanded = new Map();
function render(){
 const f=$('fcid').value.trim().toLowerCase(),q=$('order').value.trim().toLowerCase();
 filtered=(data?.orders||[]).filter(o=>o.fcid.toLowerCase().includes(f)&&o.order.toLowerCase().includes(q));
 const pages=Math.ceil(filtered.length/size);page=Math.max(0,Math.min(page,pages-1));
 $('count').textContent=filtered.length.toLocaleString();$('body').replaceChildren();
 for(const o of filtered.slice(page*size,(page+1)*size)){
  const isOpen=expanded.has(o.order)?expanded.get(o.order):o.expanded;
  const heading=document.createElement('tr');heading.className='order-heading';
  const cell=document.createElement('td');cell.colSpan=9;
  const button=document.createElement('button');button.className='order-toggle';button.type='button';button.setAttribute('aria-expanded',String(isOpen));
  button.textContent=`${isOpen?'▾':'▸'} FCID ${o.fcid}  ·  ${o.order}  ·  미출고 ${o.items.length.toLocaleString()} / 전체 ${o.total.toLocaleString()}행 (${o.rate.toFixed(2)}%)  ·  ${isOpen?'접기':'상세 펼치기'}`;
  button.onclick=()=>{expanded.set(o.order,!isOpen);render()};cell.append(button);heading.append(cell);$('body').append(heading);
  if(!isOpen)continue;
  for(const item of o.items){const tr=document.createElement('tr');tr.className='material-row';
   for(const value of [o.fcid,o.order,o.rate.toFixed(2)+'%',item['품목코드'],item['품목명'],item['규격'],item['투입단위'],item['이동잔량'],item['현재고']]){const td=document.createElement('td');td.textContent=value;td.title=value;tr.append(td)}
   $('body').append(tr)
  }
 }
 $('empty').hidden=filtered.length>0;
 if(data&&!filtered.length){$('empty').querySelector('h3').textContent='조건에 맞는 미출고 자재가 없습니다';$('empty').querySelector('p').textContent='FCID 또는 제조오더번호 검색 조건을 확인해 주세요.'}
 $('page-info').textContent=pages?`${page+1} / ${pages} 페이지 · 제조오더 기준`:'';$('prev').disabled=page===0;$('next').disabled=page+1>=pages
}
$('analyze').onclick=async()=>{const master=$('master').files[0],materials=$('materials').files[0];if(!master||!materials){$('status').textContent='PP610과 PP620 파일을 모두 선택해 주세요.';return}if(master.size+materials.size>70*1024*1024){$('status').textContent='파일 합계는 70MB 이하로 선택해 주세요.';return}$('analyze').disabled=true;$('status').textContent='엑셀을 읽고 제조오더별 미출고 비율을 계산하고 있습니다…';try{const [a,b]=await Promise.all([encode(master),encode(materials)]);const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({master:a,materials:b})});const result=await response.json();if(!response.ok)throw Error(result.error);data=result;expanded.clear();page=0;for(const [id,key]of Object.entries({total:'totalOrders',remaining:'unshippedRows',eligible:'eligibleOrders',fcids:'fcids'}))$(id).textContent=data.summary[key].toLocaleString();$('warnings').textContent=Object.entries(data.warnings).map(([k,v])=>`${k}: ${v.toLocaleString()}건`).join(' · ');$('updated').textContent='최종 분석 '+new Date().toLocaleString('ko-KR');$('status').textContent='분석이 완료되었습니다. 새로고침하면 업로드 데이터가 초기화됩니다.';render()}catch(e){$('status').textContent='분석 실패: '+e.message+' 기존 조회 결과는 유지됩니다.'}finally{$('analyze').disabled=false}};
$('search').onsubmit=e=>{e.preventDefault();page=0;render()};$('reset').onclick=()=>{$('fcid').value='';$('order').value='';page=0;render()};$('prev').onclick=()=>{page--;render()};$('next').onclick=()=>{page++;render()};render();
