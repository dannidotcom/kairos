import * as fontkit from 'fontkit';
import fs from 'node:fs';
let base = fontkit.openSync('C:/Users/Msi/AppData/Local/Temp/opencode/Sora-Variable.ttf');
function makePath(text,weight,size,x,baseline,letterSpacing=0){
 const font=base.getVariation({wght:weight});
 const run=font.layout(text); const scale=size/1000; let cursor=x; const ds=[];
 for(let i=0;i<run.glyphs.length;i++){
  const g=run.glyphs[i]; const pos=run.positions[i];
  const p=g.path.scale(scale,-scale).translate(cursor+(pos.xOffset||0)*scale,baseline+(pos.yOffset||0)*scale);
  ds.push(p.toSVG()); cursor += pos.xAdvance*scale + letterSpacing;
 }
 return {d:ds.join(' '), width:cursor-x-letterSpacing};
}
const data={
  word: makePath('Kairos',600,58,94,56,0),
  slogan: makePath('Le bon message, au bon moment.',400,34,0,0,0),
  english: makePath('The right message, at the right moment.',400,20,0,0,0)
};
fs.writeFileSync('scripts/wordmark.json', JSON.stringify(data,null,2));
console.log(data.word.width, data.slogan.width, data.english.width);
