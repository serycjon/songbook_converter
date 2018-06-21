# -*- coding: utf-8 -*-
from __future__ import print_function

try: 
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup

try: #python3
    from urllib.request import urlopen
except: #python2
    from urllib2 import urlopen
 
import unicodedata
import sys
import argparse
import re
import io
import os


def parse_arguments():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('list_file', help='path to a file listing urls')
    
    return parser.parse_args()

def download(url):
    content = urlopen(url).read()
    return content

def get_plaintext_song(url):
    html = download(url)
    soup = BeautifulSoup(html)

    autor = soup.find('h1', attrs={'class': 'zarazka'}).find('a').text
    nazev = soup.find('h1', attrs={'class': 'nazev'}).text

    song_soup = soup.find('pre', attrs={'class': 'pisen'})
    chord_re = r"<span class=\"chord\" .*?>(.*?)</span>"
    song_html = unicode(song_soup)
    replacement = lambda m: u"[{}]".format(m.group(1))
    plaintext = re.sub(chord_re, replacement, song_html)
    if plaintext.startswith('<pre class="pisen">'):
        plaintext = plaintext[19:]
    else:
        raise ValueError('incorrect song html - missing start <pre class="pisen">')

    if plaintext.endswith('\n</pre>'):
        plaintext = plaintext[:-7]
    else:
        raise ValueError("incorrect song html - missing end </pre>")
    return plaintext, autor, nazev

def pure_chord_line(line):
    pure_chord_re = ur"^(\s*?\[.+?\])+\s*?$"
    m = re.match(pure_chord_re, line)
    return m is not None

def join_chord_text(chords, text):
    replacement = lambda m: "." + " "*(len(m.group(1))-3)

    condensed_chords = re.sub(ur"(\[.+?\])", replacement, chords)
    chords = re.findall(ur"\[.+?\]", chords)
    i = 0
    j = 0
    out = u""
    while i < len(text):
        if i < len(condensed_chords) and condensed_chords[i] == '.':
            out += chords[j]
            j += 1
        out += text[i]
        i += 1
    return out

def inline_chords(plaintext):
    lines = plaintext.split('\n')
    inlined_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if pure_chord_line(line):
            condensed = re.sub(ur"\[.+?\]", '.', line)
            if i+1 >= len(lines) or len(condensed) > len(lines[i+1])*1.25:
                # some weird line
                inlined_lines.append(line)
                i += 1
            else:
                # chord line followed by a normal line
                inlined_lines.append(join_chord_text(line, lines[i+1]))
                i += 2
        else:
            inlined_lines.append(line)
            i += 1
            
    inlined = '\n'.join(inlined_lines)
    return inlined

def versify(song):
    verse_beg = u'\\beginverse'
    verse_end = u'\\endverse'
    lines = song.split('\n')
    versified = []
    versified.append(verse_beg)
    last_opened = True
    for line in lines:
        if len(line.strip()) == 0:
            if not last_opened:
                versified.append(verse_end)
                versified.append(verse_beg)
        else:
            last_opened = False
            versified.append(line)

    return u'\n' + u'\n'.join(versified) + u'\n'

def to_tex(inlined, author, song_name):
    header = u'''\\beginsong{{{}}}[by={{{}}},
    sr={{}},
    cr={{}}]
    \\transpose{{0}}'''.format(song_name, author)
    replacement = lambda m: u"\\" + m.group(1)
    texified = re.sub('(\[.+?\])', replacement, inlined)
    texified = versify(texified)
    return header + '\n' + texified + '\n' + '\\endsong\n'

def string_normalize(data):
    czech = translate_czech(data)
    data = re.sub(ur"[^0-9a-zA-Z]", '-', czech)
    return translate_czech(unicode(data))

def translate_czech(data):
    # data = unicode(data, 'UTF-8')
    return unicodedata.normalize('NFKD', data.lower()).encode('ascii', 'ignore')
    
def main(url):
    plaintext, autor, nazev = get_plaintext_song(url)
    inlined = inline_chords(plaintext)
    texified = to_tex(inlined, autor, nazev)

    out_name = '{}_{}.tex'.format(string_normalize(autor), string_normalize(nazev))
    print('out_name: {}'.format(out_name))

    out_path = os.path.join('songs', out_name)
    with io.open(out_path, 'w', encoding='utf8') as fout:
        fout.write(texified)
    
    return 0

if __name__ == '__main__':
    args = parse_arguments()
    with open(args.list_file, 'r') as fin:
        list_file = fin.read()

    urls = list_file.split('\n')
    for url in urls:
        try:
            main(url)
        except Exception as e:
            print(u'url: "{}" has failed'.format(url))
