const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch({args:['--allow-file-access-from-files']});
 const p=await b.newPage({viewport:{width:4320,height:1350},deviceScaleFactor:1});
 await p.goto(`file://${__dirname}/pano.html`);await p.waitForSelector('body[data-ready]');await p.waitForTimeout(300);
 await p.screenshot({path:`${__dirname}/pano.png`});
 for(let i=0;i<4;i++) await p.screenshot({path:`${__dirname}/slide_${i+1}.png`,clip:{x:i*1080,y:0,width:1080,height:1350}});
 await b.close();})();
