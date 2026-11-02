"""Build narration files and an explicitly provisional editorial timeline."""
import json, re, csv, textwrap, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FPS, WPM = 30, 147
def words(t):
    return re.findall(r"\b[\w’'-]+\b", t)
def tc(seconds):
    ms=round(seconds*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'
def chunks(t, limit=19):
    result=[]; current=[]
    for sentence in re.split(r'(?<=[.!?])\s+', t):
        if current and len(words(' '.join(current + [sentence]))) > limit:
            result.append(' '.join(current)); current=[]
        if len(words(sentence)) > 25:
            if current: result.append(' '.join(current)); current=[]
            tokens=sentence.split()
            for i in range(0,len(tokens),limit): result.append(' '.join(tokens[i:i+limit]))
        else: current.append(sentence)
    if current: result.append(' '.join(current))
    return result

def main():
    data=json.loads((ROOT/'episode.json').read_text())
    prompts=json.loads((ROOT/'scene_prompts.json').read_text())
    sources=json.loads((ROOT/'sources.json').read_text())
    (ROOT/'voiceover').mkdir(exist_ok=True)
    (ROOT/'fonts').mkdir(exist_ok=True)
    previous=ROOT.parent/'sleep_episode/github_package/Project/fonts'
    if previous.exists():
        for p in previous.iterdir():
            if p.is_file(): shutil.copy2(p,ROOT/'fonts'/p.name)
    shots=[]; overlays=[]; subtitle=[]; frame=0; segment_index=0; total_words=0
    full=[]; annotated=[f'# {data["title"]}\n', 'English narration. All timestamps are provisional until new voice recordings are supplied.\n']
    for block in data['blocks']:
        voice='\n\n'.join(s['voice'] for s in block['segments'])+'\n'
        count=len(words(voice));total_words+=count
        block['word_count']=count
        (ROOT/'voiceover'/f'{block["file"]}.txt').write_text(voice)
        full.append(voice)
        block['estimated_start_seconds']=round(frame/FPS,3)
        annotated.append(f'## {block["id"]:02d} · {block["title"]}\n\n{voice}')
        related=[s for s in sources if block['id'] in s['blocks']]
        if related: annotated.append('Sources: '+ '; '.join(f'[{s["id"]}: {s["title"]}]({s["url"]})' for s in related)+'\n')
        for seg_index,segment in enumerate(block['segments'],1):
            segment_index+=1
            original_id=segment['asset'];asset=prompts['aliases'].get(original_id,original_id)
            start=frame
            pieces=chunks(segment['voice'])
            if block['id']==1 and seg_index==1:
                pieces=['One bad step.','A crack.','Your leg will not hold you.']
            label='ILLUSTRATIVE SCENARIO' if block['id'] in [1,2,4,8] else ''
            if asset in ['09','10','19','23']: label='SCHEMATIC'
            if asset=='11':label='MODERN COMPARISON · NHS'
            if block['id']==5:label='SHANIDAR 1 · ILLUSTRATIVE RECONSTRUCTION'
            if block['id']==6:label='LIANG TEBO · RESEARCH INTERPRETATION'
            if block['id']==7:label='PUBLISHED DEBATE · 2023'
            for piece_index,piece in enumerate(pieces):
                n=len(words(piece));dur=max(.85,n/WPM*60+.13)
                frames=max(1,round(dur*FPS))
                use_asset=asset
                z=1.0 if piece_index%2==0 else 1.13;cx=cy=.5;move=.025 if piece_index%2==0 else 0
                if asset in ['09','10','11','18','19','23','24','25']:
                    z=1;move=0
                if block['id']==1:
                    if seg_index==1:
                        if piece_index==0:z=1;move=.035
                        elif piece_index==1:z=1.65;cx=.57;cy=.66;move=0
                        else:use_asset='02';z=1.45;cx=.31;cy=.39;move=.02
                    elif seg_index in [2,3,6]:
                        z=1.25 if piece_index%2==0 else 1.52;cx=.30;cy=.42
                    elif seg_index==5:
                        z=1;cx=.5;cy=.5;move=0
                shot={'shot':len(shots)+1,'block':block['id'],'segment':seg_index,'asset':use_asset,
                      'source_asset_role':original_id,'voiceover':piece,'start_frame':frame,'frames':frames,
                      'start':frame/FPS,'end':(frame+frames)/FPS,'zoom':z,'cx':cx,'cy':cy,'move':move,
                      'label':label,'timing_status':'estimated_not_audio_aligned'}
                shots.append(shot);subtitle.append((frame/FPS,(frame+frames)/FPS,piece));frame+=frames
            if segment['text']:
                length=min((frame-start)/FPS, max(2.5,min(5.5,len(words(segment['text']))*.55+.7)))
                overlays.append({'segment':segment_index,'block':block['id'],'start':start/FPS,'end':start/FPS+length,
                    'text':segment['text'],'style':'title','timing_status':'estimated'})
        block['estimated_end_seconds']=round(frame/FPS,3)
    data['word_count']=total_words
    data['estimated_duration_seconds']=frame/FPS
    data['estimated_wpm']=WPM
    data['audio_received']=False
    data['final_video_rendered']=False
    data['unique_artwork_count']=24
    (ROOT/'episode.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'Voiceover_Full_EN.txt').write_text('\n'.join(full))
    (ROOT/'Script_EN_with_sources.md').write_text('\n'.join(annotated))
    (ROOT/'timeline_DRAFT.json').write_text(json.dumps(shots,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'text_overlays_DRAFT.json').write_text(json.dumps(overlays,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'Subtitles_DRAFT_EN.srt').write_text('\n\n'.join(f'{i}\n{tc(a)} --> {tc(b)}\n'+textwrap.fill(s,60) for i,(a,b,s) in enumerate(subtitle,1))+'\n')
    with (ROOT/'timeline_DRAFT.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(shots[0]));writer.writeheader();writer.writerows(shots)
    catalogue=[]
    for i in range(1,33):
        role=f'{i:02d}';aid=prompts['aliases'].get(role,role)
        catalogue.append({'role':role,'asset':aid,'path':f'assets/{aid}.png','reused':role!=aid})
    (ROOT/'asset_catalogue.json').write_text(json.dumps(catalogue,indent=2)+'\n')
    print(json.dumps({'words':total_words,'shots':len(shots),'text_overlays':len(overlays),'estimated_seconds':frame/FPS}))

if __name__=='__main__':main()
