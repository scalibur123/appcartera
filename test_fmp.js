const https = require('https');
const apikey = 't40MuetxNEIqW5RSQHWytS94r7JUH7HT';

const tickers = ['AMD','DDOG','LWLG','GFS','CVX','IRDM','RIOT','BTDR','SNOW','GIII','EDIT','ABUS','SFM','BCRX','PGEN','RGTI','LBTYA','AMRC','CZR','ZS','ACHC','MSTR','TMUS','VOYG','A','JOBY','UBER','GLXY','MSFT','MDT','ADT','CALM','COIN','AOSL','OKTA','SAH','BLCO','MOH','Z','CRNC','HNST','MAS','CRBP','OC','ABEO','RGEN','GNTX','ISRG','XERS','KVUE','SNDL','PCRX','MARA','JKHY','VREX','HRMY','FTV','WEAV','OGN','SWIM','GEHC','KKC','COO','DHR','BSY','INTU','MRNA','GT','S','POOL','PGY','WDAY','SDGR','KLAR','DOCU','BAX','CNDT','RARE','CERT','NEOV','IOVA','ASAN','FUBO','PRZO','AI','DJT','CHPT','BHVN','SPT'];

function fetch1(sym) {
  return new Promise((resolve) => {
    const url = `https://financialmodelingprep.com/stable/price-target-consensus?symbol=${sym}&apikey=${apikey}`;
    const req = https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' }, timeout: 8000 }, (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        try {
          const r = JSON.parse(d);
          const item = Array.isArray(r) ? r[0] : r;
          if (item && item.targetConsensus && item.targetConsensus > 0) {
            resolve({ sym, ok: true, target: item.targetConsensus, analysts: item.numberOfAnalysts || 0 });
          } else {
            resolve({ sym, ok: false });
          }
        } catch { resolve({ sym, ok: false }); }
      });
    });
    req.on('error', () => resolve({ sym, ok: false }));
    req.on('timeout', () => { req.destroy(); resolve({ sym, ok: false }); });
  });
}

(async () => {
  const ok = [], nok = [];
  for (const sym of tickers) {
    await new Promise(r => setTimeout(r, 250));
    const res = await fetch1(sym);
    if (res.ok) {
      ok.push(`${sym}: ${res.target} (${res.analysts} analistas)`);
    } else {
      nok.push(sym);
    }
    process.stdout.write('.');
  }
  console.log('\n\n✅ CON DATOS (' + ok.length + '):');
  ok.forEach(x => console.log(' ', x));
  console.log('\n❌ SIN DATOS (' + nok.length + '):');
  console.log(' ', nok.join(', '));
})();
