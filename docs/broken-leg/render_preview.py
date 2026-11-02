"""Render the opening visual draft; does not synthesize or invent a narrator."""
import json, math, random, re, subprocess, textwrap, wave, struct, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parent
BUILD=ROOT/'build_preview'
FPS=30

def run(cmd):
    p=subprocess.run([str(x) for x in cmd],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if p.returncode: raise RuntimeError(p.stderr[-6000:])
    return p.stdout

def at(t):
    cs=round(t*100)
    return f'{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}'

def escaped(t):
    return t.replace('\\','/').replace('{','(').replace('}',')')

def make_ass(shots,overlays,duration):
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,43,&H00FFFFFF,&H00FFFFFF,&H95000000,&H95000000,0,0,0,0,100,100,0,0,3,3,0,2,100,100,62,1
Style: Heading,Patrick Hand,90,&H003DEBFF,&H003DEBFF,&H00120E0B,&H00120E0B,0,0,0,0,100,100,1,0,1,5,1,8,90,90,92,1
Style: Label,DejaVu Sans,23,&H00FFFFFF,&H00FFFFFF,&H80000000,&H80000000,0,0,0,0,100,100,0,0,3,3,0,1,65,65,212,1
Style: Draft,DejaVu Sans,22,&H00E9E9E9,&H00E9E9E9,&H80000000,&H80000000,0,0,0,0,100,100,0,0,3,2,0,9,45,45,24,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events=[]
    def event(a,b,style,text,layer=1):
        if b>a:events.append(f'Dialogue: {layer},{at(a)},{at(b)},{style},,0,0,0,,{text}')
    event(0,duration,'Draft','VISUAL DRAFT  /  NARRATION PENDING',4)
    for shot in shots:
        lines=textwrap.wrap(escaped(shot['voiceover']),width=63)
        assert len(lines)<=3,shot
        event(shot['start'],shot['end'],'Caption',r'\N'.join(lines),3)
        if shot['label']:event(shot['start'],shot['end'],'Label',escaped(shot['label']))
    for item in overlays:
        if item['start']>=duration: continue
        text=escaped(item['text'])
        special=r'{\an9\pos(1830,110)\fs78}' if item['block']==1 and item['segment'] in [2,3] else r'{\fad(80,100)}'
        wrapped=r'\N'.join(textwrap.wrap(text,width=29))
        event(item['start'],min(duration,item['end']),'Heading',special+wrapped,2)
    (BUILD/'opening.ass').write_text(header+'\n'.join(events)+'\n')

def clip(shot):
    image=ROOT/'assets'/f'{shot["asset"]}.png'
    assert image.exists(),image
    dest=BUILD/f'{shot["shot"]:03d}.mp4'
    frames=shot['frames']; z=shot['zoom'];move=shot['move'];cx=shot['cx'];cy=shot['cy']
    filt=(f"scale=2560:1440:flags=lanczos,zoompan=z='{z}+{move}*on/{max(1,frames-1)}':"
          f"x='max(0,min(iw-iw/zoom,iw*{cx}-iw/zoom/2))':"
          f"y='max(0,min(ih-ih/zoom,ih*{cy}-ih/zoom/2))':d={frames}:s=1920x1080:fps={FPS},"
          'setsar=1,format=yuv420p')
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',image,'-vf',filt,
         '-frames:v',frames,'-an','-c:v','libx264','-preset','fast','-crf','19',
         '-threads','2','-filter_threads','1',dest])
    return dest

def sound(duration):
    # Original procedural ambience and two soft accents. No voice and no music.
    rate=48000;rng=random.Random(2026);smooth=0.;pcm=bytearray()
    for i in range(math.ceil(duration*rate)):
        t=i/rate;n=rng.uniform(-1,1);smooth=.985*smooth+.015*n
        v=smooth*.025
        q=t-1.37
        if 0<=q<.10:v+=n*.34*math.exp(-q*48)
        q=t-2.35
        if 0<=q<.30:v+=math.sin(q*math.tau*72)*.09*math.exp(-q*17)
        fade=min(1,t/.2,max(0,(duration-t)/.5))
        sample=round(max(-.8,min(.8,v*fade))*32767)
        pcm+=struct.pack('<hh',sample,sample)
    out=BUILD/'preview_fx.wav'
    with wave.open(str(out),'wb') as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(rate);f.writeframes(pcm)
    return out

def main():
    BUILD.mkdir(exist_ok=True)
    rows=json.loads((ROOT/'timeline_DRAFT.json').read_text())
    shots=[s for s in rows if s['block']==1]
    overlays=json.loads((ROOT/'text_overlays_DRAFT.json').read_text())
    duration=shots[-1]['end']
    make_ass(shots,overlays,duration)
    with ThreadPoolExecutor(max_workers=3) as pool:
        clips=list(pool.map(clip,shots))
    (BUILD/'concat.txt').write_text(''.join(f"file '{p.name}'\n" for p in clips))
    visual=BUILD/'visual.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0',
         '-i',BUILD/'concat.txt','-c','copy',visual])
    audio=sound(duration)
    dest=ROOT/'Opening_Preview_NO_VOICE.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',visual,'-i',audio,
         '-vf',f"ass=filename='{BUILD/'opening.ass'}':fontsdir='{ROOT/'fonts'}'",
         '-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','19',
         '-threads','4','-filter_threads','1','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',
         '-t',duration,'-movflags','+faststart','-metadata','title=Ancient Bergman - Opening visual draft (no narration)',dest])
    probe=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',dest]))
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (video['width'],video['height'])==(1920,1080)
    assert abs(float(probe['format']['duration'])-duration)<.08
    run(['ffmpeg','-v','error','-i',dest,'-f','null','-'])
    report={'file':dest.name,'kind':'opening_visual_draft','narration_present':False,
            'duration_seconds':float(probe['format']['duration']),'width':1920,'height':1080,
            'fps':video['r_frame_rate'],'shots':len(shots),'full_decode':'passed',
            'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    (ROOT/'preview_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__':main()
