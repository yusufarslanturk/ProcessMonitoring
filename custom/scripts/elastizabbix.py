#!/usr/bin/python3

import os
import sys
import json
import urllib.request
import time
import errno

# Check parameter count
if len(sys.argv) < 4:
    sys.exit('This script needs at least 3 parameters: ip, api, stat.')

ttl = 60
ip = sys.argv[1]

cluster_url = 'http://%s:9200/_cluster/stats' %ip
nodes_url = 'http://%s:9200/_nodes/stats' %ip
indicies_url = 'http://%s:9200/_stats' %ip
health_url = 'http://%s:9200/_cluster/health' %ip

stats = {
    'cluster': cluster_url,
    'nodes'  : nodes_url,
    'indices': indicies_url,
    'health' : health_url
}

def created_file(name):
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        os.close(fd)
        return True
    except OSError as e:
        if e.errno == errno.EEXIST:
            return False
        raise

def is_older_then(name, ttl):
    age = time.time() - os.path.getmtime(name)
    return age > ttl

def get_cache(api):
    cache = '/tmp/elastizabbix-{0}.json'.format(api)
    lock = '/tmp/elastizabbix-{0}.lock'.format(api)
    should_update = (not os.path.exists(cache)) or is_older_then(cache, ttl)
    if should_update and created_file(lock):
        try:
            d = urllib.request.urlopen(stats[api]).read()
            with open(cache, 'w') as f:
                f.write(d)
        except Exception as e:
            pass
        if os.path.exists(lock):
            os.remove(lock)
    if  os.path.exists(lock) and is_older_then(lock, 300):
        os.remove(lock)
    ret_data = {}
    try:
        with open(cache)  as data_file:
            ret_data = json.load(data_file)
    except Exception as e:
        ret_data = json.loads(urllib.request.urlopen(stats[api]).read())
    return ret_data

def get_stat(api, stat):
    d = get_cache(api)
    keys = []
    for i in stat.split('.'):
        keys.append(i)
        key = '.'.join(keys)
        if key in d:
            d = d.get(key)
            keys = []
    return d

def discover_nodes():
    d = {'data': []}
    for k,v in get_stat('nodes', 'nodes').items():
        d['data'].append({'{#NAME}': v['name'], '{#NODE}': k})
    return json.dumps(d)

def discover_indices():
    d = {'data': []}
    for k,v in get_stat('indices', 'indices').items():
        d['data'].append({'{#NAME}': k})
    return json.dumps(d)


if __name__ == '__main__':
    api = sys.argv[2]
    stat = sys.argv[3]
    if api == 'discover':
        if stat == 'nodes':
            print(discover_nodes())
        if stat == 'indices':
            print(discover_indices())

    else:
        stat = get_stat(api, stat)
        if isinstance(stat, dict):
            print('')
        else:
            print(stat)
