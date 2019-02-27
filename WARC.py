
#%%
import glob
import warcat.model
import os
import re
regex_html_char_num = re.compile(r"&#?[0-9a-zA-Z]*;", re.MULTILINE)
html_amp_dash_dict = {'&amp;':'&','&ndash;':'–','&mdash;':'—','&horbar;':'―','&minus;':'−',
                     '&hyphen;':'‐','&dash;':'‐','&HorizontalLine;':'─','&hybull;':'⁃',
                     '&#45;':'-','&#x2D;':'-','&#X2D;':'-','&#x2d;':'-','&#X2d;':'-',
                     '&#8211;':'–','&#x2013;':'–','&#X2013;':'–','&#8212;':'—','&#x2014;':'—',
                     '&#X2014;':'—','&#8722;':'−','&#x2212':'−','&#X2212':'−'}

regex_non_relevant_symb = re.compile(r"(?<=(\w))[^\s\w]+(?=(\w))", re.MULTILINE)
regex_remaining_non_relevant_symb = re.compile(r"[^\s\w]+", re.MULTILINE)
regex_alone_digits = re.compile(r"((^\d+(?=\s))|((?<=\s)[\d]+(?=\s))|((?<=\s)\d+$))", re.MULTILINE)
regex_dot_capital = re.compile(r"[.](\w)", re.MULTILINE)
regex_white_space = re.compile(r"\s+", re.MULTILINE)
dashes_set = {'–','—','―','−','‐','─','⁃','-'}
period = '.'
ampersand = '&'
apostrophe_set = {"'",'‵',"’",'‘','´','`','′'}
digits_set = {'0','1','2','3','4','5','6','7','8','9'}


#%%
'''
пожалуй, еще нужно добавить фильтр на длину слова. Скажем, слова, более 30 символов - не обрабатывать.
'''
def remove_long_words(text, word_length=30):
    if text is None:
        return ''
    elif len(text) <= word_length:
        return text
    
    a = 0
    s = ''
    
    for i, c in enumerate(text):
        if c == ' ':
            if i - a <= word_length:
                s += text[a:i+1]
                a = i+1
            else:
                a = i+1
    else:
        if c == ' ':
            return s
        
        i += 1
        
        if i - a <= word_length:
            s += text[a:i+1]

    return s


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
             or (match.group(2).isalpha() and match.group(1) in digits_set)):
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
(тут удаляются все точки)
'''
def remaining_non_relevant_repl_func(match):
    if len(match.group(0)) > 1:
        return ' '
    elif (match.group(0) == ampersand 
          or match.group(0) in dashes_set 
#           or match.group(0) == period 
          or match.group(0) in apostrophe_set):
        return match.group(0)
    else:
        return ' '


#%%
# НЕ из перечисленных: амперсанд (&), тире(все виды), апостраф(все виды)
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
Clean text according to http://redmine-ots.co.spb.ru/issues/7415
'''
def clean_text(text):
    return remove_long_words(regex_white_space.sub(' ', 
                                     clean_alone_digits(
                                        clean_remaining_non_relevant_symb(
                                            separate_dot_capital(
                                                clean_non_relevant_symb(
                                                    clean_html_char_num(text)))))))


#%%
'''
wet_list also accepts compressed files *.warc.wet.gz
'''
def clean_and_tokenize_wet_files(wet_list=None):
    if not wet_list:
        print('wet_list is not specified')
        return 
    
#     wet_list = wet_list[-1:] # one (last 00639) in list (require all list)
    wet_list = wet_list[0:1]
    
    for wet_file in wet_list:
        warc = warcat.model.WARC()
        warc.load(wet_file)
        
        pth = os.path.join('./output', wet_file[3:])
#         lg = os.path.join('./logs', wet_file[3:]) # logging - continue
        os.makedirs(pth, exist_ok=True)
#         os.makedirs(lg, exist_ok=True)
        
        print('File: ', wet_file, 'Records: ', len(warc.records), sep='\t', end='\n\n') # to logs is better
        
        for i, record in enumerate(warc.records[0:1000]): # sliced here!
            print('WARC-Type: ', record.warc_type, 'Content-Length: ', record.content_length, 
                  'Content-Type: ', record.header.fields['content-type'], 
                  'WARC-Target-URI: ' , record.header.fields.get('WARC-Target-URI'), 
                  'WARC-Date: ' , record.header.fields.get('WARC-Date'), 
                  'Num: ', i, sep='\t') 
            
            if record.warc_type != 'warcinfo':
                with record.content_block.get_file() as f:
                    text = bytes.decode(f.read())
                    file_name_urn = record.header.fields.get('WARC-Record-ID').split(':')[-1][:-1] + '.txt'
                    
                    with open(os.path.join(pth, file_name_urn), 'w') as f_to_fs:
                        f_to_fs.write(clean_text(text))
                        
#                     print('\nDirty: \n\n', text, end='\n\n')
#                     print('\nClean: \n\n', clean_text(text), end='\n\n')


#%%
if __name__ == '__main__':
    clean_and_tokenize_wet_files(glob.glob("../*.warc.wet*"))


#%%



