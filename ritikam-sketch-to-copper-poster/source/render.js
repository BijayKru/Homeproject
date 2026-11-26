const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch({args:['--allow-file-access-from-files']});
 const p=await b.newPage({viewport:{width:1080,height:1350},deviceScaleFactor:1});
 p.on('pageerror',e=>console.log('ERR',e.message));
 await p.goto(`file://${__dirname}/poster.html`);await p.waitForSelector('body[data-ready]');await p.waitForTimeout(300);
 await p.screenshot({path:`${__dirname}/poster.png`});await b.close();})();
