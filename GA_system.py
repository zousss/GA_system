#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, url_for, json,jsonify
from flaskext.mysql import MySQL
from flask import render_template
import datetime
import time

mysql = MySQL()
app = Flask(__name__)
mysql.init_app(app)

@app.route("/")
def hello():
    return "Hello"

#游分系统入口
@app.route("/search")
def search_game():
    kf_games = kaifu_games()
    remen_games = hot_games()
    xin_games = new_games()
    return render_template('search_page.html',kf_games=kf_games,xin_games=xin_games,remen_games=remen_games)

#获取近期开服游戏
def kaifu_games():
    sql = """
        SELECT
        	distinct
        	game_name
        FROM
        	gametesthistory
        WHERE
        	game_testserver NOT REGEXP '公测|封测|内测'
        AND SUBSTR(game_testtime, 1, 10)= CURRENT_DATE
        LIMIT 10
    """
    cursor = mysql.connect().cursor()
    cursor.execute(sql)
    kf_games = cursor.fetchall()
    return kf_games

#获取近期热门游戏
def hot_games():
    sql = """
        SELECT
        	distinct
        	t1.game_name,
        	t2.app_rank
        FROM
        	gametesthistory t1
        left JOIN
        	appinfo.app_rank t2
        on t1.game_name = t2.app_name
        WHERE
        	SUBSTR(t1.game_testtime, 1, 10)= CURRENT_DATE
        ORDER BY t2.app_rank desc
        LIMIT 10
    """
    cursor = mysql.connect().cursor()
    cursor.execute(sql)
    remen_games = cursor.fetchall()
    return remen_games

#获取近期新游戏
def new_games():
    sql = """
        SELECT
        	distinct
        	game_name
        FROM
        	gametesthistory
        WHERE
        	game_testserver REGEXP '公测|封测|内测'
        AND SUBSTR(game_testtime, 1, 10)= CURRENT_DATE
        LIMIT 10
    """
    cursor = mysql.connect().cursor()
    cursor.execute(sql)
    xin_games = cursor.fetchall()
    return xin_games

#总况页面获取数据生成echarts图表
@app.route('/echarts',methods=['GET'])
def get_game_echarts():
    cursor = mysql.connect().cursor()
    sql = """
        SELECT
        	t1.dh_game_type,
        	t1.test_type,
        	t1.type_cnt / t2.type_cnt
        FROM
        	game_type_view t1
        LEFT JOIN(
        	SELECT
        		test_type,
        		sum(type_cnt) AS type_cnt
        	FROM
        		game_type_view
        	GROUP BY
        		test_type
        )t2 ON t1.test_type = t2.test_type
    """
    cursor.execute(sql)
    gametypes = cursor.fetchall()
    type = []
    for game in gametypes:
        type.append({'dh_game_type':game[0],'test_type':game[1],'type_num':float(game[2])})
    return json.dumps(type)

#总况页面获取数据生成echarts图表
@app.route('/channel_echarts',methods=['GET'])
def get_channel_echarts():
    cursor = mysql.connect().cursor()
    sql = """
        select a.dh_game_type,a.game_source,a.type_cnt/b.total_cnt
            from (
                 select t1.game_source as game_source,t2.dh_game_type as dh_game_type,count(*) as type_cnt
                   from game_info t1
                   join game_type t2
                     on t1.game_type = t2.game_type and t1.game_source = t2.url
                  group by t1.game_source,t2.dh_game_type
             ) a
             JOIN (
                 select t1.game_source as game_source,count(*) as total_cnt
                   from game_info t1
                   join game_type t2
                     on t1.game_type = t2.game_type and t1.game_source = t2.url
                  group by t1.game_source
             ) b
             on a.game_source = b.game_source
            ;
    """
    cursor.execute(sql)
    gametypes = cursor.fetchall()
    type = []
    for game in gametypes:
        type.append({'dh_game_type':game[0],'game_source':game[1],'type_rate':float(game[2])})
    return json.dumps(type)

#游戏详情入口
@app.route("/game_info",methods=['GET'])
def game_info():
    if request.method == "GET":
        if request.args.get('gamename'):
            gamename = request.args.get('gamename')
            game_info = get_game_info(gamename)
            same_type_game = get_same_type(gamename)
            simi_game = get_simi_type(gamename)
            zs360_data = zs360_game(gamename)
            yyb_data = yyb_game(gamename)
            wdj_data = wdj_game(gamename)
    if game_info:
        return render_template('gameinfo.html',game_info=game_info,same_type_games=same_type_game,simi_games=simi_game,zs360_datas=zs360_data,yyb_datas=yyb_data,wdj_datas=wdj_data)
    else:
        return render_template('error.html')

def get_game_info(game_name):
    cursor = mysql.connect().cursor()
    sql = """
        SELECT DISTINCT
        	game_name,
        	game_type,
        	game_desc,
        	game_img,
        	game_tag,
        	game_source,
        	game_link
        FROM
        	game_info
        WHERE
        	game_name = '""" \
          +game_name+ \
          """'
          """

    cursor.execute(sql)
    game_info = cursor.fetchall()
    return game_info

def get_same_type(game_name):
    cursor = mysql.connect().cursor()
    sql = """
        SELECT
        	game_link,
        	game_name
        FROM
        	game_info
        WHERE
        	game_type =(
        		SELECT
        			game_type
        		FROM
        			game_info
        		WHERE
        			game_name = '""" \
                        +game_name+ \
          """'
        	)
        LIMIT 6
    """
    cursor.execute(sql)
    game_info = cursor.fetchall()
    return game_info

def get_simi_type(game_name):
    cursor = mysql.connect().cursor()
    sql = """
        SELECT
        	similarty_game
        FROM
        	gamesimilarity
        WHERE
        	game_name = '""" \
          +game_name+ \
          """'
        AND similarty_game != '""" \
          +game_name+ \
          """'
        ORDER BY
        	similarty DESC
        LIMIT 6
    """
    cursor.execute(sql)
    game_info = cursor.fetchall()
    return game_info

@app.route('/baidudata',methods=['GET'])
def get_baidudata():
    game_name = request.args.get('gamename')
    sql = """
            SELECT
                SUBSTR(record_time, 1, 10),
                replace(game_fork,',',''),
                replace(game_post,',',''),
                replace(game_record,',','')
            FROM
                baidugamedata
            WHERE
                game_name = '"""+ \
          game_name+ \
          """'
            GROUP BY
                1,2,3,4
    """
    cursor = mysql.connect().cursor()
    cursor.execute(sql)
    gameinfo = cursor.fetchall()
    return jsonify(dates = [x[0] for x in gameinfo],
                   gamefork = [x[1] for x in gameinfo],
                   gamepost = [x[2] for x in gameinfo],
                   gamerecord = [x[3] for x in gameinfo])

@app.route('/taptapdata',methods=['GET'])
def get_taptapdata():
    game_name = request.args.get('gamename')
    sql = """
            SELECT
                SUBSTR(record_time, 1, 10),
                replace(game_downloadnum,',',''),
                replace(game_commentnum,',',''),
                replace(game_topicnum,',','')
            FROM
                taptap_gamedata
            WHERE
                game_name = '"""+ \
          game_name+ \
          """'
            GROUP BY
                1,2,3,4
    """
    cursor = mysql.connect().cursor()
    cursor.execute(sql)
    gameinfo = cursor.fetchall()
    return jsonify(dates = [x[0] for x in gameinfo],
                   gamedownload = [x[1] for x in gameinfo],
                   gamecomment = [x[2] for x in gameinfo],
                   gametopic = [x[3] for x in gameinfo])
#获取360手机助手数据
def zs360_game(game_name):
    sql = """
        SELECT
        	CONCAT('评分：', app_rate),
        	CONCAT('评论量：', app_comment),
        	CONCAT('下载量：', REPLACE(REPLACE(SUBSTR(app_download,4),'次',''),'万','0000')),
        	CONCAT('更新时间：',SUBSTR(record_time,1,10))
        FROM
        	appinfo.appstore_appdata
        WHERE
        	app_name = '"""+ \
          game_name.encode('utf-8')+ \
          """'
        AND app_source = '360手机助手'
        ORDER BY
        	record_time DESC
        LIMIT 1
    """
    cursor = mysql.connect().cursor()
    cursor.execute(sql)
    zs360_data = cursor.fetchall()
    return zs360_data
#获取应用宝数据
def yyb_game(game_name):
    sql = """
        SELECT
        	CONCAT('评分：', app_rate),
        	CONCAT('评论量：', app_comment),
        	CONCAT('下载量：',app_download),
        	CONCAT('更新时间：',SUBSTR(record_time,1,10))
        FROM
        	appinfo.appstore_appdata
        WHERE
        	app_name = '"""+ \
          game_name.encode('utf-8')+ \
          """'
        AND app_source = '应用宝'
        ORDER BY
        	record_time DESC
        LIMIT 1
    """
    cursor = mysql.connect().cursor()
    cursor.execute(sql)
    yyb_data = cursor.fetchall()
    return yyb_data
#获取豌豆荚数据
def wdj_game(game_name):
    sql = """
        SELECT
        	CONCAT('评分：', '--'),
        	CONCAT('评论量：', app_comment),
        	CONCAT('下载量：',app_download),
        	CONCAT('更新时间：',SUBSTR(record_time,1,10))
        FROM
        	appinfo.appstore_appdata
        WHERE
        	app_name = '"""+ \
          game_name.encode('utf-8')+ \
          """'
        AND app_source = '豌豆荚'
        ORDER BY
        	record_time DESC
        LIMIT 1
    """
    cursor = mysql.connect().cursor()
    cursor.execute(sql)
    wdj_data = cursor.fetchall()
    return wdj_data

#游戏对比页面入口
@app.route("/game_compare",methods=['GET'])
def game_compare():
    if request.method == "GET":
        gamename = request.args.get('game')
        compare_gamename = request.args.get('compare_game')
    return render_template('game_compare.html',gamename=gamename,compare_gamename=compare_gamename)

@app.route("/compare_data",methods=['GET'])
def compare_data():
    if request.method == "GET":
        gamename = request.args.get('game1')
        compare_gamename = request.args.get('game2').strip()
        sql = """
            SELECT
            	game_name,
            	game_downloadnum,
            	SUBSTR(record_time, 1, 10)
            FROM
            	taptap_gamedata
            WHERE
            	game_name in ('"""+gamename+"""', '"""+compare_gamename+"""')
            ORDER BY 3
        """
        cursor = mysql.connect().cursor()
        cursor.execute(sql)
        comp_data = cursor.fetchall()
        game1 = {}
        game2 = {}
        now = datetime.datetime.now()
        dates = []
        for i in range(-7,-1):
            delta  = datetime.timedelta(days=i)
            new_date = now+delta
            dates.append(new_date.strftime('%Y-%m-%d'))
        for com in comp_data:
            for date in dates:
                if com[0] == gamename and com[2] == date:
                    game1[date] = [com[1]]
                if com[0] == compare_gamename and com[2] == date:
                    game2[date] = [com[1]]
        return jsonify(dates,game1,game2)

@app.route("/market_data",methods=['GET'])
def market_data():
    if request.method == "GET":
        gamename = request.args.get('game1')
        compare_gamename = request.args.get('game2').strip()
        sql = """
            SELECT
            	app_name,
            	CASE
            		WHEN app_download like '%万%'
            			THEN CAST(REPLACE(REPLACE(SUBSTR(app_download,4),'次',''),'万','0000') AS DOUBLE)
            		WHEN app_download like '%亿%'
            			THEN CAST(REPLACE(REPLACE(SUBSTR(app_download,4),'次',''),'亿','00000000') AS DOUBLE)
            		ELSE app_download
            		END as app_download,
            	SUBSTR(record_time, 1, 10)
            FROM
            	appinfo.appstore_appdata
            WHERE
            	app_source = '360手机助手'
            AND app_name in ('"""+gamename.encode('utf-8')+"""', '"""+compare_gamename.encode('utf-8')+"""')
        """
        cursor = mysql.connect().cursor()
        cursor.execute(sql)
        comp_data = cursor.fetchall()
        game1 = {}
        game2 = {}
        now = datetime.datetime.now()
        dates = []
        for i in range(-7,-1):
            delta  = datetime.timedelta(days=i)
            new_date = now+delta
            dates.append(new_date.strftime('%Y-%m-%d'))
        for com in comp_data:
            for date in dates:
                if com[0] == gamename and com[2] == date:
                    game1[date] = [com[1]]
                if com[0] == compare_gamename and com[2] == date:
                    game2[date] = [com[1]]
        return jsonify(dates,game1,game2)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, threaded=True)