from wsgiref import simple_server
import sys
import cgi
import cgitb
cgitb.enable()

import sqlite3

import hashlib
import secrets
import datetime
import re
import random

# データベースファイルのパスを設定
DBNAME = 'kadai6.db'

HTML_HEAD = '<html lang="ja">\n' \
            '<head>\n' \
            '<meta charset="UTF-8">\n' \
            '<title>langmash</title>\n' \
            '<link rel="stylesheet" type="text/css" href="./css/main.css">\n' \
            '</head>\n'

def init_db():
    con = sqlite3.connect(DBNAME)
    cur = con.cursor()
    create_table = 'create table if not exists users (name varchar(64), password varchar(64), token varchar(16))'
    cur.execute(create_table)
    con.commit()
    cur.close()
    con.close()

def hashing(name, password):
    hash = hashlib.sha256()
    hash.update(name + password)
    return hash.hexdigest()

def make_image(environ, start_response):
    name = environ['PATH_INFO']
    data = open('images/langs/'+name, 'rb').read() # simulate entire image on memory
    start_response('200 OK', [('Content-Type', 'image/jpeg'), ('Content-Length', str(len(data)))])
    return [data]

def set_cookie_header(name, value, days=365):
    dt = datetime.datetime.now() + datetime.timedelta(days=days)
    fdt = dt.strftime('%a, %d %b %Y %H:%M:%S GMT')
    secs = days * 86400
    return ('Set-Cookie', '{}={}; Expires={}; Max-Age={}; Path=/'.format(name, value, fdt, secs))

def is_auth(token):
    if token == '':
        return (False,)
    con = sqlite3.connect(DBNAME)
    cur = con.cursor()
    sql = 'select * from users where token = ?'
    count = 0
    names = []
    res = ()
    for raw in cur.execute(sql, (token,)):
        count += 1
        names.append(raw[0])
    if count == 1:
        res = (True, names)
    else:
        res =  (False,)

    con.commit()
    cur.close()
    con.close()

    return res

def make_header_and_token(environ):
    token = ''

    m = re.search(r'(.*)token=(.{32})', environ['HTTP_COOKIE'])
    if m != None:
        token = m.groups()[1]

    # HTML（共通ヘッダ部分）
    html = HTML_HEAD
    html += '<body>\n' \

    if is_auth(token)[0] == True:
        html += '<a href="/">ホーム</a>\n' \
                '<a href="/search">言語の検索</a>\n' \
                '<a href="/votepage">言語の格付け</a>\n' \
                '<a href="/add_lang">言語の追加</a>\n' \
                '<a href="/logout">ログアウト</a>\n' \
                '<h2>ようこそ!' + is_auth(token)[1][0] + '</h2>\n'
    else:
        html += '<a href="/">ホーム</a>\n' \
                '<a href="/register">ユーザ登録</a>\n' \
                '<a href="/login">ログイン</a>\n'

    html += '<h1>LangMash</h1>\n' \
            '<p>langmashはプログラミング言語の格付けサービスです</p>'

    return html, token

def root(environ, start_response):
    html, token = make_header_and_token(environ)

    html += '<div class="ranking">\n'

    con = sqlite3.connect(DBNAME)
    cur = con.cursor()
    con.text_factory = str

    sql = 'select * from langs'
    langs = {}
    for raw in cur.execute(sql):
        langs[raw[1]] = raw[2]
    langs = sorted(langs.items(), key=lambda x:x[1], reverse=True)
    html += '<h2>現在のランキング</h2>\n' \
            '<ol>\n'
    i = 0
    while i < 5:
        html += '<li>' + str(i+1) + ':' + langs[i][0] + '</li>\n'
        i += 1

    html += '</ol>\n' \
            '</div>\n' \
            '</body>\n' \
            '</html>\n'
    html = html.encode('utf-8')

    con.commit()
    cur.close()
    con.close()

    # レスポンス
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8'),
        ('Content-Length', str(len(html))), set_cookie_header('token', token)])
    return [html]

def login(environ, start_response):
    html, token = make_header_and_token(environ)

    token = ''

    form = cgi.FieldStorage(environ=environ,keep_blank_values=True)
    if ('name' not in form) or ('password' not in form):
        html += '<body>\n' \
                '<h2>LOGIN</h2>\n' \
                '<div class="form1">\n' \
                '<form>\n' \
                'ユーザー名 <input type="text" name="name"><br>\n' \
                'パスワード <input type="text" name="password"><br>\n' \
                '<input type="submit" value="登録">\n' \
                '</form>\n' \
                '</div>\n' \
                '</body>\n'
    else:
        name = form.getvalue("name", "0")
        password = form.getvalue("password", "0")
        password_hashed = hashing(name.encode(), password.encode())

        con = sqlite3.connect(DBNAME)
        cur = con.cursor()
        con.text_factory = str

        sql = 'select * from users where name = ?'
        count = 0
        user_info = []
        for raw in cur.execute(sql, (name,)):
            count += 1
            user_info.append(raw)
        if count == 1 and user_info[0][1]==password_hashed:
            html += 'ログインに成功しました\n'
            token = secrets.token_hex(16)
            sql = 'update users set token = ? where name = ?'
            cur.execute(sql, (token, name))
        else:
            html += 'ログインに失敗しました\n'

        con.commit()
        cur.close()
        con.close()

    html += '</body>\n' \
            '</html>\n'
    html = html.encode('utf-8')

    # レスポンス
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8'),
        ('Content-Length', str(len(html))), set_cookie_header('token', token)])
    return [html]

def logout(environ, start_response):
    html, token = make_header_and_token(environ)

    con = sqlite3.connect(DBNAME)
    cur = con.cursor()
    delete_token = 'update users set token = ? where token = ?'
    cur.execute(delete_token, ('', token))
    con.commit()
    cur.close()
    con.close()

    html += '<p>ログアウトに成功しました</p>\n' \
            '</body>\n' \
            '</html>\n'
    html = html.encode('utf-8')

    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8'),
        ('Content-Length', str(len(html))), set_cookie_header('token', token)])
    return [html]

def register(environ, start_response):
    html, token = make_header_and_token(environ)

    token = ''

    form = cgi.FieldStorage(environ=environ,keep_blank_values=True)
    if ('name' not in form) or ('password' not in form):
        html += '<h2>REGISTER</h2>\n' \
                '<div class="form1">\n' \
                '<form>\n' \
                'ユーザー名 <input type="text" name="name"><br>\n' \
                'パスワード <input type="text" name="password"><br>\n' \
                '<input type="submit" value="登録">\n' \
                '</form>\n' \
                '</div>\n' \
                '</body>\n'
    else:
        name = form.getvalue("name", "0")
        password = form.getvalue("password", "0")

        password_hashed = hashing(name.encode(), password.encode())

        con = sqlite3.connect(DBNAME)
        cur = con.cursor()
        con.text_factory = str
        sql = 'insert into users (name, password) values (?,?)'
        cur.execute(sql, (name, password_hashed))

        token = secrets.token_hex(16)

        sql = 'update users set token = ? where name = ?'
        cur.execute(sql, (token, name))
        con.commit()
        cur.close()
        con.close()

        environ['PATH_INFO'] = '/' #login?name='+name+'&password='+password_hashed
        # start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8'),
        #     ('Content-Length', str(len(html))), set_cookie_header('token', token)])
        return main(environ, start_response)

    html += '</html>\n'
    html = html.encode('utf-8')

    # レスポンス
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8'),
        ('Content-Length', str(len(html))), set_cookie_header('token', token)])
    return [html]

def votepage(environ, start_response):
    html, token = make_header_and_token(environ)

    con = sqlite3.connect(DBNAME)
    cur = con.cursor()
    con.text_factory = str

    sql = 'select * from langs'
    langs = []
    for raw in cur.execute(sql):
        langs.append(raw)

    con.commit()
    cur.close()
    con.close()

    l_lang = ''
    r_lang = ''

    while l_lang == r_lang:
        l_lang = langs[random.randint(0, len(langs)-1)]
        r_lang = langs[random.randint(0, len(langs)-1)]

    html += '<h3>Which Hotter? Click to Choose<h3>\n' \
            '<div class="lang_box" style="display: inline-block;">\n' \
            '<img src="' + l_lang[3] + '" width="300" height="300">\n' \
            '<p>' + l_lang[1] + '</p>\n' \
            '<a href="/vote?lang=' + l_lang[1] + '&score=' + str(l_lang[2]) + '">vote</a>\n' \
            '</div>\n' \
            '<div class="lang_box" style="display: inline-block;">\n' \
            '<img src="' + r_lang[3] + '" width="300" height="300">\n' \
            '<p>' + r_lang[1] + '</p>\n' \
            '<a href="/vote?lang=' + r_lang[1] + '&score=' + str(r_lang[2]) + '">vote</a>\n' \
            '</div>\n' \
            '</body>\n'

    html += '</html>\n'
    html = html.encode('utf-8')

    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8'), ('Content-Length', str(len(html))), set_cookie_header('token', token)])
    return [html]

def vote(environ, start_response):
    html, token = make_header_and_token(environ)

    # query = environ.get('QUERY_STRING')
    # m = re.search(r'.*lang=(.*)&score=(.*$)', query)
    # print(m)
    # lang = m.groups()[0]
    # score = int(m.groups()[1]) + 1
    form = cgi.FieldStorage(environ=environ,keep_blank_values=True)
    lang = form.getvalue("lang", "0")
    score = int(form.getvalue("score", "0")) + 1
    print(lang)
    print(score)

    con = sqlite3.connect(DBNAME)
    cur = con.cursor()
    con.text_factory = str

    sql = 'update langs set score = ? where name = ?'
    cur.execute(sql, (score, lang))

    con.commit()
    cur.close()
    con.close()

    html += '投票が完了しました\n' \
            '</body>\n'

    html += '</html>\n'
    html = html.encode('utf-8')

    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8'), ('Content-Length', str(len(html))), set_cookie_header('token', token)])
    return [html]

def search(environ, start_response):
    html, token = make_header_and_token(environ)


    form = cgi.FieldStorage(environ=environ, keep_blank_values=True)
    if 'search' not in form:
        html += '<br />\n' \
                '<div class="search_from">\n' \
                '<form>\n' \
                'プログラミング言語を検索  <input type="search" name="search" placeholder="キーワードを入力してください">\n' \
                '<input type="submit" value="検索">\n' \
                '</form>\n' \
                '</div>\n' 
    else:
        search = form.getvalue("search", "0")
        print(search)

        html += '<div class="ranking">\n' \
                '<ol>\n'

        con = sqlite3.connect(DBNAME)
        cur = con.cursor()
        con.text_factory = str
        sql = 'select * from langs where name = ?'
        for raw in cur.execute(sql, (search,)):
            html += raw[1] + 'の得票数 : ' + str(raw[2]) + '\n' 
        
        html += '</div>\n' \
                '</ol>\n'

        con.commit()
        cur.close()
        con.close()

    html += '</body>\n' \
            '</html>\n'
    html = html.encode('utf-8')

    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8'), ('Content-Length', str(len(html))), set_cookie_header('token', token)])
    return [html]

def add_lang(environ, start_response):
    html, token = make_header_and_token(environ)

    form = cgi.FieldStorage(environ=environ, keep_blank_values=True)
    if 'name' not in form:
        html += '<br />\n' \
                '<div class="add_form">\n' \
                '<form>\n' \
                '追加したい言語を入力してください\n' \
                '<input type="text" name="name">\n' \
                '<input type="submit" value="登録">\n' \
                '</form>\n' \
                '</div>\n' 
    else:
        name = form.getvalue("name", "0")

        con = sqlite3.connect(DBNAME)
        cur = con.cursor()
        con.text_factory = str
        sql = 'insert into langs (name, score, filename) values (?, ?, ?)'
        cur.execute(sql, (name, 0, ''))
        # print(sqlite3.Error)
        
        html += '言語を追加しました\n'
        
        con.commit()
        cur.close()
        con.close()

    html += '</body>\n' \
            '</html>\n'
    html = html.encode('utf-8')

    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8'), ('Content-Length', str(len(html))), set_cookie_header('token', token)])
    return [html]

def main(environ, start_response):
    # pathで場合分け
    path = environ['PATH_INFO']
    # print(path)

    m = re.search(r'.*(.png)$', path)
    if m != None:
        # 画像ファイルの時
        response = make_image(environ, start_response)
        return response

    if path == '/' or path == '':
        response = root(environ, start_response)
        return response
    elif path == '/login':
        response = login(environ, start_response)
        return response
    elif path == '/register':
        response = register(environ, start_response)
        return response
    elif path == '/logout':
        response = logout(environ, start_response)
        return response
    elif path == '/votepage':
        response = votepage(environ, start_response)
        return response
    elif path == '/vote':
        response = vote(environ, start_response)
        return response
    elif path == '/search':
        response = search(environ, start_response)
        return response
    elif path == '/add_lang':
        response = add_lang(environ, start_response)
        return response
    else:
        start_response('404 Not Found', [('Content-type', 'text/plain')])
        return [b'404 Not Found']

if __name__ == '__main__':
    print('-------------------')
    print('welcome to langmash')
    print('-------------------')
    port = 8080
    if len(sys.argv) == 2:
        port = int(sys.argv[1])

    init_db()
    server = simple_server.make_server('', port, main)
    server.serve_forever()