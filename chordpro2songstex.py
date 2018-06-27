# -*- coding: utf-8 -*-
from __future__ import print_function

import sys
import argparse
import re
import os
import io


def parse_arguments():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--src', help='path to directory with .chord files', required=True)
    parser.add_argument('--dst', help='path to output directory', required=True)
    
    return parser.parse_args()

def main(args):
    extensions = set(['.chord', '', '.txt'])
    chord_files = [f for f in next(os.walk(args.src))[2] if os.path.splitext(f)[1] in extensions]

    for chord_file in chord_files:
        src_path = os.path.join(args.src, chord_file)
        file_name = os.path.splitext(chord_file)[0]
        dst_path = os.path.join(args.dst, '{}.tex'.format(file_name))

        with io.open(src_path, 'r', encoding='utf8') as fin:
            chord_pro_contents = fin.read()

        tex_contents = chord_pro2tex(chord_pro_contents)

        with io.open(dst_path, 'w', encoding='utf8') as fout:
            fout.write(tex_contents)
    return 0

def chord_pro2tex(chord_pro):
    lines = chord_pro.split('\n')
    author_re = ur"\{artist: (.*?)\}"
    title_re = ur"\{title: (.*?)\}"
    capo_re = ur"\{capo: (.*?)\}"

    author = None
    title = None
    capo = None

    chord_replacement = lambda m: u"\\" + m.group(1)
    meta_replacement = lambda m: u"% {{{}}}".format(m.group(1))

    tex_lines = []
    for line in lines:
        songline = True
        author_m = re.search(author_re, line)
        if author_m is not None:
            author = author_m.group(1)
            songline = False

        title_m = re.search(title_re, line)
        if title_m is not None:
            title = title_m.group(1)
            songline = False

        capo_m = re.search(capo_re, line)
        if capo_m is not None:
            capo = capo_m.group(1)
            songline = False

        if songline:
            tex_line = re.sub('(\[[^:]+?\])', chord_replacement, line)
            tex_line = tex_line.replace(u'{start_of_verse}', u'\\beginverse')
            tex_line = tex_line.replace(u'{end_of_verse}', u'\\endverse')
            tex_line = tex_line.replace(u'{start_of_chorus}', u'\\beginchorus')
            tex_line = tex_line.replace(u'{end_of_chorus}', u'\\endchorus')
            tex_line = tex_line.replace(u'{chorus}', u'\\beginchorus\nR:\\endchorus')
            tex_line = re.sub('(\{.*?\})', meta_replacement, tex_line)
            tex_lines.append(tex_line)

    # produce header
    header = u'''\\beginsong{{{}}}[by={{{}}},
sr={{}},
cr={{}}]
\\transpose{{0}}
'''.format(title, author)
    if capo is not None:
        header += u'''\\capo{{{}}}
'''.format(capo)

    return header + '\n'.join(tex_lines) + '\n\\endsong\n'


if __name__ == '__main__':
    args = parse_arguments()
    sys.exit(main(args))
