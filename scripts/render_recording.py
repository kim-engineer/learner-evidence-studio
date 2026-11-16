"""Render the recorded terminal timeline at its original speed. Needs Pillow and ffmpeg."""
import json
import math
from pathlib import Path
import shutil
import subprocess
import textwrap
from PIL import Image, ImageDraw, ImageFont


def main():
    folder=Path("evaluation/demo")
    entries=[json.loads(line) for line in (folder/"agent-run.cast").read_text().splitlines()]
    header, events=entries[0],entries[1:]
    duration=float(json.loads((folder/"recording-info.json").read_text())["duration_seconds"])
    font_path=next((p for p in [Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
                              Path("C:/Windows/Fonts/consola.ttf")] if p.exists()),None)
    if font_path is None or not shutil.which("ffmpeg"):
        raise SystemExit("Install a monospace font (DejaVu Sans Mono or Consolas) and ffmpeg.")
    font=ImageFont.truetype(str(font_path),16)
    bold=ImageFont.truetype(str(font_path),19)
    width,height,fps=1280,960,5
    process=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24",
        "-s",f"{width}x{height}","-r",str(fps),"-i","-","-an","-c:v","libx264","-preset","veryfast",
        "-crf","19","-pix_fmt","yuv420p","-movflags","+faststart",str(folder/"agent-demo.mp4")],stdin=subprocess.PIPE)
    lines=[]; index=0
    try:
        for frame in range(math.ceil(duration*fps)+1):
            at=frame/fps
            while index<len(events) and events[index][0]<=at:
                for line in events[index][2].replace("\r","").splitlines():
                    lines.extend(textwrap.wrap(line,width=116,replace_whitespace=False,drop_whitespace=False) or [""])
                index+=1
            image=Image.new("RGB",(width,height),"#10282e")
            draw=ImageDraw.Draw(image)
            draw.rectangle((0,0,width,64),fill="#193b42")
            draw.text((32,21),"LEARNER EVIDENCE STUDIO",font=bold,fill="#f2f8f7")
            draw.text((740,23),f"REAL LOCAL RUN  |  {at:05.1f}s / {duration:04.1f}s",font=font,fill="#91d9ce")
            for row,line in enumerate(lines[-36:]):
                color="#dbe8e8"
                if "PLAN ->" in line or "CALL " in line: color="#83d8e7"
                if "CHECK" in line or line.startswith("PAUSED") or "KNOWN LIMITATION" in line: color="#ffb087"
                if "WRITE" in line or line.startswith("COMPLETE"): color="#91e2bb"
                draw.text((32,86+row*22),line,font=font,fill=color)
            draw.line((32,914,width-32,914),fill="#37565d")
            draw.text((32,927),"Synthetic records | Continuous terminal capture | Original timing | Full JSON trace included",font=font,fill="#98afb2")
            process.stdin.write(image.tobytes())
            if frame==math.ceil(duration*fps)-1:
                image.save(folder/"terminal-final-frame.png")
    finally:
        process.stdin.close()
    if process.wait()!=0:
        raise SystemExit("Video rendering failed")
    print(folder/"agent-demo.mp4")


if __name__=="__main__":
    main()
