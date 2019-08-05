# -*- encoding: utf-8 -*-

import os
import networkx as nx
from tqdm import tqdm
import pathos

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
    return dgs


def generating((i, dg, fout)):
    #global pbar
    if not os.path.isfile(fout):
        rg = nx.DiGraph(nx.directed_configuration_model(
                list(d for n, d in dg.in_degree()),
                list(d for n, d in dg.out_degree()),
                create_using = nx.DiGraph()))
        nx.write_pajek(rg, fout)
    #pbar.update(1)
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
        for f in fs:
            if '.json' in f: continue
            if '.graphml' in f: continue
            if '_rand' in f: continue
            if 'rand_' in f: continue
            if '_rand_net' in f: continue

            fp = os.path.join(basedir, dir, 'net', f)
            outdir = os.path.join(basedir, dir, 'net', f+'_rand_net')
            if not os.path.exists(outdir):
                os.makedirs(outdir)

            dgs = read_a_file(fp)
            k = 0
            for dg in dgs:
                if dg.number_of_edges()<=2: continue
                print(dg.number_of_nodes(), dg.number_of_edges())

                iterlist = []
                for i in range(times):
                    fout = os.path.join(outdir, f+'_c%s_r%s.net'%(str(k), str(i).zfill(3)))
                    iterlist.append((i, dg, fout))
                #pool = pathos.threading.ThreadPool(nodes=threads_no)
                #random_results = pool.map(generating, iterlist)
                pool = pathos.multiprocessing.ProcessingPool(nodes=threads_no)
                pool.imap(generating, iterlist)
                k+=1
            #break
    print('done')
