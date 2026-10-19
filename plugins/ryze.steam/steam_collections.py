"""Read-only Steam collection and title-cache readers. Never change Steam files.

Binary cache layout reference: SteamDatabase/SteamAppInfo (versions 39-41).
Collections: user-collections.* records in cloudstorage, including pending edits.
App metadata alone does not establish ownership; Uncategorized is local/partial.
"""
import json
from pathlib import Path
import struct


class BinaryReader:
    def __init__(self, data, start=0, end=None, strings=None):
        self.data, self.pos = data, start
        self.end = len(data) if end is None else end
        self.strings = strings

    def take(self, size):
        if size < 0 or self.pos + size > self.end:
            raise ValueError('Truncated Steam metadata cache')
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return result

    def number(self, fmt):
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))[0]

    def string(self):
        stop = self.data.find(b'\x00', self.pos, self.end)
        if stop < 0:
            raise ValueError('Unterminated Steam metadata string')
        value = self.data[self.pos:stop].decode('utf-8', 'replace')
        self.pos = stop + 1
        return value

    def block(self, depth=0):
        if depth > 64:
            raise ValueError('Steam metadata nesting exceeds the supported limit')
        result = {}
        while self.pos < self.end:
            kind = self.number('<B')
            if kind == 8:
                return result
            if self.strings is None:
                key = self.string()
            else:
                index = self.number('<I')
                if index >= len(self.strings):
                    raise ValueError('Invalid Steam metadata string index')
                key = self.strings[index]
            if kind == 0:
                value = self.block(depth + 1)
            elif kind == 1:
                value = self.string()
            elif kind == 2:
                value = self.number('<i')
            elif kind == 3:
                value = self.number('<f')
            elif kind in (4, 6):
                value = self.number('<I')
            elif kind == 7:
                value = self.number('<Q')
            elif kind == 10:
                value = self.number('<q')
            else:
                raise ValueError('Unsupported Steam binary metadata field')
            result[key] = value
        raise ValueError('Unclosed Steam metadata object')


def app_metadata(path):
    data = path.read_bytes()
    reader = BinaryReader(data)
    magic = reader.number('<I')
    reader.number('<I')  # Universe; no credentials or PICS tokens are returned.
    if magic not in (0x07564427, 0x07564428, 0x07564429):
        raise ValueError('Unsupported Steam appinfo version')
    strings = None
    if magic == 0x07564429:
        offset = reader.number('<Q')
        if offset < reader.pos or offset > len(data) - 4:
            raise ValueError('Invalid Steam string table offset')
        table = BinaryReader(data, offset)
        count = table.number('<I')
        if count > table.end - table.pos:
            raise ValueError('Invalid Steam string table size')
        strings = [table.string() for _ in range(count)]
        reader.end = offset
    result = {}
    while reader.pos < reader.end:
        appid = reader.number('<I')
        if appid == 0:
            return result
        size = reader.number('<I')
        header_size = 60 if magic >= 0x07564428 else 40
        end = reader.pos + size
        if size < header_size or end > reader.end:
            raise ValueError('Invalid Steam metadata entry length')
        payload = BinaryReader(data, reader.pos + header_size, end, strings)
        info = payload.block().get('appinfo', {}).get('common', {})
        if isinstance(info, dict):
            name = info.get('name')
            if isinstance(name, str) and name:
                result[str(appid)] = {'name': name, 'type': str(info.get('type', '')).casefold(),
                                      'icon_hash': str(info.get('icon', ''))}
        reader.pos = end
    raise ValueError('Steam metadata footer is missing')


def profile_config(roots, read_vdf):
    """Never combine collections from different local Steam accounts."""
    for root in roots:
        profiles = [p for p in (root/'userdata').glob('*/config') if p.parent.name.isdigit()]
        if len(profiles) == 1:
            return profiles[0]
        if len(profiles) > 1:
            login = read_vdf(root/'config/loginusers.vdf').get('users', {})
            selected = [key for key, value in login.items()
                        if isinstance(value, dict) and value.get('MostRecent') == '1' and key.isdigit()]
            if len(selected) == 1:
                account = str(int(selected[0]) - 76561197960265728)
                return next((p for p in profiles if p.parent.name == account), None)
            raise ValueError('Multiple Steam profiles found; no current profile could be identified')
    return None


def collection_records(directory):
    index = directory/'cloud-storage-namespaces.json'
    namespace = 1
    if index.exists():
        namespaces = json.loads(index.read_text(encoding='utf-8'))
        if isinstance(namespaces, list) and namespaces:
            namespace = int(max(namespaces, key=lambda item: int(item[1]))[0])
    records = {}
    # Pending modified records overlay committed records, including deletions.
    for suffix in ('.json', '.modified.json'):
        path = directory/('cloud-storage-namespace-'+str(namespace)+suffix)
        if not path.exists():
            continue
        entries = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(entries, list):
            raise ValueError('Unsupported Steam collection cache format')
        for entry in entries:
            if not isinstance(entry, list) or len(entry) != 2:
                continue
            key, record = entry
            if isinstance(key, str) and key.startswith('user-collections.') and isinstance(record, dict):
                records[key] = record
    result = []
    for key, record in records.items():
        if record.get('is_deleted') or not record.get('value'):
            continue
        value = record['value']
        collection = json.loads(value) if isinstance(value, str) else value
        if not isinstance(collection, dict) or not isinstance(collection.get('name'), str) or not collection['name'].strip():
            continue
        def ids(values):
            return {str(v) for v in values if isinstance(v, (str, int)) and str(v).isdigit() and 0 < int(v) <= 0xffffffff}
        members = ids(collection.get('added', [])) - ids(collection.get('removed', []))
        result.append({'id': key, 'name': collection['name'], 'appids': sorted(members, key=int),
                       'dynamic': bool(collection.get('filterSpec'))})
    return result


def load(roots, installed, read_vdf, artwork, favorites=None):
    warnings, catalog, collections = [], {}, []
    favorites = favorites or set()
    fallback = [{**game, 'installed': True, 'type': 'game', 'icon': ''} for game in installed]
    try:
        config = profile_config(roots, read_vdf)
        if config is None:
            return {'catalog': fallback, 'collections': [], 'collections_notice': 'No Steam collection cache is available yet.'}
        collections = collection_records(config/'cloudstorage')
        local = read_vdf(config/'localconfig.vdf') if (config/'localconfig.vdf').exists() else {}
        apps = local.get('UserLocalConfigStore', {}).get('Software', {}).get('Valve', {}).get('Steam', {}).get('apps', {})
        if not isinstance(apps, dict):
            apps = {}
        known = {str(v) for v in apps if str(v).isdigit()}
        known.update(path.stem for path in (config/'librarycache').glob('*.json') if path.stem.isdigit())
        known.update(game['appid'] for game in installed)
        for collection in collections:
            known.update(collection['appids'])
        metadata = {}
        for root in roots:
            path = root/'appcache/appinfo.vdf'
            if path.exists():
                metadata.update(app_metadata(path))
        installed_map = {game['appid']: game for game in installed}
        hidden = set()
        for collection in collections:
            if collection['id'].endswith('.hidden'):
                hidden.update(collection['appids'])
        for appid in known - hidden:
            meta = metadata.get(appid)
            game = installed_map.get(appid)
            if game is None and (meta is None or meta['type'] not in ('game', 'application')):
                continue
            meta = meta or {'name': game['name'], 'type': 'game', 'icon_hash': ''}
            cached_played = apps.get(appid, {}).get('LastPlayed', '0') if isinstance(apps.get(appid), dict) else '0'
            cached_played = int(cached_played) if str(cached_played).isdigit() else 0
            entry = {**meta, 'appid': appid, 'installed': game is not None,
                     'size': game['size'] if game else 0, 'last_played': game['last_played'] if game else cached_played,
                     'favorite': appid in favorites,
                     'artwork': game['artwork'] if game else artwork(roots, appid), 'icon': ''}
            for root in roots:
                icon = root/'appcache/librarycache'/appid/(meta['icon_hash']+'.jpg')
                if meta['icon_hash'] and icon.is_file():
                    entry['icon'] = icon.resolve().as_uri()
                    break
            catalog[appid] = entry
        members = set()
        visible = []
        for collection in collections:
            if collection['id'].endswith('.hidden'):
                continue
            members.update(collection['appids'])
            collection['appids'] = [v for v in collection['appids'] if v in catalog]
            if collection['dynamic']:
                warnings.append('Dynamic collection filters are not evaluated; only saved memberships are shown.')
            visible.append(collection)
        visible.sort(key=lambda c: (0 if c['id'].endswith('.favorite') else 1, c['name'].casefold()))
        visible.append({'id': 'local:uncategorized', 'name': 'Uncategorized',
                        'appids': sorted(set(catalog) - members, key=int), 'dynamic': False})
        collections = visible
    except (OSError, ValueError, TypeError, KeyError, struct.error, RecursionError):
        warnings.append('Steam collections could not be read. Installed games remain available.')
    # Uncategorized is intentionally restricted to played/cached/collected/installed titles;
    # all appinfo entries would falsely include store pages and apps from other users.
    return {'catalog': sorted(catalog.values(), key=lambda game: game['name'].casefold()) or fallback,
            'collections': collections, 'collections_notice': '\n'.join(warnings)}
