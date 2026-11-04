"""Export tracked team source without repository internals or local player data."""
from pathlib import Path,PurePosixPath
import argparse,json,subprocess,tomllib,zipfile

ROOT=Path(__file__).resolve().parents[1]

def source_files(root):
 root=Path(root).resolve()
 try:
  top=subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=root,stderr=subprocess.DEVNULL,text=True).strip()
  if Path(top).resolve()!=root:raise ValueError('Not this project repository')
  names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
 except (subprocess.CalledProcessError,FileNotFoundError,ValueError):
  names=json.loads((root/'release-files.json').read_text())
 for name in filter(None,names):
  p=PurePosixPath(name)
  if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe release path')
  if any(part in ('.git','.venv','data','dist','__pycache__','.pytest_cache') for part in p.parts):continue
  if p.name.startswith('.env') or p.name=='secrets.toml' or p.suffix in ('.db','.sqlite','.sqlite3','.bundle','.log'):continue
  path=root/name
  if not path.is_file():continue
  if not path.resolve().is_relative_to(root):raise ValueError('Release file points outside project')
  yield name

def package(root,output):
 root=Path(root).resolve();output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
  for name in sorted(source_files(root)):
   if (root/name).resolve()==output:continue
   archive.write(root/name,'Team-Plot-Twist/'+name)
 return output

if __name__=='__main__':
 version=tomllib.loads((ROOT/'pyproject.toml').read_text())['project']['version']
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'dist'/f'Team-Plot-Twist-{version}.zip')
 args=parser.parse_args();print(package(ROOT,args.output))
