#coding=utf-8
import traceback

from jubi_common import *
from apscheduler import events
from apscheduler.schedulers.blocking import BlockingScheduler

#涨幅计算

rate_time_span = 60  # 时间间隔


def trim_to_minute(time):
    """
    将时间向上裁剪至分钟整点
    :param time: 
    :return: 
    """
    return time - (time % rate_time_span)


def get_next_time(t):
    """
    获取指定时间之后的整点一分钟
    :param t: 
    :return: 
    """
    if t == 0:
        return 0
    return trim_to_minute(t) + rate_time_span


class TickerRepository(object):

    def __init__(self):
        pass

    @staticmethod
    @monitor("get_next_minute_ticker")
    def get_next_minute_ticker(coin, time):
        """
        获取指定时间行情
        :param coin: 币种
        :param time: 
        :return: 
        """
        ret = ()
        cursor = conn.cursor()

        next_time = get_next_time(time)
        cursor.execute('select pk, price from jb_coin_ticker where coin=%s and pk >= %s order by pk asc limit 1', (coin, next_time))
        if cursor.rowcount == 0:
            return ret
        d = cursor.fetchone()
        ret = (coin, trim_to_minute(d[0]), d[1])
        cursor.close()

        return ret

    @staticmethod
    def get_price(coin, t):
        """
        获取指定时间的价格。如果不存在，则向前（必须）获取
        :param coin: 币种
        :param t: 时间
        :return: 
        """
        cursor = conn.cursor()
        cursor.execute("select price from jb_coin_ticker where coin=%s and pk<= %s order by pk desc limit 1", (coin, t))
        if cursor.rowcount == 0:
            return 0
        raw = cursor.fetchone()
        return raw[0]


class TickerIncRepository(object):
    """
    行情涨幅
    """
    def __init__(self):
        pass

    @staticmethod
    @monitor("get_last_item")
    def get_last_item(coin):
        """
        获取数据库中最晚的时间
        :param coin: 币种 
        :return: pk 
        """
        cursor = conn.cursor()
        cursor.execute('select pk from jb_coin_rate where coin=%s order by pk desc limit 1', (coin,))
        if cursor.rowcount == 0:
            return 0
        raw = cursor.fetchone()
        return raw[0]

    @staticmethod
    @monitor("add_item")
    def add_item(item):
        """
        批量添加
        :param item: (pk, coin, rate)
        :return: 
        """
        if item is None or len(item) == 0:
            return
        cursor = conn.cursor()
        cursor.execute("insert into jb_coin_rate(coin, pk, rate) values(%s, %s, %s) ", item)
        conn.commit()
        cursor.close()

def get_and_set_origin_price(m, coin, pk_time):
    """
    获取和设置日开盘价
    :param m: map
    :param coin: 
    :param pk_time: 任意时间
    :return: 
    """
    t = get_day_begin_time_int(pk_time)
    d = m.get(coin)
    if d is None or d[0] != t:
        p = TickerRepository.get_price(coin, t)
        d = (t, p)
        m[coin] = d
    return d[1]


def get_calculated_item(m, dt):
    """
    获取计算涨幅后的结果
    :param m: 
    :param dt: 
    :return: 
    """
    coin = dt[0]
    pk_time = dt[1]
    price = dt[2]
    origin_price = get_and_set_origin_price(m, coin, pk_time)
    if origin_price == 0 or pk_time == get_day_begin_time_int(pk_time):
        r = (coin, pk_time, 0)
        return r
    rate = round((price - origin_price) / origin_price, 4) * 100
    r = (coin, pk_time, rate)
    return r

@monitor("work")
def work():
    conn.connect()
    cs = get_all_coins()
    # 日开盘价
    coin_origin_price_map = {}
    while True:
        has_item = False  # 判断是否还有需要加入的项
        for c in cs:
            coin = c[0]
            last_pk = TickerIncRepository.get_last_item(coin)
            dt = TickerRepository.get_next_minute_ticker(coin, last_pk)
            if len(dt) == 0:
                continue
            item = get_calculated_item(coin_origin_price_map, dt)
            TickerIncRepository.add_item(item)
            has_item = True
        if not has_item:
            break

def err_listener(event):
    if event.exception:
        exstr = traceback.format_exc()
        logger.error('The increase calculate job crashed with exception : {0}'.format(event.exception))
        logger.error(exstr)


def mis_listener(event):
    logger.warning("The increase calculate job misfired at {}".format(time.strftime("%Y-%m-%d %X")))


if __name__ == '__main__':
    conf = {
        'apscheduler.job_defaults.coalesce': 'false',
        'apscheduler.job_defaults.max_instances': '1'
    }
    sched = BlockingScheduler(conf)
    sched.add_job(work, 'cron', second='30')
    sched.add_listener(err_listener, events.EVENT_JOB_ERROR)
    sched.add_listener(mis_listener, events.EVENT_JOB_MISSED)

    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        exstr = traceback.format_exc()
        logger.error(exstr)