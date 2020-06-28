#!/bin/bash
if [ $1 = 'init' ]; then
    echo 'データベースを初期化します'
    rm -r -f kadai6.db
fi

if [[ ! -f ./kadai6.db ]]; then 
    echo 'データベースを初期化'
    sqlite3 kadai6.db < init_db.sql
fi
echo 'langmashを起動します…'
python main.py