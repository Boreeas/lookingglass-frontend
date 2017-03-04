from typing import List

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session

Base = declarative_base()


class FullGameInfo:
    def __init__(self, start_date, end_result: str, elo_value: int, opponent: "Player"):
        self.start_date = start_date
        self.end_result = end_result  # type: str
        self.elo_value = elo_value  # type: int
        self.opponent = opponent  # type: Player


class Player(Base):
    __tablename__ = 'players'

    display_name = Column(String, nullable=False)
    normalized_display_name = Column(String, nullable=False)
    player_id = Column(String, primary_key=True)
    elo = Column(Integer, default=0, nullable=False)

    __games__ = relationship("PlayerPlayedGame", back_populates="player")

    def __repr__(self):
        return "<Player(display_name='{}', player_id='{}', elo='{}')>".format(
            self.display_name, self.player_id, self.elo
        )

    def get_games(self, session: Session) -> List[FullGameInfo]:
        query = session.query(Game, PlayerPlayedGame) \
            .select_from(Player) \
            .join(PlayerPlayedGame) \
            .join(Game, Game.game_id == PlayerPlayedGame.game_id) \
            .filter(Player.player_id == self.player_id) \
            .order_by(Game.start_date.desc())
        result = []
        for game, participation in query:
            players = game.get_players(session)
            if len(players) == 1:
                opponent = Player()
                opponent.display_name = "Unknown Weaver"
                opponent.player_id = '#deleted#'
                opponent.elo = 0
                opponent.normalized_display_name = "unknown weaver"
            elif players[0].player_id == self.player_id:
                opponent = players[1]
            else:
                opponent = players[0]
            result.append(FullGameInfo(game.start_date, participation.end_result, participation.elo_diff, opponent))
        return result


class Game(Base):
    __tablename__ = 'games'

    game_id = Column(String, primary_key=True)
    start_date = Column(DateTime(timezone=True), nullable=False)

    __players__ = relationship("PlayerPlayedGame", back_populates="game")

    def __repr__(self):
        return "<Game(game_id='{}', start_date='{}')>".format(self.game_id, self.start_date)

    def get_players(self, session: Session) -> List[Player]:
        query = session.query(Player) \
            .select_from(Game) \
            .join(PlayerPlayedGame) \
            .join(Player, Player.player_id == PlayerPlayedGame.player_id) \
            .filter(Game.game_id == self.game_id)
        return [game for game in query.all()]


class PlayerPlayedGame(Base):
    __tablename__ = 'playerplayedgame'

    player_id = Column(String, ForeignKey('players.player_id'), primary_key=True)
    game_id = Column(String, ForeignKey('games.game_id'), primary_key=True)
    end_result = Column(ENUM('Win', 'Loss', 'Draw', 'Coop Win', 'Coop Loss'))
    elo_diff = Column(Integer, nullable=True)

    player = relationship(Player, back_populates="__games__")
    game = relationship(Game, back_populates="__players__")
