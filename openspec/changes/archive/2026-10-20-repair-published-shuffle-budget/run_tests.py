"""Run unmodified suites; explicitly report Windows symlink privilege skips."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))


class PlatformResult(unittest.TextTestResult):
    def addError(self,test,err):
        # This is missing OS privilege, never a skip for assertions/code errors.
        if os.name=='nt' and isinstance(err[1],OSError) and getattr(err[1],'winerror',None)==1314:
            self.addSkip(test,'Windows cannot create symlinks (WinError 1314); alias coverage unavailable')
        else:
            super().addError(test,err)


parser=argparse.ArgumentParser()
parser.add_argument('suite',choices=['skeleton','baseline'])
parser.add_argument('--label',required=True)
args=parser.parse_args()
evidence=Path(__file__).parent/'evidence'
evidence.mkdir(exist_ok=True)
package='graph_value_skeleton' if args.suite=='skeleton' else 'nograph_baseline'
started=time.monotonic()
with (evidence/(args.label+'.log')).open('x',encoding='utf-8') as stream:
    start=ROOT/'benchmark'/package/'tests'
    suite=unittest.defaultTestLoader.discover(str(start),
            top_level_dir=str(ROOT) if (start/'__init__.py').exists() else str(start))
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=PlatformResult).run(suite)
summary={'command':[sys.executable,*sys.argv], 'cwd':str(ROOT),'python':sys.version,
         'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
         'skips':[(test.id(),reason) for test,reason in result.skipped],
         'elapsed_seconds':time.monotonic()-started,'success':result.wasSuccessful()}
with (evidence/(args.label+'.json')).open('x',encoding='utf-8') as handle:
    json.dump(summary,handle,indent=2,ensure_ascii=False)
print(json.dumps(summary,ensure_ascii=False))
sys.exit(0 if result.wasSuccessful() else 1)
