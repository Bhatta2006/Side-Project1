import { execFileSync } from 'node:child_process';
import path from 'node:path';

// Authored answer text, loaded once; the app still shuffles and grades every answer.
const python = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
export const outputCheckAnswers: Record<string, string> = JSON.parse(execFileSync(python, ['-c', `
import json, pathlib, yaml
concept = yaml.safe_load(pathlib.Path('content/courses/zero/concepts/programs-and-output.yaml').read_text(encoding='utf-8'))
answers = {'zero:programs-and-output:' + q['id']: q['options'][q['answer']] for q in concept['quiz']}
for path in pathlib.Path('content/quiz/zero/programs-and-output').glob('*.yaml'):
    family = yaml.safe_load(path.read_text(encoding='utf-8'))
    answers.update({family['id'] + ':' + q['id']: q['options'][q['answer']] for q in family.get('items', [])})
print(json.dumps(answers))
`], { encoding: 'utf8' }));
