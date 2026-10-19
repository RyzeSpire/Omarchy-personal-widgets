#!/usr/bin/env python3
"""Compact read-only game details. Steam install/actions require explicit clicks."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
import json
import re
import sys
import time
from urllib.error import URLError, HTTPError
from urllib.request import Request, build_opener

import steam_backend as desktop
import steam_collections
import steam_friends as account


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):self.hidden += 1
        if tag in ('br', 'p', 'li'):self.parts.append(' ')
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):self.hidden = max(0,self.hidden-1)
        if tag in ('p', 'li'):self.parts.append(' ')
    def handle_data(self, text):
        if not self.hidden:self.parts.append(text)


def text(value, limit=700):
    parser = PlainText()
    parser.feed(str(value or ''))
    return re.sub(r'\s+', ' ', ''.join(parser.parts)).strip()[:limit]


def number(value, default=None):
    return int(value) if isinstance(value, (int, str)) and str(value).isdigit() else default


def asset(roots, appid, filenames):
    for name in filenames:
        for root in roots:
            base = root/'appcache/librarycache'/appid
            matches = sorted(base.glob('*/'+name)) + sorted(base.glob(name))
            if matches:return matches[-1].resolve().as_uri()
            legacy = root/'appcache/librarycache'/(appid+'_'+name)
            if legacy.is_file():return legacy.resolve().as_uri()
    return ''


def sections(path):
    """Read complete cache records, even if Steam left an appended record suffix."""
    result = {}
    if not path.exists() or path.stat().st_size > 4*1024*1024:return result
    raw = path.read_text(encoding='utf-8', errors='replace')
    decoder, pos = json.JSONDecoder(), 0
    while pos < len(raw):
        while pos < len(raw) and (raw[pos].isspace() or raw[pos] in ',]'):pos += 1
        if pos >= len(raw):break
        try:part, pos = decoder.raw_decode(raw, pos)
        except ValueError:break
        records = [part] if isinstance(part,list) and len(part)==2 and isinstance(part[0],str) else part
        if not isinstance(records,list):continue
        for record in records:
            if isinstance(record,list) and len(record)==2 and isinstance(record[0],str) and isinstance(record[1],dict):
                result[record[0]] = record[1].get('data')
    return result


def cache_read(path, seconds):
    try:
        data=json.loads(path.read_text())
        if data.get('version')==1 and time.time()-data.get('saved_at',0)<seconds:return data.get('payload')
    except (OSError,ValueError,TypeError,AttributeError):pass
    return None


def cache_write(path, payload):
    account.atomic_json(path,{'version':1,'saved_at':int(time.time()),'payload':payload})


def image_url(value):
    if not isinstance(value,str):return ''
    # Only Steam CDN images, without credentials or query parameters.
    safe=account.avatar_url(value.split('?')[0])
    old='https://steamcdn-a.akamaihd.net/steamcommunity/public/images/apps/'
    if safe.startswith(old):safe='https://shared.fastly.steamstatic.com/community_assets/images/apps/'+safe[len(old):]
    return safe


def cached_achievements(cache):
    data = cache.get('achievements')
    if not isinstance(data,dict) or number(data.get('nTotal')) is None or number(data.get('nAchieved')) is None:
        return {'available':False,'source':'','total':None,'unlocked':None,'items':[]}
    items = {}
    for group in ('vecHighlight','vecUnachieved','vecAchievedHidden'):
        for item in data.get(group,[]):
            if not isinstance(item,dict):continue
            key=str(item.get('strID') or item.get('strName') or '')
            if key:items[key]={'id':key,'name':text(item.get('strName'),100),'description':text(item.get('strDescription'),300),
                              'unlocked':bool(item.get('bAchieved')),'icon':image_url(item.get('strImage'))}
    return {'available':True,'source':'local_cache','total':int(data['nTotal']),'unlocked':int(data['nAchieved']),
            'items':list(items.values())[:6]}


def local_info(appid):
    appid=desktop.app_id(appid)
    library=desktop.library()
    game=next((item for item in library['catalog'] if item['appid']==appid),None)
    if game is None:raise ValueError('This title is no longer in your cached library. Refresh the library.')
    roots=desktop.steam_roots()
    config=steam_collections.profile_config(roots,desktop.read_vdf)
    local,cache={},{}
    if config:
        if (config/'localconfig.vdf').exists():
            local=desktop.read_vdf(config/'localconfig.vdf').get('UserLocalConfigStore',{}).get('Software',{}).get('Valve',{}).get('Steam',{}).get('apps',{}).get(appid,{})
        cache=sections(config/'librarycache'/(appid+'.json'))
    descriptions=cache.get('descriptions') if isinstance(cache.get('descriptions'),dict) else {}
    associations=cache.get('associations') if isinstance(cache.get('associations'),dict) else {}
    collection_names=[c['name'] for c in library['collections'] if appid in c['appids'] and c['id']!='local:uncategorized']
    info={**game,'hero':asset(roots,appid,['library_hero.jpg','library_header.jpg']),
          'logo':asset(roots,appid,['logo.png']), 'description':text(descriptions.get('strSnippet')),
          'developers':[text(v.get('strName'),100) for v in associations.get('rgDevelopers',[]) if isinstance(v,dict)],
          'publishers':[text(v.get('strName'),100) for v in associations.get('rgPublishers',[]) if isinstance(v,dict)],
          'release_date':'','features':[],'platforms':[],'storage_required':'', 'collections':collection_names,
          'playtime_minutes':number(local.get('Playtime')),
          'last_played':number(local.get('LastPlayed'),game.get('last_played') or None),
          'history_source':'local_cache' if local else '', 'achievements':cached_achievements(cache),
          'friends':{'loaded':False,'entries':[],'unavailable':0,'notice':''},'notes':[]}
    try:
        profile=account.current_profile()
        snapshot=account.read_snapshot(profile['steamid'])
        for friend in (snapshot or {}).get('friends',[]):
            if friend.get('group')=='in_game' and friend.get('game','').casefold()==game['name'].casefold():
                info['friends']['entries'].append({**friend,'activity':'Playing now','playtime_minutes':None})
    except (OSError,ValueError):pass
    return info


def public_store(appid, fresh=False):
    path=account.cache_dir()/('game-public-store-'+appid+'.json')
    previous=cache_read(path,86400)
    if previous is not None and not fresh:return previous
    uri='https://store.steampowered.com/api/appdetails?appids='+appid+'&l=english'
    try:
        with build_opener(account.NoRedirect()).open(Request(uri,headers={'User-Agent':'Omarchy-Steam-Widget/1.3'}),timeout=6) as response:
            raw=response.read(4*1024*1024+1)
        if len(raw)>4*1024*1024:raise ValueError()
        value=json.loads(raw).get(appid,{})
        if not value.get('success') or not isinstance(value.get('data'),dict):raise ValueError()
        data=value['data']
        requirements=text(data.get('pc_requirements',{}).get('minimum'),2500)
        storage=re.search(r'(?:Storage|Hard (?:Disk|Drive)|Disk Space):?\s*([\d.,]+\s*(?:GB|MB|TB))',requirements,re.I)
        result={'description':text(data.get('short_description')),
                'developers':[text(v,100) for v in data.get('developers',[])],
                'publishers':[text(v,100) for v in data.get('publishers',[])],
                'release_date':text(data.get('release_date',{}).get('date'),80),
                'features':[text(v.get('description'),100) for v in data.get('categories',[]) if isinstance(v,dict)][:24],
                'platforms':[label for key,label in [('windows','Windows'),('mac','macOS'),('linux','Linux')] if data.get('platforms',{}).get(key)],
                'storage_required':storage.group(1) if storage else '',
                'header':image_url(data.get('header_image'))}
        cache_write(path,result)
        return result
    except HTTPError as error:
        error.close()
    except (OSError,URLError,ValueError,TypeError,AttributeError):pass
    return previous or {}


def current_api():
    try:
        profile=account.current_profile();config=account.read_config()
        if config and config['steamid']==profile['steamid']:return profile,config['api_key']
    except (OSError,ValueError):pass
    return None,None


def owned_game(key, steamid, appid):
    response=account.api('GetOwnedGames/v1',key,{'input_json':json.dumps({'steamid':steamid,'include_appinfo':True,'include_played_free_games':True,'appids_filter':[int(appid)]})})
    data=response.get('response',{})
    if not isinstance(data,dict) or not any(k in data for k in ('games','game_count')):return None,False
    game=next((g for g in data.get('games',[]) if isinstance(g,dict) and str(g.get('appid'))==appid),None)
    return game,True


def own_stats(appid, profile, key):
    game,visible=owned_game(key,profile['steamid'],appid)
    if game is None:return {}
    return {'playtime_minutes':number(game.get('playtime_forever')),
            'last_played':number(game.get('rtime_last_played')),'history_source':'api'}


def achievements(appid, profile, key, fresh=False):
    path=account.cache_dir()/('game-public-schema-'+appid+'.json')
    schema=cache_read(path,86400)
    if schema is None or fresh:
        raw=account.api('GetSchemaForGame/v2',key,{'appid':appid,'l':'english'})
        schema=raw.get('game',{}).get('availableGameStats',{}).get('achievements',[])
        if not isinstance(schema,list):schema=[]
        schema=[{k:item.get(k) for k in ('name','displayName','description','hidden','icon','icongray')} for item in schema if isinstance(item,dict)]
        cache_write(path,schema)
    raw=account.api('GetPlayerAchievements/v1',key,{'steamid':profile['steamid'],'appid':appid,'l':'english'})
    data=raw.get('playerstats',{})
    if not data.get('success') or not isinstance(data.get('achievements'),list):
        raise account.FriendsError('Achievement progress is unavailable for this game or profile.')
    states={v.get('apiname'):v for v in data['achievements'] if isinstance(v,dict)}
    items=[]
    for definition in schema:
        key_name=definition.get('name');state=states.get(key_name,{})
        unlocked=bool(state.get('achieved'))
        hidden=bool(definition.get('hidden')) and not unlocked
        items.append({'id':key_name,'name':'Hidden achievement' if hidden else text(definition.get('displayName') or key_name,100),
                      'description':'' if hidden else text(definition.get('description'),300),
                      'unlocked':unlocked,'icon':image_url(definition.get('icon') if unlocked else definition.get('icongray'))})
    total=len(schema) if schema else len(states)
    unlocked=sum(bool(v.get('achieved')) for v in states.values())
    items.sort(key=lambda item:(item['unlocked'],item['name'].casefold()))
    return {'available':True,'source':'api','total':total,'unlocked':unlocked,'items':items[:6]}


def info(appid, fresh=False):
    result=local_info(appid)
    profile,key=current_api()
    path=account.cache_dir()/('game-personal-info-'+profile['steamid']+'-'+appid+'.json') if profile else None
    cached=cache_read(path,600) if path else None
    if cached is not None and not fresh:
        # Favorite pins, installation and local artwork are always taken from current files.
        for field in ('playtime_minutes','last_played','history_source','achievements'):
            if field in cached and cached[field] is not None:result[field]=cached[field]
    tasks={'store':lambda:public_store(appid,fresh)}
    if profile and (cached is None or fresh):
        tasks['history']=lambda:own_stats(appid,profile,key)
        tasks['achievements']=lambda:achievements(appid,profile,key,fresh)
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending={pool.submit(fn):name for name,fn in tasks.items()}
        for future in as_completed(pending):
            name=pending[future]
            try:
                value=future.result()
                if name=='store':
                    for field in ('description','developers','publishers','release_date','features','platforms','storage_required'):
                        if value.get(field):result[field]=value[field]
                    if not result['hero']:result['hero']=value.get('header','')
                elif name=='history':
                    for field,v in value.items():
                        if v is not None:result[field]=v
                else:result['achievements']=value
            except (OSError,ValueError,TypeError,AttributeError):
                if name=='achievements' and not result['achievements']['available']:
                    result['notes'].append('Achievement progress is unavailable for this game or profile.')
    for achievement in result.get('achievements',{}).get('items',[]):
        achievement['icon']=image_url(achievement.get('icon',''))
    if path:
        cache_write(path,{k:result[k] for k in ('playtime_minutes','last_played','history_source','achievements')})
    return result


def friends_who_play(appid, fresh=False):
    base=local_info(appid);profile,key=current_api()
    if not profile:return {**base['friends'],'loaded':True,'notice':'Connect Steam Friends to check shared games.'}
    snapshot=account.read_snapshot(profile['steamid'])
    if snapshot is None:return {**base['friends'],'loaded':True,'notice':'Refresh Steam Friends, then check this game again.'}
    path=account.cache_dir()/('game-personal-friends-'+profile['steamid']+'-'+appid+'.json')
    cached=cache_read(path,600)
    if cached is not None and not fresh:return cached
    people=snapshot.get('friends',[])[:200]
    entries={person['steamid']:person for person in base['friends']['entries']}
    unavailable=0;deadline=time.monotonic()+25
    def check(friend):
        if time.monotonic()>deadline:return friend,None,False
        try:game,visible=owned_game(key,friend['steamid'],appid);return friend,game,visible
        except (OSError,ValueError):return friend,None,False
    with ThreadPoolExecutor(max_workers=4) as pool:
        for friend,game,visible in pool.map(check,people):
            if not visible:unavailable+=1;continue
            if game:
                minutes=number(game.get('playtime_forever'),0)
                last=number(game.get('rtime_last_played'),0)
                recent=number(game.get('playtime_2weeks'))
                activity='Played recently' if (recent or 0)>0 or last>time.time()-14*86400 else 'Played previously' if minutes else 'Owns this game'
                if friend['steamid'] in entries:activity='Playing now'
                entries[friend['steamid']]={**friend,'activity':activity,'playtime_minutes':minutes,'recent_minutes':recent}
    rank={'Playing now':0,'Played recently':1,'Played previously':2,'Owns this game':3}
    result={'loaded':True,'entries':sorted(entries.values(),key=lambda person:(rank[person['activity']],person['name'].casefold())),
            'unavailable':unavailable,'notice':str(unavailable)+' friends have private/unavailable game details.' if unavailable else ''}
    if len(snapshot.get('friends',[]))>200:result['notice']+=' Checked the first 200 friends.'
    cache_write(path,result)
    return result


ACTIONS={'install':'steam://install/{id}','steam':'steam://nav/games/details/{id}',
         'properties':'steam://gameproperties/{id}','store':'steam://store/{id}',
         'community':'steam://openurl/https://steamcommunity.com/app/{id}/',
         'achievements':'steam://url/SteamIDAchievementsPage/{id}'}


def action(appid, name):
    desktop.app_id(appid)
    if name not in ACTIONS:raise ValueError('Unknown game action.')
    local_info(appid)  # Only titles in the widget's known library can dispatch actions.
    uri=ACTIONS[name].format(id=appid)
    if name=='achievements':
        profile=account.current_profile()
        uri='steam://openurl/https://steamcommunity.com/profiles/'+profile['steamid']+'/stats/'+appid+'/?tab=achievements'
    result=desktop.dispatch(uri)
    result['focused']=desktop.focus_client('properties' if name=='properties' else 'library')
    return result


def main(args):
    if len(args) in (2,3) and args[0] in ('info','local','friends'):
        appid=desktop.app_id(args[1]);fresh=len(args)==3 and args[2]=='fresh'
        if args[0]=='local':return {'info':local_info(appid)}
        if args[0]=='info':return {'info':info(appid,fresh)}
        return {'friends':friends_who_play(appid,fresh)}
    if len(args)==3 and args[0]=='action':return action(desktop.app_id(args[1]),args[2])
    raise ValueError('Unknown game details command.')


if __name__=='__main__':
    request_tag=None
    try:
        arguments=sys.argv[1:]
        if len(arguments)>=2 and arguments[-2]=='--request-tag':
            if not arguments[-1].isdigit():raise ValueError('Invalid request identifier.')
            request_tag=int(arguments[-1]);arguments=arguments[:-2]
        print(json.dumps({'ok':True,'request_tag':request_tag,**main(arguments)},ensure_ascii=False))
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        error=sys.exc_info()[1]
        message=str(error) if type(error) is ValueError or isinstance(error,account.FriendsError) else 'This game’s information could not be loaded.'
        print(json.dumps({'ok':False,'request_tag':request_tag,'error':message},ensure_ascii=False));sys.exit(1)
