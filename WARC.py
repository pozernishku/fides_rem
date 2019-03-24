
#%%
import glob
import csv
import warcat.model
import argparse
# import logging
import os
import re
from operator import itemgetter, attrgetter

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
    if text is None:
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
def fr_dist_with_domain(text, ref, slice_percent=90, short_tail=1, strip_ones=1):
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
        return [(words_list[0], 1, domain),]
    
    if cnt_dist == 1:
        return [(items[0] + (domain,)),]
    
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
                    return strip_ones_func(result_items, first_one_idx, domain)
                else:
                    return result_items if result_items else [(' ', 0, domain),]
            else:
                result_items.append(items[i] + (domain,))
        else:
            if cur_prc > slice_percent:
                if items[i][1] == prev_cnt:
                    result_items.append(items[i] + (domain,))
                else:
                    if strip_ones == 1 and cnt_fr_words > cnt_border:
                        return strip_ones_func(result_items, first_one_idx, domain)
                    else:
                        return result_items if result_items else [(' ', 0, domain),]
            else:
                result_items.append(items[i] + (domain,))
    else:
        if strip_ones == 1 and cnt_fr_words > cnt_border:
            return strip_ones_func(result_items, first_one_idx, domain)
        else:
            return result_items if result_items else [(' ', 0, domain),]


#%%
def strip_ones_func(items, idx, dmn):
    if items and idx is not None:
        return items[:idx]
    elif items and idx is None:
        return items
    elif not items:
        return [(' ', 0, dmn),]
    else:
        return items[:idx]


#%%
'''
wet_list also accepts compressed files *.warc.wet.gz
Процент обрезания задавать параметрически, чтобы постом можно было подобрать оптимальный.
'''
def clean_tokenize_frqdis_wet_files(wet_list=None, slice_percent=90, short_tail=1, strip_ones=1):
    if not wet_list:
        print('wet_list is not specified')
        return
    
#     wet_list = wet_list[-1:] # one (last 00639) in list (require all list)
#     wet_list = wet_list[0:3]
    
    for wet_file in wet_list:
        warc = warcat.model.WARC()
        
        try:
            warc.load(wet_file)
        except Exception as e:
            print('Error in ', wet_file)
            with open(os.path.join('./output', wet_file[3:] + '.error'), 'w') as e_f:
                e_f.write(str(e))
            continue
        
        pth = os.path.join('./output', wet_file[3:])
#         lg = os.path.join('./logs', wet_file[3:]) # logging - continue

        os.makedirs(pth, exist_ok=True)
#         os.makedirs(lg, exist_ok=True)
        
        print('File: ', wet_file, 'Records: ', len(warc.records), sep='\t', end='\n\n') # to logs is better
        
        wet_fr_dist = []
        
        for i, record in enumerate(warc.records): # sliced here! warc.records[:50]
            file_uri = record.header.fields.get('WARC-Target-URI')
            print(record.header.fields.list(), 'Num: ', i, sep='\t', end='\n\n')
            
            if record.warc_type != 'warcinfo':
                with record.content_block.get_file() as f:
                    text = bytes.decode(f.read())
                    
                    # а и по ним строить частотное распределение
                    emails = ' '.join(regex_email.findall(text))
                    sites = ' '.join(map(strip_urls, regex_www.findall(text)))
                    hash_tags = ' '.join(regex_hashtag.findall(text))
                    
                    cleaned_text = clean_text(text) + '  ' + emails + '  ' + sites + '  ' + hash_tags
                    wet_fr_dist.extend(fr_dist_with_domain(cleaned_text, file_uri, slice_percent, 
                                                           short_tail, strip_ones))
                    
        else: # WET file end loop -- save to csv
            file_name_wet_csv = wet_file[3:] + '.csv'
            with open(os.path.join(pth, file_name_wet_csv), 'w', newline='') as csv_f:
                writer = csv.writer(csv_f, delimiter='\t')
                writer.writerows(wet_fr_dist)


#%%
# if __name__ == '__main__':
#     clean_tokenize_frqdis_wet_files(glob.glob("../*.warc.wet*"), 90, 1, 1)


#%%
if __name__ == '__main__':
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
    
    args = parser.parse_args()
    
    clean_tokenize_frqdis_wet_files(glob.glob("../*.warc.wet*"), args.slice_percent, 
                                    args.short_tail, args.strip_ones)


#%%



