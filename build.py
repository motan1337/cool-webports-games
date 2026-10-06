import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description='Extract a supported local FNaF EXE and build the browser port.')
parser.add_argument('--exe', type=Path, required=True, help='Path to your supported FiveNightsatFreddys.exe')
args = parser.parse_args()
game_path = args.exe.expanduser().resolve()
os.environ['FNAF_EXE'] = str(game_path)
from fnaf1.tools.game_input import load_game
try:
    load_game()
except (OSError, ValueError) as error:
    parser.error(str(error))
node = shutil.which('node')
if not node:
    parser.error('Node.js is required for the runtime checks. Install Node, then run this command again.')
tools = root / 'fnaf1/tools'
steps = [(sys.executable, tools / name) for name in [
    'inspect_exe.py', 'read_chunks.py', 'extract_initial.py', 'extract_images.py',
    'summarize_events.py', 'decode_game.py', 'describe_events.py', 'verify_assets.py', 'build_viewer.py']]
steps += [(node, tools / 'test_runtime.cjs'), (sys.executable, tools / 'build_pages.py')]
with (root / 'build.log').open('w', encoding='utf-8') as log:
    for executable, script in steps:
        print(f'Running {script.name}', flush=True)
        result = subprocess.run([executable, str(script)], cwd=root, capture_output=True, text=True)
        log.write(f'\n{script.name}\n{result.stdout}\n{result.stderr}\n')
        log.flush()
        if result.returncode:
            print(result.stderr[-2000:] or result.stdout[-2000:], file=sys.stderr)
            raise SystemExit(result.returncode)
print('Built fnaf1/pages/index.html and fnaf1/dist/fnaf1-pages.zip')
print('Detailed output: build.log')
