# -*- encoding: utf-8 -*-

import os
import json

import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

import HATA as hata


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
    return dg


def process_one_graph(fp):
    print('')
    print('')
    print('')
    print(fp)
    g = read_a_file(fp)

    dirpath, fn1 = os.path.split(fp)
    #fp2 = os.path.join(dirpath, fn1+'_pos.json')
    fp3 = os.path.join(dirpath, fn1+'_ext.json')
    fp4 = os.path.join(dirpath, fn1+'_int.json')
    fp5 = os.path.join(dirpath, fn1+'_out.graphml')
    fp6 = os.path.join(dirpath, fn1+'_res.png')
    """
    print('prepare pos file')
    if not(os.path.isfile(fp2)):
        pos = nx.spring_layout(g)
        pos = { k:(v[0], v[1]) for k,v in pos.items() }
        with open(fp2, 'w') as fp_hand:
            json.dump(pos, fp_hand, indent=2, sort_keys=True)
    else:
        with open(fp2, 'r') as fread:
            pos = json.load(fread)
    """

    print('start running algorithm')
    if not(os.path.isfile(fp5)):
        dg, ext_dic, int_dic = hata.bridge_or_bond(g, times=100,
                                        external=None,  threads=12,
                                        run_silent=False)
        with open(fp3, 'w') as fp_hand:
            json.dump(ext_dic, fp_hand, indent=2, sort_keys=True)
        with open(fp4, 'w') as fp_hand:
            json.dump(int_dic, fp_hand, indent=2, sort_keys=True)
        nx.write_graphml(dg, fp5)
        print('making figures')
        make_fig(dg, pos, fn1[:-4], fp6)
    else:
        print('done before, skip', fp)

def make_fig(dg, pos, name, fp6):
    cmap = ListedColormap(['w', 'xkcd:sapphire', 'xkcd:rosy pink', 'xkcd:boring green', 'xkcd:butterscotch'])
    color_dic = {1:'xkcd:sapphire', 2:'xkcd:rosy pink', 3:'xkcd:boring green', 4:'xkcd:butterscotch', -1:'w'}

    fig, axs = hata.draw_result(dg, pos=pos, color_dic=color_dic, cmap=cmap)
    fig.suptitle(name)
    plt.tight_layout()
    fig.savefig(fp6, bbox_to_inches='tight')
    plt.close()
    #break


if __name__ == '__main__':
    dirbase = 'data3/Konect'
    dirs = sorted(os.listdir(dirbase))
    for dir in dirs:
        #dir = dirs[-2]
        #print dir
        pdir = os.path.join(dirbase, dir, 'net')
        fs = sorted(os.listdir(pdir))
        fs = [ f for f in fs if f[:4]=='out.' ]
        #print fs
        for f in fs:
            fp = os.path.join(pdir, f)
            process_one_graph(fp)
        print('done')
