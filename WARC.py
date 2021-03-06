#!/usr/bin/env python3


# To add a new cell, type '#%%'
# To add a new markdown cell, type '#%% [markdown]'

#%%
import multiprocessing
import requests
import time
import glob
import gzip
import shutil
import csv
from warcio.archiveiterator import ArchiveIterator
import argparse
import os
import re
from operator import itemgetter, attrgetter

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

regex_html_char_num = re.compile(r"&#?[0-9a-zA-Z]*;", re.MULTILINE)
html_amp_dash_dict = {'&amp;':'&','&ndash;':'–','&mdash;':'—','&horbar;':'―','&minus;':'−',
                     '&hyphen;':'‐','&dash;':'‐','&HorizontalLine;':'─','&hybull;':'⁃',
                     '&#45;':'-','&#x2D;':'-','&#X2D;':'-','&#x2d;':'-','&#X2d;':'-',
                     '&#8211;':'–','&#x2013;':'–','&#X2013;':'–','&#8212;':'—','&#x2014;':'—',
                     '&#X2014;':'—','&#8722;':'−','&#x2212':'−','&#X2212':'−'}

regex_non_relevant_symb = re.compile(r"(?<=(\w))[^\s\w]+(?=(\w))", re.MULTILINE)
regex_remaining_non_relevant_symb = re.compile(r"[^\s\w]+", re.MULTILINE)
regex_alone_digits = re.compile(r"(?<=\s)[\d]+(?=\s)", re.MULTILINE)
regex_dot_capital = re.compile(r"[.](\w)", re.MULTILINE)
regex_white_space = re.compile(r"\s+", re.MULTILINE)

regex_email = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.MULTILINE | re.IGNORECASE)
regex_hashtag = re.compile(r"(?<!&)#\w+\b(?!;)")
regex_www = re.compile(r"\b(?:https?://|www\.)+\S{3,}", re.MULTILINE | re.IGNORECASE)

dashes_set = {'–','—','―','−','‐','─','⁃','-'}
period = '.'
ampersand = '&'
apostrophe_set = {"'",'‵',"’",'‘','´','`','′'}
digits_set = {'0','1','2','3','4','5','6','7','8','9'}


#%%
'''
пожалуй, еще нужно добавить фильтр на длину слова. Скажем, слова, более 30 символов - не обрабатывать.
- точки между буквами не обрабатываются за искл. сочетание "точка+одиночная заглавная буква" разделяются пробелом;
'''
def remove_long_words(text, word_length=30):
    if text is None or text == '':
        return ''
    
    a = 0
    s = ''
    
    for i, c in enumerate(text):
        if c == ' ':
            if i - a <= word_length:
                s += final_cuts(text[a:i+1])
                a = i+1
            else:
                z = final_cuts(text[a:i+1]).strip()
                if len(z) <= word_length:
                    s += z + ' '
                a = i+1
    else:
        if c == ' ':
            return s
        
        i += 1
        
        if i - a <= word_length:
            s += final_cuts(text[a:i+1])
        else:
            z = final_cuts(text[a:i+1]).strip()
            if len(z) <= word_length:
                s += z

    return s


#%%
'''
- отдельно стоящие небуквенные и нецифровые последовательности удалять; это касается и тире, апострофа и амперсанда:
Ano Novo – & Australia Day – Good Friday – Easter Saturday - Easter Monday
g = 'страница от 10.01.2018. Оригинал '
'''
def final_cuts(word):
    n = len(word)
    
    if n == 0:
        return word
    elif n == 1:
        if (word in dashes_set or word == period or word == ampersand 
            or word in apostrophe_set or word == ' ' or word in digits_set):
            return ' '
        else:
            return word
    elif n >= 2:
        front = word[0]
        tail = word[-1]
        pre_tail = word[-2:-1]
        pre_check_digit = word[-3:-2]
        
        if (front in dashes_set or front == period or front == ampersand 
            or front in apostrophe_set):
            word = ' ' + word[1:]
        
        if (tail in dashes_set or tail == period or tail == ampersand 
            or tail in apostrophe_set):
            word = word[:-1] + ' '
            
        if ((pre_tail in dashes_set or pre_tail == period or pre_tail == ampersand 
            or pre_tail in apostrophe_set) and tail == ' '):
            word = word[:-2] + ' ' + word[-1:]
            
        if (pre_check_digit in digits_set or pre_tail in digits_set or tail in digits_set or front in digits_set):
            word = clean_alone_digits(' ' + word + ' ')
    
    return word


#%%
def html_repl_func(match):
    if match.group() in html_amp_dash_dict:
        return html_amp_dash_dict[match.group()]
    else:
        return ''


#%%
'''
-удалить все хтмл-символы, кроме дефиса и амперсанда (их заменять на символ);
'''
def clean_html_char_num(text):
    match = regex_html_char_num.search(text)
    if match:
        return regex_html_char_num.sub(html_repl_func, text)
    else:
        return text


#%%
def non_relevant_repl_func(match):
    if len(match.group(0)) > 1:
        return ' '
    elif ((match.group(0) in dashes_set 
           or match.group(0) in apostrophe_set 
           or match.group(0) == period 
           or match.group(0) == ampersand)
          and (match.group(1).isalpha() and match.group(2).isalpha())):
        return match.group(0)
    elif ((match.group(0) in dashes_set)
          and ( (match.group(1).isalpha() and match.group(2) in digits_set)
             or (match.group(2).isalpha() and match.group(1) in digits_set))):
        return match.group(0)
    else:
        if match.group(1).isalpha() and match.group(2).isalpha():
            return ' '
        elif ((match.group(1).isalpha() and match.group(2) in digits_set) 
             or (match.group(2).isalpha() and match.group(1) in digits_set)
             or (match.group(1) in digits_set and match.group(2) in digits_set)):
            return ' '
        else:
            return match.group(0)


#%%
def dot_capital_repl_func(match):
    if match.group(1).isupper():
        return ' ' + match.group(1)
    else:
        return match.group(0)


#%%
'''
-все небуквенные и нецифровые символы между буквами заменяются на пробелы за исключением:
тире (все виды), точки и апострофа (их тоже несколько) между буквами не обрабатываются;
тире (все виды) между сочетаниями буква-цифра (и наоборот) не обрабатываются;
'''
def clean_non_relevant_symb(text):
    match = regex_non_relevant_symb.search(text)
    if match:
        return regex_non_relevant_symb.sub(non_relevant_repl_func, text)
    else:
        return text


#%%
'''
цифровые последовательности, не содержащие букв, удалятся;
# цифры в перемешку с небуквенными символами остаются: A-077-B
'''
def clean_alone_digits(text):
    match = regex_alone_digits.search(text)
    if match:
        return regex_alone_digits.sub('', text)
    else:
        return text


#%%
'''
сочетание "точка+одиночная заглавная буква" разделяются пробелом;
name: DUC. Enjoy - все точки также удаляются, после обаботки: сочетание "точка+одиночная заглавная буква" разделяются пробелом;
(Тут заменяются на пробел только те точки, которые стоят перед заглавной буквой)
'''
def separate_dot_capital(text):
    match = regex_dot_capital.search(text)
    if match:
        return regex_dot_capital.sub(dot_capital_repl_func, text)
    else:
        return text


#%%
'''
name: DUC. Enjoy - все точки также удаляются, после обаботки: сочетание "точка+одиночная заглавная буква" разделяются пробелом; 
удалено условие: тут удаляются все точки [^\s\w]+
'''
def remaining_non_relevant_repl_func(match):
    if len(match.group(0)) > 1:
        return ' '
    elif (match.group(0) == ampersand 
          or match.group(0) in dashes_set 
          or match.group(0) == period 
          or match.group(0) in apostrophe_set):
        
        if match.start() == 0 or match.start() == match.endpos-1:
            return ' '
        
        return match.group(0)
    else:
        return ' '


#%%
# НЕ из перечисленных: амперсанд (&), тире(все виды), точка (.), апостраф(все виды)
'''
идея же в том, чтобы избавиться от небуквенных последовательностей, а также "помочь" токенизации при построении частотного распределения. 

например, 
stuff, here - тут запятой не должно быть;
Flights: FLAGRANTS - здесь не нужно двоеточие;
Germany-c60-199?) - здесь скобки и вопр. знака;
'''
def clean_remaining_non_relevant_symb(text):
    match = regex_remaining_non_relevant_symb.search(text)
    if match:
        return regex_remaining_non_relevant_symb.sub(remaining_non_relevant_repl_func, text)
    else:
        return text


#%%
'''
кстати, выделенные url, e-mail, hash-tag могут также пригодиться для оценки, 
поэтому есть смысл их не просто удалять, а и по ним строить частотное распределение 
(например, их кол-во и распределение могут показывать "связность" ресурса).
'''
def clean_from_emails(text):
    match = regex_email.search(text)
    if match:
        return regex_email.sub(' ', text)
    else:
        return text


#%%
def clean_from_www(text):
    match = regex_www.search(text)
    if match:
        return regex_www.sub(' ', text)
    else:
        return text


#%%
def clean_from_hashtag(text):
    match = regex_hashtag.search(text)
    if match:
        return regex_hashtag.sub(' ', text)
    else:
        return text


#%%
def strip_port(res_url):
    res_len = len(res_url)
    for d in range(1, 7 if res_len > 5 else res_len+1):
        if res_url[-d] == ':':
            return res_url[:-d]
    else:
        return res_url


#%%
# h or w
# if h then stop on third / or on the end of the string (if no more /) https://test.com   www.test.com/
# if w then stop on first / or on the end of the string (if no more /)
def strip_urls(url):
    cnt = 0
    if len(url) == 0: return url
    first = url[0]
    
    for i, c in enumerate(url):
        if c == '/':
            cnt += 1
            if (first == 'h' and cnt == 3) or (first == 'w' and cnt == 1):
                return strip_port(url[:i]).strip('\\')
    else:
        return strip_port(url).strip('\\')


#%%
'''
Clean text according to http://redmine-ots.co.spb.ru/issues/7415
'''
def clean_text(text):
    return remove_long_words(
                                regex_white_space.sub(' ', 
                                     clean_alone_digits(
                                        clean_remaining_non_relevant_symb(
                                            separate_dot_capital(
                                                clean_non_relevant_symb(
                                                    clean_from_hashtag(
                                                        clean_from_www(
                                                            clean_html_char_num(
                                                                clean_from_emails(text))))))))))


#%%
'''
Сокращение хвостов происходит по проценту от общей суммы слов (90-95%), это значит: 
суммируются частоты всех слов (=100%), список слов ранжируется, например, по убыванию, 
и 5-10% «хвост» низкочастотного распределения отрезается (это почти 100% шум: ошибки, описки, прочий хлам). 
При этом общий объем частотного словаря уменьшится более, чем в два раза.

т.е. идея учитывать "плотность" распределения, а не просто обрезать по кол-ву.
тогда мы вынем нужные слова, а мусор выкинем.

и еще один нюанс: часто порог попадает на группу слов с одинаковой частотой, особенно, если объем текста большой,
так вот, хорошо бы либо всю эту группу либо отбрасывать, либо включать;

стоит добавить ещё один параметр (?) strip_ones=1
- думаю, да, пригодится.
'''
def fr_dist_with_domain(text, ref, slice_percent=90, short_tail=1, strip_ones=1, lang_percent=80):
    words_list = text.lower().split()
    domain = strip_urls(ref).lower()
        
    di = dict()
    
    for w in words_list:
        di[w] = di.get(w, 0) + 1
    
    items = sorted(di.items(), key=itemgetter(1), reverse=True)
    result_items = []
            
    cnt_all = len(words_list)
    cnt_dist = len(items)
    
    if cnt_all == 0:
        return [(' ', 0, domain),]
    elif cnt_all == 1:
        return drop_non_latin_rus([(words_list[0], 1, domain),], domain, lang_percent)
    
    if cnt_dist == 1:
        return drop_non_latin_rus([(items[0] + (domain,)),], domain, lang_percent)
    
    cur_prc = 0
    cnt_fr_words = 0
    first_one_idx = None
    cnt_border = 25 # Change to 25!
    
    for i in range(cnt_dist):
        cur_prc += 100 / (cnt_all/items[i][1])
        prev_cnt = 0 if i == 0 else items[i-1][1]
        cnt_fr_words += 1 if items[i][1] > 1 else 0
        first_one_idx = i if first_one_idx is None and items[i][1] == 1 else first_one_idx
        
#         print(items[i][0], items[i][1], cur_prc, prev_cnt, cnt_fr_words, first_one_idx)
        
        if short_tail:
            if cur_prc > slice_percent:
                if strip_ones == 1 and cnt_fr_words > cnt_border:
                    return strip_ones_func(drop_non_latin_rus(result_items, domain, lang_percent), 
                                           first_one_idx)
                else:
                    return drop_non_latin_rus(result_items, domain, 
                                              lang_percent) if result_items else [(' ', 0, domain),]
            else:
                result_items.append(items[i] + (domain,))
        else:
            if cur_prc > slice_percent:
                if items[i][1] == prev_cnt:
                    result_items.append(items[i] + (domain,))
                else:
                    if strip_ones == 1 and cnt_fr_words > cnt_border:
                        return strip_ones_func(drop_non_latin_rus(result_items, domain, lang_percent), 
                                               first_one_idx)
                    else:
                        return drop_non_latin_rus(result_items, domain, 
                                                  lang_percent) if result_items else [(' ', 0, domain),]
            else:
                result_items.append(items[i] + (domain,))
    else:
        if strip_ones == 1 and cnt_fr_words > cnt_border:
            return strip_ones_func(drop_non_latin_rus(result_items, domain, lang_percent), first_one_idx)
        else:
            return drop_non_latin_rus(result_items, domain, lang_percent) if result_items else [(' ', 0, domain),]


#%%
'''
оставить языки которые используют:
- латиницу
- русский

Filter used in fr_dist_with_domain which drops out frequency distributions 
with low language percent of cyrillic or latin chars.
'''

def drop_non_latin_rus(items, domain, lang_percent=80):
    symb_count_all = 0
    symb_count_fit = 0
    
    if not items:
        return [(' ', 0, domain),] # adds empty record with specified domain 
    else:
        for item in items:
            word = item[0]
            word_frequency = item[1]
            n = len(word)
            N = 0
            for c in word:
                x = ord(c)
                if ((x >= 0x0000 and x <= 0x02AF)    # below are blocks of Latin script in Unicode
                    or (x >= 0x1D00 and x <= 0x1DBF) # https://en.wikipedia.org/wiki/Latin_script_in_Unicode
                    or (x >= 0x1E00 and x <= 0x1EFF)
                    or (x >= 0x2070 and x <= 0x209F)
                    or (x >= 0x2100 and x <= 0x218F)
                    or (x >= 0x2C60 and x <= 0x2C7F)
                    or (x >= 0xA720 and x <= 0xA7FF)
                    or (x >= 0xAB30 and x <= 0xAB6F)
                    or (x >= 0xFB00 and x <= 0xFB06)
                    or (x >= 0xFF00 and x <= 0xFF64)
                    or (x >= 0x2460 and x <= 0x24FF) # https://en.wikipedia.org/wiki/Enclosed_Alphanumerics
                    or (x >= 0x3248 and x <= 0x325F) # https://en.wikipedia.org/wiki/Enclosed_CJK_Letters_and_Months
                    or (x >= 0x32B1 and x <= 0x32BF) # continue
                    or (x >= 0x1D400 and x <= 0x1D7FF)#https://en.wikipedia.org/wiki/Mathematical_Alphanumeric_Symbols
                    or (x >= 0x1F100 and x <= 0x1F1FF)
                    or (x >= 0xA4D0 and x <= 0xA4FF) # https://en.wikipedia.org/wiki/Lisu_(Unicode_block)
                    
                    or (x >= 0x0400 and x <= 0x052F) # below are blocks of Cyrillic script in Unicode
                    or (x >= 0x2DE0 and x <= 0x2DFF) # https://en.wikipedia.org/wiki/Cyrillic_script_in_Unicode
                    or (x >= 0xA640 and x <= 0xA69F)
                    or (x >= 0x1C80 and x <= 0x1C8F)
                    
                    or (chr(x) in dashes_set)
                    or (chr(x) == period)
                    or (chr(x) == ampersand)
                    or (chr(x) in apostrophe_set)
                    or (chr(x) in digits_set)
                   ):
                    N += 1
                else:
                    N += 0
#                 print(c, n, N, word_frequency)
            else:
                symb_count_all += n * word_frequency
                symb_count_fit += N * word_frequency
            
#             print(item, n, N, word_frequency, symb_count_all, symb_count_fit)
        else:
            prc_fit = symb_count_fit / symb_count_all * 100
            
            if prc_fit >= lang_percent:
#                 print('>>>>>>> ADDED!', domain, lang_percent)
#                 print(symb_count_all, symb_count_fit)
#                 print(items)
#                 print()
                return items
            else:
#                 print('>>>>>>> DROPED!', domain, lang_percent)
#                 print(symb_count_all, symb_count_fit)
#                 print(items)
#                 print()
                return []


#%%
def strip_ones_func(items, idx):
    if items and idx is not None:
        return items[:idx]
    elif items and idx is None:
        return items
    elif not items:
        return items
#         return [(' ', 0, dmn),] # removed parameter dmn
    else:
        return items[:idx]


#%%
'''
wet_list also accepts compressed files *.warc.wet.gz
Процент обрезания задавать параметрически, чтобы постом можно было подобрать оптимальный.
'''
def clean_tokenize_frqdis_wet_files(wet_list=None, done_list_file='wet.paths.done', 
                                    slice_percent=90, short_tail=1, strip_ones=1, lang_percent=80):
    if not wet_list:
        print('wet_list is not specified')
        return
    
    done_set = set()
    
    try:
        with open(done_list_file, newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                done_set.add(row.pop())
    except Exception as e:
        print(str(e))
        return
    
#     wet_list = wet_list[:count]
    
    for wet_file in wet_list:
        # new iteration if wet_file is done earlier
        if wet_file[3:] in done_set:
            print(wet_file[3:], 'is in', done_list_file, '- skipped.', end='\n\n')
            continue
        
        pth = './output0'
        os.makedirs(pth, exist_ok=True)
        
        print('File: ', wet_file, 'Records: ', 'Iterator in use', sep='\t', end='\n\n')
        
        wet_fr_dist = []
        
        with open(wet_file, 'rb') as stream:
            for i, record in enumerate(ArchiveIterator(stream)):
                file_uri = record.rec_headers.get_header('WARC-Target-URI')
    
                if i%10000 == 0:
                    print(record.rec_headers, 'Num: ', i, sep='\t', end='\n\n')

                if record.rec_type != 'warcinfo':
                    text = bytes.decode(record.content_stream().read())

                    # а и по ним строить частотное распределение
                    emails = ' '.join(regex_email.findall(text))
                    sites = ' '.join(map(strip_urls, regex_www.findall(text)))
                    hash_tags = ' '.join(regex_hashtag.findall(text))

                    cleaned_text = clean_text(text) + '  ' + emails + '  ' + sites + '  ' + hash_tags
                    wet_fr_dist.extend(fr_dist_with_domain(cleaned_text, file_uri, slice_percent, 
                                                           short_tail, strip_ones, lang_percent))
                                      
            else: # WET file end loop -- save to csv
                file_name_wet_csv = wet_file[3:] + '.csv'
                full_output_path = os.path.join(pth, file_name_wet_csv)
                
                with open(full_output_path, 'w', newline='') as csv_f:
                    writer = csv.writer(csv_f, delimiter='\t')
                    writer.writerows(wet_fr_dist)
                
                # gzip csv file
                with open(full_output_path, 'rb') as f_in:
                    with gzip.open(full_output_path+'.gz', 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(full_output_path)

                # Send file info to telegram chat (as telegram bot message)
                try:
                    requests.get('https://api.telegram.org/bot{0}/sendMessage?chat_id={1}&text={2}'.format(TOKEN, CHAT_ID, wet_file[3:]))
                except:
                    print('Telegram message not sent') # Message is to sdtout or nohup file
                    print(wet_file[3:]) 
                    
                # Add WET file name to wet.paths.done list
                with open(done_list_file, 'a', newline='') as f:
                    writer = csv.writer(f, delimiter='\t')
                    writer.writerows([(wet_file[3:],)])


#%%
def do_cpu_bound(args):
    with multiprocessing.Pool() as pool:  # multiprocessing.Pool(processes=2)
        pool.starmap(clean_tokenize_frqdis_wet_files, args)


#%%
if __name__ == '__main__':
    paths = glob.glob("../*.warc.wet*")
    args_list = []
    
    parser = argparse.ArgumentParser()
    parser.add_argument('slice_percent', 
                        help='Slice percent. Used to cut off the trash tail of the frequency distribution.',
                        type=int)
    parser.add_argument('short_tail',
                        help='Short tail. Used to preserve the tail which has the words with equal frequency.',
                        type=int)
    parser.add_argument('strip_ones',
                        help='Strip ones. Used to strip words with freq of one if more than 25 words have freq > 1.',
                        type=int)
    parser.add_argument('lang_percent',
                        help='Language percent. Used to drop out frequency distributions with low language percent of cyrillic or latin chars.',
                        type=int)
    parser.add_argument('count',
                        help='WET-files count to process from WET-files list. Those files which are already done will be skipped.',
                        type=int)
    args = parser.parse_args()
    
    paths = paths[:args.count]
    
    for path in paths:
        args_list.append(([path], 'wet.paths.done', args.slice_percent, args.short_tail, 
                          args.strip_ones, args.lang_percent))
        
    start_time = time.time()
    do_cpu_bound(args_list)
    duration = time.time() - start_time
    print('Duration {0} seconds'.format(duration))


#%%
# if __name__ == '__main__':
#     paths = glob.glob("../*.warc.wet*")
#     count = 3 # paramater
#     args_list = []
    
#     paths = paths[:count]
    
#     for path in paths:
#         args_list.append(([path], 'wet.paths.done', 90, 1, 1, 80))
    
#     start_time = time.time()
#     do_cpu_bound(args_list)
#     duration = time.time() - start_time
#     print('Duration {0} seconds'.format(duration))


#%%
# import fasttext


#%%
# x = fasttext.tokenize('tet I`m. Go with me Mr. John, how are you. you`d like it \ \ + f')


#%%
# x


#%%
# help(fasttext.FastText)


