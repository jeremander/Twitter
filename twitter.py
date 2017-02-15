import json
import networkx as nx
from collections import defaultdict
from functools import reduce

data = json.load(open('tweets.json', 'r'))
num_users = len(data)
tags_by_user = [user['tags'] for user in data] 
tag_counts = defaultdict(int)
for tags in tags_by_user:
    for tag in tags:
        tag_counts[tag] += 1

user_ids = set(map(int, [user['id'] for user in data]))
orig_ids = list(sorted(user_ids))
relabel = {user_id : i for (i, user_id) in enumerate(orig_ids)}
edges = []
for user in data:
    source = relabel[int(user['id'])]
    for friend_id in map(int, user['friends']):
        if (friend_id in user_ids):
            target = relabel[friend_id]
            edges.append((source, target))

dg = nx.DiGraph(edges)
comps = list(nx.connected_components(dg.to_undirected()))
complens = [len(comp) for comp in comps]