import random, string
import datetime

def format_timestamp(timestamp):
    ts = timestamp / 1000
    dt = datetime.datetime.fromtimestamp(ts)
    formatted_dt = dt.strftime('%Y-%m-%d %H:%M:%S')
    return formatted_dt

def format_time(seconds):
    periods = [
        ('day', 60*60*24),
        ('hour', 60*60),
        ('minute', 60),
        ('second', 1)
    ]

    strings = []
    for name, count in periods:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                strings.append(f"{value} {name}")
            else:
                strings.append(f"{value} {name}s")
    return ', '.join(strings)

characters = string.ascii_letters + string.digits

def generate_string(length):
    return ''.join(random.choice(characters) for _ in range(length))

def is_numeric(value):
    return value.isdigit()