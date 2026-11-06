const {chromium}=require('playwright');
(async()=>{
 const b=await chromium.launch({args:['--allow-file-access-from-files']});
 const out=process.argv[2]||'out'; require('fs').mkdirSync(out,{recursive:true});
 const jobs=[];
 for(const v of ['dhanteras','diwali']) for(const l of ['desktop','mobile']) for(const t of ['1','0']) jobs.push({v,l,t});
 for(const j of jobs){
  const D=j.l==='desktop', w=D?1440:540, h=D?600:675;
  const p=await b.newPage({viewport:{width:w,height:h},deviceScaleFactor:2});
  await p.goto(`file://${__dirname}/banner.html?v=${j.v}&l=${j.l}&t=${j.t}`);
  await p.waitForSelector('body[data-ready]'); await p.waitForTimeout(300);
  const name=`Ritikam_${j.v[0].toUpperCase()+j.v.slice(1)}_Hero_${D?'Desktop_2880x1200':'Mobile_1080x1350'}${j.t==='0'?'_NoText':''}.png`;
  await p.locator('#c').screenshot({path:`${out}/${name}`}); await p.close(); console.log(name);
 }
 await b.close();
})();
