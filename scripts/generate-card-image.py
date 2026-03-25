#!/usr/bin/env python3
"""Generate postcard card images from postcards.json using HTML template + browser screenshot."""
import json, sys, os, subprocess, tempfile, shutil

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'postcard-template.html')

TYPE_MAP = {
    'normal':     {'badge': '🦐 明信片', 'bg': 'bg-normal', 'badge_cls': 'badge-normal'},
    'surprise':   {'badge': '✨ 惊喜',   'bg': 'bg-surprise', 'badge_cls': 'badge-surprise'},
    'treasure':   {'badge': '🌟 宝藏',   'bg': 'bg-treasure', 'badge_cls': 'badge-treasure'},
    'easter':     {'badge': '🎁 彩蛋',   'bg': 'bg-easter', 'badge_cls': 'badge-easter'},
    'roundtable': {'badge': '🪑 圆桌',   'bg': 'bg-roundtable', 'badge_cls': 'badge-roundtable'},
}

def render_postcard(postcard, output_path):
    with open(TEMPLATE_PATH) as f:
        html = f.read()
    
    t = TYPE_MAP.get(postcard.get('type', 'normal'), TYPE_MAP['normal'])
    
    tags_html = ''.join(f'<span class="tag">{tag}</span>' for tag in postcard.get('tags', []))
    
    html = html.replace('{{BG_CLASS}}', t['bg'])
    html = html.replace('{{BADGE_CLASS}}', t['badge_cls'])
    html = html.replace('{{BADGE_TEXT}}', f"{t['badge']} #{postcard.get('number', '???')}")
    html = html.replace('{{SCORE}}', str(round(postcard.get('score', 0), 1)))
    html = html.replace('{{TITLE}}', postcard.get('title', ''))
    html = html.replace('{{CONTENT}}', postcard.get('content', ''))
    html = html.replace('{{TAGS}}', tags_html)
    html = html.replace('{{SOURCE}}', postcard.get('source', ''))
    
    # Write temp HTML
    tmp = tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8')
    tmp.write(html)
    tmp.close()
    
    # Screenshot with agent-browser or chromium
    try:
        # Try agent-browser first
        result = subprocess.run(
            ['agent-browser', 'snap', f'file://{tmp.name}', 
             '--width', '400', '--height', '560', 
             '--output', output_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"Generated: {output_path}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Try chromium/google-chrome headless
    for browser in ['chromium-browser', 'chromium', 'google-chrome', 'google-chrome-stable']:
        try:
            result = subprocess.run(
                [browser, '--headless', '--no-sandbox', '--disable-gpu',
                 f'--window-size=400,560', '--hide-scrollbars',
                 f'--screenshot={output_path}', f'file://{tmp.name}'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"Generated: {output_path}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    print(f"Error: No browser available for screenshot. Temp HTML at: {tmp.name}")
    return False

def main():
    postcards_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'web', 'postcards.json')
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', 'scripts', 'preview-output')
    
    os.makedirs(output_dir, exist_ok=True)
    
    with open(postcards_path) as f:
        postcards = json.load(f)
    
    for pc in postcards:
        num = pc.get('number', '000')
        output_path = os.path.join(output_dir, f'postcard-{num}.png')
        render_postcard(pc, output_path)

if __name__ == '__main__':
    main()
