import os

single_page = 16

prev_page = '<a class="extend prev" rel="prev" {href}>&laquo; Prev</a>\r\n'
page_ancher = '<a class="page-number" {href}>{id}</a>\r\n'
current_ancher = '<span class="page-number current">{id}</span>'
next_page = '<a class="extend next" rel="next" {href}>Next &raquo;</a>\r\n'
nav = '<nav id="page-nav">{anchors}</nav>'


def read_all(path):
    with open(path, 'r') as f:
        return f.read()


base = read_all('template/__base__.htm')
item = read_all('template/__item__.htm')
article = read_all('template/__article__.htm')

def read_summary(path):
    content = ""
    i = 0
    with open(path, 'r') as f:
        for line in f:
            if line[:3] != '<p>':
                continue

            i += 1
            content += line
            if len(content) > 100:
                return content
    return content

def read_summary_deprecated(path):
    i = 0
    need_continue = False
    content = ""
    with open(path, 'r') as f:
        for line in f:
            content += line
            i += 1
            if line[:4] == '<pre':
                need_continue = True
                i -= 5
            if line[:6] == '</pre>':
                need_continue = False
            if need_continue != True and (i > 1 or len(content) > 100):
                return content
    return content


def get_paths(basepath):
    paths = []
    for dirpath, dirnames, filenames in os.walk(basepath):
        for file in filenames:
            if (file[-6:] == '.shtml'):
                fullpath = os.path.join(dirpath, file[:-6])
                paths.append(fullpath)
    return paths


def sort_paths(paths):
    paths = sorted(paths)
    reverse_paths = sorted(paths, reverse=True)
    return reverse_paths


def replace_article_info(a, path):
    blogs, year, month, title = path.split('/')
    a = a.replace('{article-title}', title.replace('-', ' '), -1)
    a = a.replace('{article-link}', '/'+path+'.html', -1)
    a = a.replace('{article-date}', year+'年'+month+'月')
    return a


def generate_article(path, last_path, next_path):
    with open(path+'.html', 'w') as f:
        content = read_all(path + '.shtml')
        a = article.replace('{content}', content)
        a = replace_article_info(a, path)
        if last_path != '':
            a = a.replace('{last-article-link}', '/'+last_path+'.html', -1)
            a = a.replace('{last-article-title}', last_path.split('/')[-1], -1)
        else:
            a = a.replace('{last-article-link}', '/', -1)
            a = a.replace('{last-article-title}', '', -1)

        if next_path != '':
            a = a.replace('{next-article-link}', '/'+next_path+'.html', -1)
            a = a.replace('{next-article-title}', next_path.split('/')[-1], -1)
        else:
            a = a.replace('{next-article-link}', '/', -1)
            a = a.replace('{next-article-title}', '', -1)
        f.write(base.replace('{item}', a, -1))


def generate_single_article(path):
    with open(path+'.html', 'w') as f:
        content = read_all(path + '.shtml')
        a = article.replace('{content}', content)
        a = a.replace('{article-title}', '')
        a = a.replace('{article-date}', '')
        a = a.replace('{last-article-link}', '', -1)
        a = a.replace('{last-article-title}', '', -1)
        a = a.replace('{next-article-link}', '', -1)
        a = a.replace('{next-article-title}', '', -1)
        f.write(base.replace('{item}', a, -1))


def generate_page_nav(current, total):
    if current > 2:
        anchors = prev_page.replace(
            '{href}', 'href="/page/'+str(current-1)+'/"')
    else:
        anchors = prev_page.replace('{href}', 'href="/"')

    for i in range(1, current):
        anchor = page_ancher.replace('{id}', str(i))
        anchor = anchor.replace('{href}', 'href="/page/'+str(i)+'/"')
        anchors += anchor
    anchors += current_ancher.replace('{id}', str(current))
    for i in range(current+1, total+1):
        anchor = page_ancher.replace('{id}', str(i))
        anchor = anchor.replace('{href}', 'href="/page/'+str(i)+'/"')
        anchors += anchor

    anchors = anchors.replace('/page/1/', '/')

    if current < total:
        anchors += next_page.replace('{href}',
                                     'href="/page/'+str(current+1)+'/"')
    else:
        anchors += next_page.replace('{href}', 'href="/"')
    return nav.replace('{anchors}', anchors)


def generate_page(id, articles, total):
    path = './'
    print(id)
    if id > 1:
        path = 'page/' + str(id) + '/'
    if not os.path.exists(path):
        os.makedirs(path)
    with open(path+'index.html', 'w') as f:
        index_item = ''
        for a in articles:
            itemi = item.replace('{content}', read_summary(a+'.shtml'))
            index_item += replace_article_info(itemi, a)
        index_item += generate_page_nav(id, total)
        f.write(base.replace('{item}', index_item))


def generate(dirs):
    paths = []
    for dir in dirs:
        paths += get_paths(dir)
    paths = sort_paths(paths)
    total_path = len(paths)
    print("total paths:", total_path)

    generate_article(paths[0], '', paths[1])
    generate_article(paths[total_path-1], paths[total_path-2], '')
    for i in range(1, total_path-1):
        generate_article(paths[i], paths[i-1], paths[i+1])

    pages, left = divmod(total_path, single_page)
    total = pages
    if left > 0:
        total += 1
        id = pages+1
        generate_page(id, paths[pages*single_page:], total)

    for i in range(pages):
        id = i+1
        generate_page(id, paths[i*single_page:(i+1)*single_page], total)


if __name__ == '__main__':
    dirs = ["blogs/2018", "blogs/2019", "blogs/2020", "blogs/2021"]
    generate(dirs)

    generate_single_article('blogs/me')
