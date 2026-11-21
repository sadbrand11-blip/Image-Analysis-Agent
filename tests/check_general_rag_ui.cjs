// Retrieval status must distinguish no evidence, unavailable models and an experiment.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path');
const repo=process.argv[2]||path.resolve(__dirname,'..');
function node(tag){return {tag,children:[],textContent:'',value:'',append(...items){this.children.push(...items)},replaceChildren(...items){this.children=items},focus(){},set innerHTML(_){throw Error('Use text content')}};}
const elements=new Map();
const get=id=>{if(!elements.has(id))elements.set(id,node(id));return elements.get(id)};
get('question').value='为什么框数量不能说明更准确？';get('vision').value='general_rgb_v1';get('corpus').value='general-natural-v2';get('top-k').value='3';
let payload;
const context=vm.createContext({document:{getElementById:get,createElement:node},fetch:async(url,options)=>{
 payload=JSON.parse(options.body);
 return {ok:true,json:async()=>({comparisons:{
  tfidf:{available:true,query_ms:1,load_ms:2,results:[],empty_reason:'未交付证据',metadata:{corpus:'general-natural-v2',corpus_hash:'abc123',evaluation_status:'complete',acceptance_status:'experimental_explicit_selection',release_notice:'手动实验',fallback_reason:'fixture fallback',thresholds:{tfidf:.4,dense:.8}}},
  embedding:{available:false,error:'模型缺失',results:null},
  hybrid:{available:true,query_ms:3,load_ms:4,metadata:{corpus:'general-natural-v2',corpus_hash:'abc123'},results:[{title:'真实来源',text:'<script>not HTML</script>',source:'https://example.org/evidence',source_type:'project_policy',verification_level:'project_files',citation_id:'actual:1',score_kind:'rrf_rank_fusion',score:.03,tfidf_score:.5,embedding_score:.8,source_start:12,source_end:20}]}
 }})};
}});
vm.runInContext(fs.readFileSync(path.join(repo,'static/knowledge.js'),'utf8'),context);
const text=n=>[n.textContent,...n.children.map(text)].join('\n');
(async()=>{
 await get('search-form').onsubmit({preventDefault(){}});
 assert.equal(payload.corpus_version,'general-natural-v2');
 const output=text(get('rankings'));
 for(const expected of ['手动语料对照','已完成','手动实验','fixture fallback','未交付证据','模型缺失','非概率','actual:1','<script>not HTML</script>'])assert.ok(output.includes(expected),expected);
 assert.equal(get('rankings').children.length,3);
 assert.ok(text(get('status')).includes('没有调用付费 API'));
 console.log('PASS: general RAG UI corpus, evaluation, unavailable/empty, fallback and literal evidence checks');
})().catch(error=>{console.error(error);process.exitCode=1});
