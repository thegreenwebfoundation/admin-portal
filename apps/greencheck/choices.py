from djchoices import DjangoChoices, ChoiceItem


class GreenlistChoice(DjangoChoices):
    asn = ChoiceItem('as')
    ip = ChoiceItem()
    none = ChoiceItem()
    url = ChoiceItem()
    whois = ChoiceItem()


class CheckedOptions(DjangoChoices):
    admin = ChoiceItem()
    api = ChoiceItem()
    apisearch = ChoiceItem()
    bots = ChoiceItem()
    test = ChoiceItem()
    website = ChoiceItem()


class BoolChoice(DjangoChoices):
    yes = ChoiceItem()
    no = ChoiceItem()
    old = ChoiceItem()
