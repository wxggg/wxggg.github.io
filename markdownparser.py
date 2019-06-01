import os,re

def p(line):
    return '<p>'+line.strip()+'</p>'

def li(line):
    return '<li>'+line.strip()+'</li>'

def headn(n, line):
    ret = '<h' + str(n) + '><a data-uk-modal="{target:\'#category-id\'}">' + line.strip() + '</a></h' + str(n) + '>\n'

    return ret

def blockquote(line):
    return '<blockquote>'+line+'</blockquote>'

def check_char(line, c):
    for i in range(len(line)):
        if line[i] != c:
            return i
    return len(line)

def check_anchor(line):
    result = re.findall(r'\[.+\]\(.+\)',line)
    for res in result:
        x = res.replace('[','').replace(')','')
        nameurl = x.split('](')
        if len(nameurl)==2:
            anchor = '<a href="'+nameurl[1]+'">'+nameurl[0]+'</a>'
            line=line.replace(res, anchor)
    return line

def check_inline_code(line):
    result = []
    indexs=[i.start() for i in re.finditer('`', line)]
    length = len(indexs)
    if length>0 and length%2==0:
        for i in range(int(length/2)):
            i1 = indexs[i*2]
            i2 = indexs[i*2+1]+1
            result.append(line[i1:i2])

    for res in result:
        x = res.replace('`','')
        inlinecode='<code>'+x+'</code>'
        line = line.replace(res,inlinecode)
    return line

def check_strong(line):
    result = []
    indexs=[i.start() for i in re.finditer('__', line)]
    length = len(indexs)
    if length>0 and length%2==0:
        for i in range(int(length/2)):
            i1 = indexs[i*2]
            i2 = indexs[i*2+1]+2
            result.append(line[i1:i2])

    for res in result:
        x = res.replace('__','')
        inlinecode='<strong>'+x+'</strong>'
        line = line.replace(res,inlinecode)
    return line

def imgline(dirpath, line):
    img=line.replace('![](','').replace(')','').strip()
    url = img
    if img[:4] != 'http' and img[:3] != 'www':
        url = '/' + os.path.join(dirpath, img)
    return '<img src='+'"'+url+'" alt="">'

def parse(dirpath, file):
    filename = os.path.join(dirpath, file)
    f = open(filename+'.md', 'r', encoding='utf8')
    fhtml = open(filename+'.shtml', 'w', encoding='utf8')

    incode = False
    inmath = False
    inblockquote = False
    inlist = False

    for line in f:
        hn = check_char(line, '#')
        coden = check_char(line, '`')
        line = line.replace('```','')
        blockquoten = check_char(line, '>')
        starn = check_char(line, '*')
        dollarn = check_char(line, '$')
        line = re.sub(r'\\{1,2}([a-z*(){}])', r'\\\1', line)
        line = re.sub(r'\\([\*])', '*', line)



        if incode:
            if coden==3:
                incode=False
                fhtml.write('</pre>\n')
            else:
                line = line.replace('&','& ').replace('<','< ')
                fhtml.write(line)
        else:
            line = check_anchor(line)
            line = check_inline_code(line)
            line = check_strong(line)
            if starn!=1 and inlist:
                fhtml.write('</ul>\n')
                inlist=False
            if line[0]=='!':
                fhtml.write(imgline(dirpath, line)+'\n')
            elif hn>0:
                if inblockquote:
                    fhtml.write('</blockquote>\n')
                fhtml.write(headn(hn, line[hn:])+'\n')
            elif coden==3:
                incode=True
                codetype = line.strip()
                fhtml.write('<pre class="brush: '+codetype+';">\n')
            elif blockquoten>0:
                inblockquote=True
                fhtml.write('<blockquote>'+p(line[blockquoten:]))
            elif starn==3:
                fhtml.write('<hr>\n')
            elif starn==1:
                if inlist==False:
                    inlist=True
                    fhtml.write('<ul>')
                fhtml.write(li(line[starn:])+'\n')
            elif line.strip() == '$$':
                if inmath:
                    inmath = False
                    fhtml.write('$$\n')
                else:
                    inmath = True
                    fhtml.write('$$')
            elif line=='\n':
                if inblockquote:
                    inblockquote=False
                    fhtml.write('</blockquote>\n');
            else:
                if inmath:
                    fhtml.write(line.strip())
                else:
                    fhtml.write(p(line)+'\n')


    if inlist:
        fhtml.write('</ul>\n')
        inlist=False
    if inblockquote:
        fhtml.write('</blockquote>\n')
    f.close()


def parse_dir(dir):
    for dirpath,dirnames,filenames in os.walk(dir):
        for file in filenames:
            if (file[-3:] == '.md'):
                parse(dirpath, file[:-3])


if __name__ == '__main__':
    parse_dir('blogs')
