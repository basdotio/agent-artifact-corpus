"""Small runtime shims for the checked-out MoneyPrinterTurbo version."""


class LegacySubMaker:
    """Only the boundary fields consumed by MoneyPrinterTurbo's voice service."""
    def __init__(self):
        self.offset = []
        self.subs = []

    def create_sub(self, timestamp, text):
        start, duration = timestamp
        self.offset.append((start, start + duration))
        self.subs.append(text)


def mktimestamp(ticks):
    milliseconds = max(0, round(ticks / 10000))
    seconds, ms = divmod(milliseconds, 1000)
    minutes, second = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    return f'{hours:02}:{minute:02}:{second:02}.{ms:03}'


def install_edge_compat():
    import edge_tts
    from edge_tts import submaker
    if hasattr(submaker, 'mktimestamp'):
        return
    original = edge_tts.Communicate

    class WordCommunicate(original):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault('boundary', 'WordBoundary')
            kwargs.setdefault('connect_timeout', 5)
            kwargs.setdefault('receive_timeout', 10)
            super().__init__(*args, **kwargs)

    edge_tts.Communicate = WordCommunicate
    edge_tts.SubMaker = LegacySubMaker
    submaker.SubMaker = LegacySubMaker
    submaker.mktimestamp = mktimestamp
