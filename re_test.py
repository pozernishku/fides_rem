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

'''
пожалуй, еще нужно добавить фильтр на длину слова. Скажем, слова, более 30 символов - не обрабатывать.
- точки между буквами не обрабатываются за искл. сочетание "точка+одиночная заглавная буква" разделяются пробелом;

s = '.ан&то`н.шишко .а .б .в. д.ю.ю. .а.ю. Ю.а.'
s = ' . ан&то`н.шишко .а .б .в. д.ю.ю. .а.ю. Ю.а .`'
s = 'ан&то`н.шишко .а .б .в. д.ю.ю. .а.ю. Ю.а '
s = 'ан&то`н шишко  а  б  в  д ю ю   а ю  Ю а '
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
                if len(z) + 1 <= word_length:
                    s += z + ' '
                a = i+1 # possible to meet shorter cutoff word < 30. Then need to add to s
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


    '''
- отдельно стоящие небуквенные и нецифровые последовательности удалять; это касается и тире, апострофа и амперсанда:
Ano Novo – & Australia Day – Good Friday – Easter Saturday - Easter Monday
'''
def final_cuts(word):
    n = len(word)
    
    if n == 0:
        return word
    elif n == 1:
        if (word in dashes_set or word == period or word == ampersand 
            or word in apostrophe_set or word == ' '):
            return ' '
        else:
            return word
    elif n >= 2:
        front = word[0]
        tail = word[-1]
        pre_tail = word[-2:-1]
        
        if (front in dashes_set or front == period or front == ampersand 
            or front in apostrophe_set):
            word = ' ' + word[1:]
        
        if (tail in dashes_set or tail == period or tail == ampersand 
            or tail in apostrophe_set):
            word = word[:-1] + ' '
            
        if ((pre_tail in dashes_set or pre_tail == period or pre_tail == ampersand 
            or pre_tail in apostrophe_set) and tail == ' '):
            word = word[:-2] + ' ' + word[-1:]
            
#         if () # filter a digits
    
    
    return word



long = 'aaaaafffffffffffaf-fafaffafaff.'

print(len(long))

s = long + ' - s ab 1. | .2 | a. | b. ` - . &```'

print(s)

print(remove_long_words(s))