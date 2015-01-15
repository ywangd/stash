import os
import json

_subcmd_cfgfile = os.path.join(os.environ['STASH_ROOT'], '.completer_subcmd.json')

_subcmd_cfg = {
    "git": {
        "1": {
            'candidates': ['branch', 'checkout', 'clone', 'commit', 'help',
                           'log', 'modified', 'pull', 'push', 'remote', 'reset',
                           'rm', 'status'],
            'blank_completion': True,
            'with_normal_completion': False,
        },
        '-': {
            'blank_completion': False,
            'with_normal_completion': False,
            'candidate_groups': [
                ['log', ['-l', '--length', '-f', '--format', '-o', '--output']]
            ],
        }
    },

    "ls": {
        '-': {
            'blank_completion': False,
            'with_normal_completion': False,
            'candidate_groups': [
                [None, ['-1', '--one-line', '-a', '--all', '-l', '--long']],
            ]
        }
    },

    "pip": {
        "1": {
            'candidates': ['install', 'list', 'remove', 'search', 'update', 'versions'],
            'blank_completion': True,
            'with_normal_completion': False,
        },

    },


}

if os.path.exists(_subcmd_cfgfile) and os.path.isfile(_subcmd_cfgfile):
    try:
        with open(_subcmd_cfgfile) as ins:
            _subcmd_cfg.update(json.loads(ins.read()))
    except IOError:
        pass

def _select_from_candidates(candidates, tok):
    return [cand for cand in candidates if cand.startswith(tok)]

def _select_from_candidate_groups(candidate_groups, tok, after=None):
    for cg in candidate_groups:
        if cg[0] == after:
            return _select_from_candidates(cg[1], tok)
    return None


def subcmd_complete(toks, has_trailing_white):
    if len(toks) == 1 and not has_trailing_white:
        return None, None

    cmd_word = toks[0]
    if cmd_word.endswith('.py'):
        cmd_word = cmd_word[:-3]

    if has_trailing_white:
        pos = str(len(toks))
    else:
        pos = str(len(toks) - 1)

    try:
        cfg = _subcmd_cfg[cmd_word]

        if has_trailing_white:
            if pos in cfg.keys() and cfg[pos]['blank_completion']:
                return cfg[pos]['candidates'], cfg[pos]['with_normal_completion']

            elif '-' in cfg.keys() and cfg['-']['blank_completion']:
                subcmd = None
                for t in toks[-2:0:-1]:
                    if not t.startswith('-'):
                        subcmd = t
                        break
                if subcmd is not None:
                    cands = _select_from_candidate_groups(cfg['-']['candidate_groups'], toks[-1], subcmd)
                    if cands is not None:
                        return cands, cfg['-']['with_normal_completion']

        else:
            if pos in cfg.keys():
                cands = _select_from_candidates( cfg[pos]['candidates'], toks[-1])
                return cands, cfg[pos]['with_normal_completion']

            elif toks[-1].startswith('-') and cfg.has_key('-'):
                subcmd = None
                for t in toks[-2:0:-1]:
                    if not t.startswith('-'):
                        subcmd = t
                        break
                if subcmd is not None:
                    cands = _select_from_candidate_groups(cfg['-']['candidate_groups'], toks[-1], subcmd)
                    if cands is not None:
                        return cands, cfg['-']['with_normal_completion']

    except KeyError as e:
        #print repr(e), e
        pass

    return None, None