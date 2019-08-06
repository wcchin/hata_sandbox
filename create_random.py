# -*- encoding: utf-8 -*-

import os
import networkx as nx
from tqdm import tqdm
import pathos
import json


EGO_NETWORK_OUT = 'ego_O_'
EGO_NETWORK_IN = 'ego_I_'
GRAPH_KEY_COMMON_NODES_LIST = 'list_'
GRAPH_KEY_AVG_COMMON_NODES = 'avg'
GRAPH_KEY_STD_COMMON_NODES = 'std'
SUCCESSORS = 'suc'
PREDECESSORS = 'pre'


def read_a_file(fp):
    print('reading file')
    lines = []
    with open(fp, 'r') as fread:
        for line in fread.readlines():
            if line[0]=='%':
                continue
            line = line.split(' ')[:2]
            lines.append(line)
    #print len(lines)
    return make_graph(lines)


def make_graph(lines):
    print('making DiGraph')
    dg = nx.DiGraph()
    dg.add_edges_from(lines)
    dgs = sorted(nx.weakly_connected_component_subgraphs(dg, copy=False), key=len, reverse=True)
    return dgs[0]


def average_shortest_path_length(g):
    nlist = list(node for node in g.nodes())
    total = 0
    count = 0
    for index in tqdm(range(1000), 'Calculating average shortest path length'):
        s, t = random.sample(nlist, k = 2)
        if nx.has_path(g, source = s, target = t):
           total += nx.shortest_path_length(g, source = s, target = t)
           count += 1
        elif nx.has_path(g, source = t, target = s):
           total += nx.shortest_path_length(g, source = t, target = s)
           count += 1
    return (total / float(count))



def a_node_ego((g, n, r)):
    global ego_pbar
    if r == 0:
        ## myself
        g.node[n][EGO_NETWORK_OUT + str(r)] = set([n])
        g.node[n][EGO_NETWORK_IN + str(r)] = set([n])
        g.node[n][SUCCESSORS] = g.successors(n)
        g.node[n][PREDECESSORS] = g.predecessors(n)
    else:
        g.node[n][EGO_NETWORK_OUT + str(r)] = set(g.node[n][EGO_NETWORK_OUT + str(r - 1)])
        g.node[n][EGO_NETWORK_IN + str(r)] = set(g.node[n][EGO_NETWORK_IN + str(r - 1)])
        for ng in g.node[n][SUCCESSORS]: ## the edges that pointing out
            g.node[n][EGO_NETWORK_OUT + str(r)] = g.node[n][EGO_NETWORK_OUT + str(r)] | g.node[ng][EGO_NETWORK_OUT + str(r - 1)]
        for ng in g.node[n][PREDECESSORS]: ## the edges that pointing in
            g.node[n][EGO_NETWORK_IN + str(r)] = g.node[n][EGO_NETWORK_IN + str(r)] | g.node[ng][EGO_NETWORK_IN + str(r - 1)]
    ego_pbar.update(1)
    return


def generate_ego_graph(g, sp):
    global ego_pbar
    ego_pbar = tqdm(total=g.number_of_nodes()*sp, desc='generating ego info')
    for r in range(sp):
        for n in g.nodes(data=False):
            a_node_ego((g, n, r))
    ego_pbar.close()


def get_outgoing_ego_graph(g, s, t, l):
    index = EGO_NETWORK_OUT + str(l - 1) ## the l-1 layer of neighbor, as used in following way
    node_list = set()
    for ng in g.successors(s):
        if ng != t:
            node_list = node_list | g.node[ng][index] ## here
    return node_list - set([s])


def get_incoming_ego_graph(g, s, t, l):
    ### same as above; for opposite direction
    index = EGO_NETWORK_IN + str(l - 1) ## the l-1 layer of neighbor, as used in following way
    node_list = set()
    for ng in g.predecessors(s):
        if ng != t:
            node_list = node_list | g.node[ng][index] ## here
    return node_list - set([s])


def processing_link_property((g, c, sp, s, t)):
    base_st_nodes = set([s, t])
    c.node[s][0]  = set() ## for removing previously accessed neighbor nodes (0~(l-1) layer neighbors)
    c.node[t][0]  = set() ## same as above, for the other end
    s0 = set()
    t0 = set()

    for i in range(sp):
        l = i + 1
        c.node[s][l] = get_outgoing_ego_graph(c, s, t, l) - s0 - base_st_nodes
        c.node[t][l] = get_incoming_ego_graph(c, t, s, l) - t0 - base_st_nodes

        common_nodes = (c.node[s][l] & c.node[t][l]) | (c.node[s][l] & c.node[t][l-1]) | (c.node[s][l-1] & c.node[t][l])

        index1 = 'w'+str(l)+'a' ## same as article, from inferior view
        g[s][t][index1] = None
        if len(common_nodes)==0:
            g[s][t][index1] = 0
        else:
            part1_a = min(len(c.node[s][l]  ), len(c.node[t][l])  )
            part2_a = min(len(c.node[s][l]  ), len(c.node[t][l-1]))
            part3_a = min(len(c.node[s][l-1]), len(c.node[t][l])  )
            denominator_a = float(part1_a + part2_a + part3_a)
            g[s][t][index1] = float(len(common_nodes)) / denominator_a

        c.graph[GRAPH_KEY_COMMON_NODES_LIST + str(l)].append(g[s][t][index1])

        s0 |= c.node[s][l]
        t0 |= c.node[t][l]


def compute_link_property(g, sp):
    c = g.copy()
    for i in range(sp): c.graph[GRAPH_KEY_COMMON_NODES_LIST + str(i + 1)] = []

    generate_ego_graph(c, sp)
    for s, t in tqdm(g.edges(data = False)):
        processing_link_property((g, c, sp, s, t))

    for i in range(sp):
        l = str(i + 1)
        g.graph[GRAPH_KEY_AVG_COMMON_NODES + l] = scipy.mean(c.graph[GRAPH_KEY_COMMON_NODES_LIST + l])
        g.graph[GRAPH_KEY_STD_COMMON_NODES + l] = scipy.std( c.graph[GRAPH_KEY_COMMON_NODES_LIST + l])
    return g


def generating((i, dg, fout, kmax)):
    #global pbar
    if not os.path.isfile(fout):
        rg = nx.DiGraph(nx.directed_configuration_model(
                list(d for n, d in dg.in_degree()),
                list(d for n, d in dg.out_degree()),
                create_using = nx.DiGraph()))
        rg = compute_link_property(rg, sp)
        meas = {str(i+1): rg.graph[GRAPH_KEY_AVG_COMMON_NODES + str(i+1)] for i in range(kmax)}
        stds = {str(i+1): rg.graph[GRAPH_KEY_STD_COMMON_NODES + str(i+1)] for i in range(kmax)}
        #nx.write_pajek(rg, fout)
        tmp = {'mean': meas, 'std': stds}
        with open(fout, 'w') as fp_hand:
            json.dump(tmp, fp_hand, indent=2, sort_keys=True)

    if i%10==0:
        print('generated %s'%(str(i)))


if __name__ == '__main__':
    #global pbar
    times = 100
    threads_no = 12
    basedir = 'data3/Konect'
    dirs = sorted(os.listdir(basedir))
    for dir in dirs:
        #dir = dirs[0]
        fs = sorted(os.listdir(os.path.join(basedir, dir, 'net')))
        #print(fs)
        if not os.path.exists(os.path.join(basedir, dir, 'net', 'base_info')):
            os.makedirs(os.path.join(basedir, dir, 'net', 'base_info'))
        for f in fs:
            if '.json' in f: continue
            if '.graphml' in f: continue
            if '_rand' in f: continue
            if 'rand_' in f: continue
            if '_rand_net' in f: continue
            if 'base_info' in f: continue

            fp = os.path.join(basedir, dir, 'net', f)
            outdir = os.path.join(basedir, dir, 'net', f+'_rand_net')
            if not os.path.exists(outdir):
                os.makedirs(outdir)

            dg = read_a_file(fp)
            kmax = average_shortest_path_length(dg)
            #if dg.number_of_edges()<=2: continue
            print(dg.number_of_nodes(), dg.number_of_edges())
            fsum = os.path.join(basedir, dir, 'net', 'base_info', f+'_basicsummary.txt')
            with open(fsum, 'w') as fhand:
                fhand.write(','.join([dg.number_of_nodes(), dg.number_of_edges(), kmax])+'\n')

            iterlist = []
            for i in range(times):
                fout = os.path.join(outdir, f+'_r%s.json'%(str(i).zfill(3)))
                iterlist.append((i, dg, fout, kmax))
            #pool = pathos.threading.ThreadPool(nodes=threads_no)
            #random_results = pool.map(generating, iterlist)
            pool = pathos.multiprocessing.ProcessingPool(nodes=threads_no)
            pool.imap(generating, iterlist)
            #break
    print('done')
