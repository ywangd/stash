from builtins import str
import os
import json

_subcmd_cfgfile = os.path.join(os.environ['STASH_ROOT'], '.completer_subcmd.json')

_subcmd_cfg = {
    "git": {
        "1": {
            'candidates': ['branch', 'checkout', 'clone', 'commit', 'help',
                           'log', 'modified', 'pull', 'push', 'remote', 'reset',
                           'rm', 'status', 'add', 'diff', 'merge', 'init', 'fetch'],
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
            'candidates': ['install', 'list', 'remove', 'download', 'search', 'update', 'versions'],
            'blank_completion': True,
            'with_normal_completion': False,
        },

    },
    "gci": {
        "1": {
            'candidates': [
            	'enable', 'disable', 'status', 'collect', 'threshold',
            	'debug', 'break',
            	],
            'blank_completion': True,
            'with_normal_completion': False,
        },
    },
    "stashconf": {
        "1": {
            'candidates': ['input_encoding_utf8', 'ipython_style_history_search', 'py_pdb', 'py_traceback'],
            'blank_completion': True,
            'with_normal_completion': False,
        },
        "-": {
            'candidate_groups': [
                [None, ['-l', '--list', '-h', '--help']],
            ],
            'blank_completion': False,
            'with_normal_completion': False,
        },
    },
    "webviewer": {
        "-": {
            'candidate_groups': [
                [None, ['-i', '--insecure', '-h', '--help']],
            ],
            'blank_completion': True,
            'with_normal_completion': False,
        },
    },
    "monkeylord": {
        "1": {
            "candidates": ["list", "enable", "disable"],
            "blank_completion": True,
            "with_normal_completion": False,
        },
        "-": {
            "candidate_groups": [
            	[None, ["-h", "--help"]],
            	],
            "blank_completion": True,
            "with_normal_completion": False,
        },
    },
    "mount": {
    	"-": {
    		"candidate_groups": [[None, [
    			"-h", "--help", "-l", "--show-labels", "-v", "--verbose",
    			"-y", "--yes", "-f", "--fake", "-r", "--read-only",
    			"-t", "--type",
    			]]],
    		"blank_completion": True,
    		"with_normal_completion": False,
    	},
    },
    "umount": {
    	"-": {
    		"candidate_groups": [[None, [
    			"-h", "--help", "-a", "--all", "-v", "--verbose",
    			"-f", "--force",
    			]]],
    		"with_normal_completion": False,
    		"blank_completion": True,
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


def subcmd_complete(toks):
    # Only one token, this is still command, not sub-command yet
    if len(toks) == 1:
        return None, None

    word_to_complete = toks[-1]
    is_blank_completion = word_to_complete == ''

    cmd_word = toks[0]
    if cmd_word.endswith('.py'):
        cmd_word = cmd_word[:-3]

    pos = str(len(toks) - 1)

    try:
        cfg = _subcmd_cfg[cmd_word]

        if pos in list(cfg.keys()) \
                and (not is_blank_completion
                     or (is_blank_completion and cfg[pos]['blank_completion'])):
            cands = _select_from_candidates(cfg[pos]['candidates'],
                                            '' if is_blank_completion else word_to_complete)
            return cands, cfg[pos]['with_normal_completion']

        elif '-' in list(cfg.keys()) \
                and ((not is_blank_completion and word_to_complete.startswith('-'))
                     or (is_blank_completion and cfg['-']['blank_completion'])):
            subcmd = None
            for t in toks[-1:0:-1]:
                if not t.startswith('-'):
                    subcmd = t
                    break
            cands = _select_from_candidate_groups(cfg['-']['candidate_groups'],
                                                  '' if is_blank_completion else word_to_complete,
                                                  subcmd)
            if cands is not None:
                return cands, cfg['-']['with_normal_completion']

    except KeyError as e:
        pass

    return None, None