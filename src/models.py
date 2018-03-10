class TeamStats(object):

    def __init__(self,
                 name,
                 position,
                 wins,
                 ties,
                 loses,
                 points
                 ):
        self.name = name
        self.position = position
        self.played = wins + ties + loses
        self.wins = wins
        self.ties = ties
        self.loses = loses
        self.points = points

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__str__())


class Match(object):

    def __init__(self,
                 team_a,
                 team_b,
                 score_a,
                 score_b):
        self.team_a = team_a
        self.team_b = team_b
        self.score_a = score_a
        self.score_b = score_b

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__str__())
