#!/usr/bin/env python3
"""Select an allowed cached Proton server before invoking the official CLI."""
import argparse
import math
import random
import re
import subprocess
import sys
from servers import read_cache, status_known

FEATURES = {'--securecore': 1, '--tor': 2, '--p2p': 4}


def select_server(data, args, blocked):
    if not data or type(data.get('MaxTier')) is not int or not status_known(data):
        raise ValueError('No current eligible-server cache. Refresh Proton first; no unrestricted connection was attempted.')
    country = city = name = None
    feature = 0
    randomize = False
    i = 0
    while i < len(args):
        value = args[i]
        if value in ('--country', '--city'):
            i += 1
            if i >= len(args): raise ValueError('Missing location value')
            if value == '--country':
                country = args[i].upper()
                if not re.fullmatch('[A-Z]{2}', country): raise ValueError('Use a two-letter country code')
            else: city = args[i].casefold()
        elif value in FEATURES: feature |= FEATURES[value]
        elif value == '--random': randomize = True
        elif re.fullmatch('[A-Za-z0-9][A-Za-z0-9#-]{0,80}', value):
            if name is not None: raise ValueError('Only one server may be selected')
            name = value.upper()
        else: raise ValueError('Unsupported connection option')
        i += 1
    if country in blocked:
        raise ValueError('This country is blocked in the widget: ' + country)
    candidates = []
    for server in data.get('LogicalServers') or []:
        exit_code = str(server.get('ExitCountry') or '').upper()
        entry_code = str(server.get('EntryCountry') or '').upper()
        tier = server.get('Tier')
        server_name = str(server.get('Name') or '')
        if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9#-]{0,80}', server_name): continue
        if not re.fullmatch('[A-Z]{2}', exit_code): continue
        if exit_code in blocked or entry_code in blocked: continue
        if server.get('Status') != 1 or type(tier) is not int or tier > data['MaxTier']: continue
        if name is not None:
            if server_name.upper() != name: continue
        else:
            if country and exit_code != country: continue
            if city and str(server.get('City') or '').casefold() != city: continue
            bits = server.get('Features') or 0
            if bits & feature != feature: continue
            if not feature & 1 and bits & 1: continue
        candidates.append(server)
    if not candidates:
        raise ValueError('No allowed server matches this selection. Brazil/blocked routes will not be used; no fallback was attempted.')
    def score(server):
        value = server.get('Score')
        return value if isinstance(value, (int, float)) and math.isfinite(value) else float('inf')
    chosen = random.choice(candidates) if randomize and name is None else min(candidates, key=score)
    return chosen['Name']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blocked', default='BR')
    parser.add_argument('options', nargs=argparse.REMAINDER)
    ns = parser.parse_args()
    blocked = {code.strip().upper() for code in ns.blocked.split(',') if code.strip()}
    if any(not re.fullmatch('[A-Z]{2}', code) for code in blocked): parser.error('Invalid blocked country code')
    args = ns.options[1:] if ns.options[:1] == ['--'] else ns.options
    try: name = select_server(read_cache(), args, blocked)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    return subprocess.run(['protonvpn', 'connect', name], check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
