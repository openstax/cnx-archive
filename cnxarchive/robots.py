class Robots(object):
    def __init__(self, sitemap='http://cnx.org/sitemap.xml', bots=[]):
        self.sitemap = sitemap
        self.bots = bots

    def add_bot(self, bot_name, delay, pages_to_block):
        self.bots.append(Bot(bot_name, delay, pages_to_block))

    def __str__(self):
        ret_str = 'Sitemap: ' + self.sitemap + '\n'
        for bot in self.bots:
            ret_str += bot.to_string() + '\n'
        return ret_str

    def to_string(self):
        return self.__str__()


class Bot(object):
    def __init__(self, bot_name, delay, pages_to_block):
        self.name = bot_name
        self.delay = delay
        self.blocked = pages_to_block

    def __str__(self):
        ret_str = 'User-agent: ' + self.name + '\n'
        if self.delay:
            ret_str += 'Crawl-delay: ' + self.delay + '\n'
        for page in self.blocked:
            ret_str += 'Disallow: ' + page + '\n'
        return ret_str

    def to_string(self):
        return self.__str__()
