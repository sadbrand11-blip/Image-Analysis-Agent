const el=(tag,text)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;return x;};
const statusLabel=value=>({complete:'已完成',not_run:'未运行',not_formally_evaluated:'尚未独立验收',passed_small_scale_project_eval:'通过小规模项目评测',not_promoted_current_default_retained:'未达发布门槛，保留原配置',experimental_explicit_selection:'手动语料对照',experimental_explicit_mode:'手动方法对照',degraded_not_equivalent_to_release:'降级运行，成绩不直接适用'}[value]||value||'未记录');
document.getElementById('research-example').onclick=()=>{document.getElementById('question').value='图像质量分数、检测框数量及分数上升能代替真实框标注下的召回与误报评测吗？';document.getElementById('question').focus();};
document.getElementById('search-form').onsubmit=async event=>{
 event.preventDefault();const button=document.getElementById('search'),status=document.getElementById('status');button.disabled=true;status.textContent='正在本地检索，首次加载模型可能稍慢…';
 try{const response=await fetch('/api/knowledge/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:document.getElementById('question').value,vision_mode:document.getElementById('vision').value,corpus_version:document.getElementById('corpus').value||null,top_k:Number(document.getElementById('top-k').value)})});const data=await response.json();if(!response.ok)throw new Error(data.error);
 const panel=document.getElementById('rankings');panel.replaceChildren();
 for(const mode of ['tfidf','embedding','hybrid','legacy']){const result=data.comparisons[mode];if(!result)continue;const card=el('section');card.className='card';card.append(el('h2',({tfidf:'TF-IDF 词语匹配',embedding:'Embedding 语义检索',hybrid:'Hybrid 排名融合'}[mode]||mode)));
 if(!result.available){card.append(el('p','不可用：'+result.error));panel.append(card);continue;}
 card.append(el('p',`查询 ${result.query_ms.toFixed(1)} ms · 加载 ${result.load_ms.toFixed(1)} ms`));card.append(el('p',`语料 ${result.metadata.corpus} · 版本 ${result.metadata.corpus_hash.slice(0,12)}`));
 card.append(el('p',`评测：${statusLabel(result.metadata.evaluation_status)} · 采用状态：${statusLabel(result.metadata.acceptance_status)}`));
 if(result.metadata.release_notice)card.append(el('p',result.metadata.release_notice));
 if(result.metadata.fallback_reason)card.append(el('p','已降级：'+result.metadata.fallback_reason));
 if(result.metadata.thresholds)card.append(el('p',`拒绝阈值：TF-IDF ${result.metadata.thresholds.tfidf} · Embedding ${result.metadata.thresholds.dense}（均非概率）`));
 if(!result.results.length)card.append(el('p',result.empty_reason));
 result.results.forEach((r,i)=>{const item=el('article');item.append(el('h3',`${i+1}. ${r.title}`));item.append(el('p',`类型：${r.source_type||'历史资料'} · 核实：${r.verification_level||'项目文件'}`));if(r.version_warning)item.append(el('p',r.version_warning));item.append(el('p',`${r.score_kind||'tfidf_cosine'}：${r.score}（非概率）`));if(r.tfidf_score!=null)item.append(el('p',`TF-IDF ${r.tfidf_score} · Embedding ${r.embedding_score==null?'未计算':r.embedding_score}`));item.append(el('p',r.text));const link=el('a','查看出处');link.href=r.source;link.target='_blank';link.rel='noopener noreferrer';item.append(link,el('p',`引用 ${r.citation_id} · 源位置 ${r.source_start==null?'旧分段':r.source_start+'—'+r.source_end}`));card.append(item);});panel.append(card);}
 status.textContent='对照完成；没有调用付费 API。';
 }catch(error){status.textContent=error.message;}finally{button.disabled=false;}
};
