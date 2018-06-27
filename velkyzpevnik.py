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
from collections import namedtuple

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
    pure_chord_re = ur"^(\s*?\[[^:]+?\])+\s*?$"
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

def get_line_flags(line):
    ## possible types: empty, part_number, part_number_with_text, text
    if len(line.strip()) == 0:
        empty = True
    else:
        empty = False

    verse_beg_re = ur"\s*?[0-9]+?\."
    if re.match(verse_beg_re, line):
        part_number = True
    else:
        part_number = False

    chorus_beg_re = ur"\s*?(®|R)[^a-zA-Z0-9]"
    if re.match(chorus_beg_re, line):
        chorus_indicator = True
    else:
        chorus_indicator = False

    signature_re = ur"\s*?(®|[a-zA-Z0-9])+?[.:]"
    if re.match(signature_re, line):
        signature = True
    else:
        signature = False

    if len(line.strip()) > 10:
        text = True
    else:
        text = False

    Flags = namedtuple('Flags', 'empty number chorus text signature')
    return Flags(empty, part_number, chorus_indicator, text, signature)

def chord_pro_versify(song):
    part_dict = {'verse': (u'{start_of_verse}',
                           u'{end_of_verse}'),
                 'chorus': (u'{start_of_chorus}',
                            u'{end_of_chorus}')}
    # try finding paragraphs (empty lines separating them)
    # try finding an offset for the whole song
    # try finding verses by numbers 1., 2., R:
    # [: blab :] is not chord!
    lines = song.split('\n')
    i = 0
    versified = []

    versified.append(part_dict['verse'][0])
    current_part = 'verse'

    while i < len(lines):
        line = lines[i]

        line_flags = get_line_flags(line)
        if line_flags.empty:
            versified.append(part_dict[current_part][1])
            versified.append('')
            versified.append(part_dict['verse'][0])
            current_part = 'verse'
        else:
            if line_flags.number:
                versified.append(part_dict[current_part][1])
                versified.append('')
                versified.append(part_dict['verse'][0])
                versified.append(line)
                current_part = 'verse'

            elif line_flags.chorus:
                # print(u'{},{}: {}'.format(line_flags.chorus, line_flags.text, line))
                if line_flags.text or (i+1 < len(lines) and get_line_flags(lines[i+1]).text and not get_line_flags(lines[i+1]).signature):
                    versified.append(part_dict[current_part][1])
                    versified.append('')
                    versified.append(part_dict['chorus'][0])
                    versified.append(line)
                    current_part = 'chorus'
                else:
                    versified.append(part_dict[current_part][1])
                    versified.append('')
                    versified.append(u'{chorus}')
                    versified.append('')
                    versified.append(part_dict['verse'][0])
                    current_part = 'verse'
            else:
                versified.append(line)
        i += 1

    versified.append(part_dict[current_part][1])

    cleaned = []
    i = 0
    while i < len(versified):
        line = versified[i].strip()
        if i+1 < len(versified):
            next_line = versified[i+1].strip()
        else:
            next_line = None

        # if next_line is not None:
        #     print('--'+line+'--')
        #     print('--'+next_line+'--')
        #     print('len(line): {}'.format(len(line)))
        #     print('len(next_line): {}'.format(len(next_line)))
        # else:
        #     print('NONE!!!')

        if (len(line) == 0) and (next_line is not None) and (len(next_line) == 0):
            # print('double empty line!')
            i += 1
            continue
        elif line == part_dict['verse'][0] and next_line is not None and next_line == part_dict['verse'][1]:
            # print('empty verse!')
            i += 2
            continue
        elif line == part_dict['chorus'][0] and next_line is not None and next_line == part_dict['chorus'][1]:
            # print('empty chorus!')
            i += 2
            continue
        else:
            cleaned.append(line)
            i += 1
                
    return u'\n' + u'\n'.join(cleaned) + u'\n'

def to_chord_pro(inlined, author, song_name, url):
    header = u'''{{title: {}}}
{{artist: {}}}
{{meta: source {}}}
'''.format(song_name, author, url)
    versified = chord_pro_versify(inlined)
    return header + '\n' + versified + '\n'

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
    chord_pro = to_chord_pro(inlined, autor, nazev, url)
    # texified = to_tex(inlined, autor, nazev)

    out_name = '{}_{}'.format(string_normalize(autor), string_normalize(nazev))

    # out_path = os.path.join('songs', out_name+'.tex')
    # with io.open(out_path, 'w', encoding='utf8') as fout:
    #     fout.write(texified)

    out_path = os.path.join('songs_chord_pro', out_name+'.chord')
    if not os.path.exists(out_path):
        print('adding: {}'.format(out_name))
        with io.open(out_path, 'w', encoding='utf8') as fout:
            fout.write(chord_pro)
    else:
        print('already exists: {}'.format(out_name))
    
    return 0

if __name__ == '__main__':
    args = parse_arguments()
    with open(args.list_file, 'r') as fin:
        list_file = fin.read()

    urls = list_file.split('\n')
    for url in urls:
        if url.startswith('#'):
            continue
        try:
            main(url)
        except Exception as e:
            print(u'url: "{}" has failed'.format(url))
            print(repr(e))
