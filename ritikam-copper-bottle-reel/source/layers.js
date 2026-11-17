const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch({args:['--allow-file-access-from-files']});
 const p=await b.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
 for(const l of ['top1','top2','top3','bot1','bot2','bot3','wm','end']){
  await p.goto(`file://${__dirname}/text.html?l=${l}`);await p.waitForSelector('body[data-ready]');await p.waitForTimeout(150);
  await p.screenshot({path:`${__dirname}/L_${l}.png`,omitBackground:true});}
 await b.close();})();
