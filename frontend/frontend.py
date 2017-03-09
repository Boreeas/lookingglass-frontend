import os

import flask
import sqlalchemy
from db import Player
from flask import Flask, g, request
from sqlalchemy import or_, func
from sqlalchemy.orm import Session, sessionmaker

app = Flask(__name__)
app.config.from_json("config.json")

engine = sqlalchemy.create_engine("postgresql://{username}:{password}@localhost/{dbname}".format(
    username=app.config["DB_USER"],
    password=app.config["DB_PASS"],
    dbname=app.config["DB_NAME"]
))  # type: sqlalchemy.engine.base.Engine


def connect_db() -> sqlalchemy.orm.Session:
    return sessionmaker(bind=engine)()


def get_db() -> sqlalchemy.orm.Session:
    if not hasattr(g, 'db_session'):
        g.db_session = connect_db()
    return g.db_session


@app.teardown_appcontext
def close_db(err):
    if hasattr(g, 'db_session'):
        g.db_session.close()


@app.route('/')
def index():
    return flask.render_template("index.jinja2")


@app.route('/search')
def search():
    query = request.args["query"]
    if not query:
        return flask.redirect('/')
    norm_query = query.lower()

    session = get_db()
    db_query = session.query(Player).filter(or_(
        Player.normalized_display_name == norm_query,
        Player.player_id == norm_query
    ))
    search_results = [player for player in db_query.all()]
    if not search_results:
        db_query = session.query(Player) \
            .filter(Player.visibility_restricted == False) \
            .filter(func.similarity(Player.normalized_display_name, norm_query) > 0.2) \
            .order_by(func.similarity(Player.normalized_display_name, norm_query).desc())
        search_results = [player for player in db_query.all()]
    elif len(search_results) == 1:
        return flask.redirect(flask.url_for('show_user', userid=search_results[0].player_id))

    return flask.render_template("search.jinja2", query=query, search_results=search_results)


@app.route('/show/<userid>')
def show_user(userid: str):
    session = get_db()
    user = session.query(Player)\
        .filter(Player.player_id == userid.lower())\
        .filter(Player.visibility_restricted == False)

    if not len(user.all()) or userid == '#deleted#':
        return flask.render_template("nosuchuser.jinja2", display_name="Unknown Weaver")
    player = user[0]
    result_proxy = session.execute(
        "SELECT (COUNT(*)::FLOAT / (SELECT COUNT(*) FROM Players)) AS relative_elo FROM Players WHERE elo >= :elo",
        {"elo": player.elo}
    )  # type: sqlalchemy.engine.ResultProxy
    relative_elo = 100 * result_proxy.fetchone()[0]
    relative_elo = int(100 * relative_elo) / 100.0
    return flask.render_template("show.jinja2", player=player, relative_elo=relative_elo, games=player.get_games(session))


@app.route('/top')
def show_top():
    session = get_db()
    query = session.query(Player).filter(Player.visibility_restricted == False).order_by(Player.elo.desc()).limit(100)
    results = [player for player in query.all()]
    return flask.render_template("top.jinja2", search_results=results)

@app.route('/unlist')
def hide_player():
    return flask.render_template("hideme.jinja2")


if __name__ == '__main__':
    extra_dirs = ['templates', 'static']
    extra_files = extra_dirs[:]
    for extra_dir in extra_dirs:
        for dirname, dirs, files in os.walk(extra_dir):
            for filename in files:
                filename = os.path.join(dirname, filename)
                if os.path.isfile(filename):
                    extra_files.append(filename)
    app.run(extra_files=extra_files)
    app.run()
