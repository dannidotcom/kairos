import * as fontkit from 'fontkit';
let font = fontkit.openSync('C:/Users/Msi/AppData/Local/Temp/opencode/Sora-Variable.ttf');
font = font.getVariation({wght:600});
const text='Kairos'; const run=font.layout(text); const size=58; const scale=size/1000;
let x=96; const y=56; const ds=[];
for(let i=0;i<run.glyphs.length;i++){
 const g=run.glyphs[i]; const adv=run.positions[i].xAdvance;
 const p=g.path.scale(scale,-scale).translate(x,y);
 ds.push(p.toSVG());
 x += adv*scale;
}
console.log('width', x-96, 'end', x);
console.log(ds.join(' '));
const slogan='Le bon message, au bon moment.';
const r2=font.layout(slogan); let x2=0; const sds=[];
for(let i=0;i<r2.glyphs.length;i++){const g=r2.glyphs[i], adv=r2.positions[i].xAdvance; sds.push(g.path.scale(0.5/1000,-0.5/1000).translate(x2,0).toSVG()); x2+=adv*0.5/1000;}
console.log('slogan width',x2);
