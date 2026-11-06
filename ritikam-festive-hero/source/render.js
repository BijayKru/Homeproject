const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch({args:['--allow-file-access-from-files']});
 for(const t of ['1','0']){const p=await b.newPage({viewport:{width:1440,height:600},deviceScaleFactor:2});
 await p.goto(`file://${__dirname}/hero.html?t=${t}`);await p.waitForSelector('body[data-ready]');await p.waitForTimeout(300);
 await p.locator('#c').screenshot({path:`${__dirname}/Ritikam_Hero${t==='0'?'_NoText':''}.png`});await p.close();}
 await b.close();})();
